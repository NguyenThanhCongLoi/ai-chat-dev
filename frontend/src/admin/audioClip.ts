/** Export only the selected samples as mono PCM16 WAV for voice cloning. */
export function encodeWavClip(buffer: Pick<AudioBuffer,"duration"|"sampleRate"|"length"|"numberOfChannels"|"getChannelData">, start: number, end: number): Blob {
    if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end > buffer.duration + .001 || end <= start)
        throw new Error("Chọn điểm bắt đầu và kết thúc hợp lệ.");
    if (end - start > 10.001) throw new Error("Đoạn mẫu clone tối đa 10 giây.");
    const first=Math.floor(start*buffer.sampleRate),last=Math.min(buffer.length,Math.floor(end*buffer.sampleRate));
    const count=last-first;
    if(count<1)throw new Error("Đoạn được chọn quá ngắn.");
    const bytes=new ArrayBuffer(44+count*2),view=new DataView(bytes);
    const text=(offset:number,value:string)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
    text(0,"RIFF");view.setUint32(4,36+count*2,true);text(8,"WAVE");text(12,"fmt ");
    view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
    view.setUint32(24,buffer.sampleRate,true);view.setUint32(28,buffer.sampleRate*2,true);
    view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,"data");view.setUint32(40,count*2,true);
    const channels=Array.from({length:buffer.numberOfChannels},(_,i)=>buffer.getChannelData(i));
    for(let i=0;i<count;i++){
        let value=0;for(const channel of channels)value+=channel[first+i];
        value=Math.max(-1,Math.min(1,value/channels.length));
        view.setInt16(44+i*2,Math.round(value<0?value*32768:value*32767),true);
    }
    return new Blob([bytes],{type:"audio/wav"});
}
