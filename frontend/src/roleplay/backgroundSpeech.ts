type PcmChunk={audio:string;sample_rate:number};
/** Prepare without autoplay, retain audio and publish received chunks to listeners. */
export async function consumePreparedSpeech(response: Response,onChunk?:(chunk:PcmChunk)=>void): Promise<Blob> {
    if(!response.ok)throw new Error("TTS HTTP "+response.status);
    const type=(response.headers.get("content-type")||"").toLowerCase();
    if(type.startsWith("audio/"))return response.blob();
    const frames:Uint8Array[]=[];let rate=0;
    const reader=response.body?.getReader();
    if(!reader)throw new Error("Không đọc được stream TTS.");
    let complete=type.startsWith("audio/"),audio=false;
    if(!complete&&!type.startsWith("text/event-stream")){await reader.cancel();throw new Error("Gateway không trả về âm thanh.");}
    const decoder=new TextDecoder();let pending="",size=0;
    try {
        while(true) {
            const {value,done}=await reader.read();
            size+=value?.length||0;
            if(size>24*1024*1024)throw new Error("Audio stream quá lớn.");
            if(type.startsWith("text/event-stream")) {
                pending=(pending+decoder.decode(value,{stream:!done})).replace(/\r\n/g,"\n");
                let boundary:number;
                while((boundary=pending.indexOf("\n\n"))>=0) {
                    const block=pending.slice(0,boundary);pending=pending.slice(boundary+2);
                    const data=block.split("\n").filter(line=>line.startsWith("data:")).map(line=>line.slice(5).trimStart()).join("\n");
                    if(!data)continue;
                    const event=JSON.parse(data);
                    if(event.error)throw new Error(typeof event.error==="string"?event.error:event.error.message||"TTS stream lỗi.");
                    if(event.type==="speech.audio.delta"){
                        if(event.format!=="pcm"||!event.audio)throw new Error("TTS gateway không trả về PCM.");
                        const nextRate=Number(event.sample_rate);
                        if(!Number.isInteger(nextRate)||nextRate<8000||nextRate>96000||(rate&&rate!==nextRate))throw Error("Sample rate TTS không hợp lệ.");
                        const raw=atob(event.audio);
                        if(!raw.length||raw.length%2)throw Error("Chunk PCM16 không hợp lệ.");
                        rate=nextRate;frames.push(Uint8Array.from(raw,char=>char.charCodeAt(0)));
                        onChunk?.({audio:event.audio,sample_rate:rate});
                        audio=true;
                    }
                    if(event.type==="speech.audio.done"){
                        if(!audio)throw new Error("TTS không trả về audio.");
                        complete=true;
                    }
                }
            }
            if(done)break;
        }
        if(!complete||!size)throw new Error("TTS stream chưa hoàn tất.");
        const bytes=frames.reduce((sum,frame)=>sum+frame.length,0);
        const wav=new ArrayBuffer(44+bytes),view=new DataView(wav);
        const label=(offset:number,value:string)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
        label(0,"RIFF");view.setUint32(4,36+bytes,true);label(8,"WAVE");label(12,"fmt ");
        view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
        view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);
        label(36,"data");view.setUint32(40,bytes,true);
        const output=new Uint8Array(wav);let offset=44;
        for(const frame of frames){output.set(frame,offset);offset+=frame.length;}
        return new Blob([wav],{type:"audio/wav"});
    } finally {await reader.cancel().catch(()=>{});}
}

type Job={version:string;promise:Promise<void>;chunks:PcmChunk[];listeners:Set<(chunk:PcmChunk)=>void>;blob?:Blob};
type LivePlayer={push:(audio:string,rate:number)=>Promise<void>;finish:()=>Promise<void>};
export class BackgroundSpeech {
    private jobs=new Map<string,Job>();
    prepare(id:string,version:string,request:()=>Promise<Response>):Promise<void> {
        const current=this.jobs.get(id);
        if(current?.version===version)return current.promise;
        const job:Job={version,promise:Promise.resolve(),chunks:[],listeners:new Set()};
        job.promise=Promise.resolve().then(request).then(response=>consumePreparedSpeech(response,chunk=>{
            job.chunks.push(chunk);for(const listener of job.listeners)listener(chunk);
        })).then(blob=>{
            job.blob=blob;job.chunks=[];
            let total=Array.from(this.jobs.values()).reduce((sum,value)=>sum+(value.blob?.size||0),0);
            for(const [key,value] of this.jobs){
                if(total<=64*1024*1024&&this.jobs.size<=32)break;
                if(value.blob&&value!==job){total-=value.blob.size;this.jobs.delete(key);}
            }
        });
        this.jobs.set(id,job);
        void job.promise.catch(()=>{if(this.jobs.get(id)===job)this.jobs.delete(id);});
        return job.promise;
    }
    pending(id:string):Promise<void>|undefined{return this.jobs.get(id)?.promise;}
    clear(){this.jobs.clear();}
    async play(id:string,signal:AbortSignal,player:LivePlayer,onFirst:()=>void):Promise<{blob:Blob}|{played:true}|null>{
        const job=this.jobs.get(id);if(!job)return null;
        if(signal.aborted)throw new DOMException("Aborted","AbortError");
        if(job.blob)return {blob:job.blob};
        let queue=Promise.resolve(),received=false;
        const receive=(chunk:PcmChunk)=>{
            queue=queue.then(async()=>{
                if(signal.aborted)throw new DOMException("Aborted","AbortError");
                await player.push(chunk.audio,chunk.sample_rate);
                if(!received){received=true;onFirst();}
            });
            void queue.catch(()=>{});
        };
        for(const chunk of job.chunks)receive(chunk);
        job.listeners.add(receive);
        let rejectAbort:()=>void=()=>{};
        const aborted=new Promise<never>((_,reject)=>{rejectAbort=()=>reject(new DOMException("Aborted","AbortError"));});
        signal.addEventListener("abort",rejectAbort,{once:true});
        try{
            await Promise.race([job.promise,aborted]);
            await Promise.race([queue,aborted]);
            if(received){await Promise.race([player.finish(),aborted]);return {played:true};}
            return job.blob?{blob:job.blob}:null;
        }finally{
            job.listeners.delete(receive);signal.removeEventListener("abort",rejectAbort);
        }
    }
}
