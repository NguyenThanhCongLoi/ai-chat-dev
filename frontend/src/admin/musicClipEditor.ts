import {encodeMusicClip} from "./musicAudioClip";
export function bindMusicClipEditor(input:HTMLInputElement,prefix:string) {
  const host=document.createElement("section");
  host.className="cmsMusicClipEditor";host.hidden=true;
  host.innerHTML=`
    <label class="cmsMusicTrim"><input id="${prefix}-trim" type="checkbox">Chỉ upload đoạn đã chọn</label>
    <label>Nghe file gốc<audio id="${prefix}-original" controls preload="metadata"></audio></label>
    <div id="${prefix}-bounds" class="cmsMusicClipBounds" hidden>
      <label>Bắt đầu (giây)<input id="${prefix}-start" type="number" min="0" step="0.01" value="0"><input id="${prefix}-start-range" type="range" min="0" step="0.01" value="0" aria-label="Điểm bắt đầu"></label>
      <label>Kết thúc (giây)<input id="${prefix}-end" type="number" min="0" step="0.01"><input id="${prefix}-end-range" type="range" min="0" step="0.01" aria-label="Điểm kết thúc"></label>
      <label class="full">Nghe đoạn đã cắt<audio id="${prefix}-preview" controls preload="metadata"></audio></label>
    </div>
    <small id="${prefix}-status" role="status"></small>`;
  (input.closest("label")||input).after(host);
  const field=<T extends HTMLElement>(suffix:string)=>host.querySelector<T>("#"+prefix+"-"+suffix)!;
  const trim=field<HTMLInputElement>("trim"),original=field<HTMLAudioElement>("original"),preview=field<HTMLAudioElement>("preview");
  const start=field<HTMLInputElement>("start"),end=field<HTMLInputElement>("end");
  const startRange=field<HTMLInputElement>("start-range"),endRange=field<HTMLInputElement>("end-range");
  const bounds=field<HTMLElement>("bounds"),status=field<HTMLElement>("status");
  let buffer:AudioBuffer|null=null,clip:Blob|null=null,file:File|undefined,originalUrl="",clipUrl="",revision=0;
  const pause=()=>{original.pause();preview.pause();};
  function release(){
    pause();buffer=null;clip=null;file=undefined;
    for(const audio of [original,preview]){audio.removeAttribute("src");audio.load();}
    if(originalUrl)URL.revokeObjectURL(originalUrl);if(clipUrl)URL.revokeObjectURL(clipUrl);
    originalUrl=clipUrl="";host.hidden=true;bounds.hidden=true;trim.checked=false;
  }
  function update(){
    preview.pause();clip=null;
    if(clipUrl)URL.revokeObjectURL(clipUrl);clipUrl="";preview.removeAttribute("src");
    bounds.hidden=!trim.checked;
    if(!trim.checked){status.textContent="Upload nguyên file đã chọn.";return;}
    if(!buffer){status.textContent="Chưa đọc được audio để cắt.";return;}
    try{
      clip=encodeMusicClip(buffer,Number(start.value),Number(end.value));
      clipUrl=URL.createObjectURL(clip);preview.src=clipUrl;
      status.textContent="Đã chọn "+(Number(end.value)-Number(start.value)).toFixed(2)+" giây / File gốc "+buffer.duration.toFixed(2)+" giây. Chỉ đoạn này được upload.";
    }catch(error){status.textContent=String(error);}
  }
  trim.onchange=update;
  for(const [number,range] of [[start,startRange],[end,endRange]]){
    number.oninput=()=>{range.value=number.value;update();};
    range.oninput=()=>{number.value=range.value;update();};
  }
  original.onplay=()=>preview.pause();preview.onplay=()=>original.pause();
  input.onchange=async()=>{
    const token=++revision;release();file=input.files?.[0];if(!file)return;
    host.hidden=false;trim.disabled=true;status.textContent="Đang đọc file âm thanh…";
    trim.checked=file.size>20*1024*1024;
    originalUrl=URL.createObjectURL(file);original.src=originalUrl;
    const context=new AudioContext();
    try{
      const decoded=await context.decodeAudioData(await file.arrayBuffer());if(token!==revision)return;
      buffer=decoded;
      for(const element of [start,end,startRange,endRange])element.max=String(decoded.duration);
      start.value=startRange.value="0";end.value=endRange.value=String(Math.min(decoded.duration,30));
      trim.disabled=false;update();
    }catch{if(token===revision)status.textContent="Không đọc được audio để cắt. Có thể upload file gốc hoặc thử WAV/MP3 khác.";}
    finally{await context.close();}
  };
  const boundary=input.closest(".scrim")||input.closest(".view");
  const observer=new MutationObserver(()=>{if(boundary?.hasAttribute("hidden")||boundary?.classList.contains("view")&&!boundary.classList.contains("active"))pause();});
  if(boundary)observer.observe(boundary,{attributes:true,attributeFilter:["hidden","class"]});
  return {
    reset(){revision++;input.value="";release();status.textContent="";},
    dispose(){revision++;observer.disconnect();release();host.remove();input.onchange=null;},
    selectedFile(){
      const current=input.files?.[0];
      if(!current)throw Error("Chọn một file nhạc.");
      if(!trim.checked){
        if(current.size>20*1024*1024)throw Error("File gốc vượt 20 MB. Hãy bật cắt và chọn đoạn nhạc để upload.");
        return current;
      }
      if(current!==file||!clip)throw Error("Chọn đoạn nhạc hợp lệ và chờ đọc audio xong trước khi upload.");
      const stem=current.name.replace(/\.[^.]+$/,"");
      return new File([clip],stem+"-clip.wav",{type:"audio/wav"});
    },
    pause,
  };
}
