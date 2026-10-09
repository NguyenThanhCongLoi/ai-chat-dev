import { encodeWavClip } from "./audioClip";
let previousCleanup:(()=>void)|undefined;
export function bindVoiceClipEditor() {
    previousCleanup?.();
    const input=document.querySelector<HTMLInputElement>("#clone-voice-audio")!;
    input.insertAdjacentHTML("afterend",`<div id="voice-clip-editor" hidden style="display:grid;gap:12px;margin-top:12px">
        <label>Nghe file gốc<audio id="voice-original-preview" controls preload="metadata" style="width:100%"></audio></label>
        <div class="voiceClipBounds">
        <label>Bắt đầu (giây)<input id="voice-clip-start" type="number" min="0" step="0.01" value="0"><input id="voice-clip-start-range" type="range" min="0" step="0.01" value="0" aria-label="Điểm bắt đầu"></label>
        <label>Kết thúc (giây)<input id="voice-clip-end" type="number" min="0" step="0.01" value="0"><input id="voice-clip-end-range" type="range" min="0" step="0.01" value="0" aria-label="Điểm kết thúc"></label></div>
        <small id="voice-clip-duration" role="status"></small>
        <label>Nghe đoạn đã cắt<audio id="voice-clip-preview" controls preload="metadata" style="width:100%"></audio></label>
        <small>Chỉ đoạn đã chọn được gửi để clone, tối đa 10 giây. Lời đọc tham chiếu phải khớp đoạn này.</small>
        </div>`);
    const editor=document.querySelector<HTMLElement>("#voice-clip-editor")!;
    // Inline display is removed while hidden, otherwise it overrides [hidden].
    editor.style.display="";editor.style.gap="12px";
    const original=document.querySelector<HTMLAudioElement>("#voice-original-preview")!;
    const preview=document.querySelector<HTMLAudioElement>("#voice-clip-preview")!;
    const start=document.querySelector<HTMLInputElement>("#voice-clip-start")!;
    const end=document.querySelector<HTMLInputElement>("#voice-clip-end")!;
    const startRange=document.querySelector<HTMLInputElement>("#voice-clip-start-range")!;
    const endRange=document.querySelector<HTMLInputElement>("#voice-clip-end-range")!;
    const status=document.querySelector<HTMLElement>("#voice-clip-duration")!;
    let buffer:AudioBuffer|null=null,clip:Blob|null=null,originalUrl="",clipUrl="",revision=0;
    function release() {
        original.pause();preview.pause();
        if(originalUrl)URL.revokeObjectURL(originalUrl);
        if(clipUrl)URL.revokeObjectURL(clipUrl);
        originalUrl=clipUrl="";buffer=null;clip=null;
        original.removeAttribute("src");preview.removeAttribute("src");editor.hidden=true;
    }
    function update() {
        preview.pause();clip=null;
        if(clipUrl)URL.revokeObjectURL(clipUrl);clipUrl="";
        preview.removeAttribute("src");
        if(!buffer)return;
        try {
            clip=encodeWavClip(buffer,Number(start.value),Number(end.value));
            clipUrl=URL.createObjectURL(clip);preview.src=clipUrl;
            status.textContent="Đã chọn "+(Number(end.value)-Number(start.value)).toFixed(2)+" giây / File gốc "+buffer.duration.toFixed(2)+" giây";
        }catch(error){status.textContent=String(error);}
    }
    for(const [number,range] of [[start,startRange],[end,endRange]]) {
        number.oninput=()=>{range.value=number.value;update();};
        range.oninput=()=>{number.value=range.value;update();};
    }
    original.onplay=()=>preview.pause();preview.onplay=()=>original.pause();
    input.onchange=async()=>{
        const sequence=++revision;release();
        const file=input.files?.[0];if(!file)return;
        editor.hidden=false;status.textContent="Đang đọc file âm thanh…";
        if(file.size>20*1024*1024){status.textContent="Mẫu giọng tối đa 20 MB.";return;}
        originalUrl=URL.createObjectURL(file);original.src=originalUrl;
        const context=new AudioContext();
        try {
            const decoded=await context.decodeAudioData(await file.arrayBuffer());
            if(sequence!==revision)return;
            buffer=decoded;
            for(const element of [start,end,startRange,endRange])element.max=String(buffer.duration);
            start.value=startRange.value="0";end.value=endRange.value=String(Math.min(buffer.duration,10));
            update();
        }catch{if(sequence===revision)status.textContent="Không đọc được audio. Hãy thử file WAV hoặc MP3 khác.";}
        finally{await context.close();}
    };
    const modal=input.closest(".scrim");
    const observer=new MutationObserver(()=>{if(modal?.hasAttribute("hidden")){original.pause();preview.pause();}});
    if(modal)observer.observe(modal,{attributes:true,attributeFilter:["hidden"]});
    previousCleanup=()=>{revision++;observer.disconnect();release();};
    return {
        reset() { revision++; input.value=""; release(); status.textContent=""; },
        selectedFile() {
            if(!clip)throw new Error("Chọn và cắt đoạn audio hợp lệ trước khi upload.");
            const stem=(input.files?.[0]?.name||"voice-reference").replace(/\.[^.]+$/,"");
            return new File([clip],stem+"-clip.wav",{type:"audio/wav"});
        }
    };
}
