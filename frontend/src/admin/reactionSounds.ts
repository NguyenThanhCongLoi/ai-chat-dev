type Current={id:string};
let refresh=()=>{};
export function refreshReactionSounds(){refresh();}
export function bindReactionSounds(current:()=>Current|undefined){
  const anchor=document.querySelector("#character-voice-clone");
  if(!anchor)return;
  anchor.insertAdjacentHTML("afterend",`<fieldset id="character-reactions" class="field wide cmsReactionSounds">
  <legend>Âm phản ứng nhân vật</legend>
  <small>Tạo sẵn 12 clip bằng mẫu clone hiện tại. Các clip được lưu trên server, phát riêng với lời thoại và không gọi model khi chat. Mẫu clone cần dài hơn 5 giây; khuyến nghị khoảng 10 giây.</small>
  <label>Giọng dùng để tạo clip<select id="reaction-target"><option value="shared">Dùng chung (VI / EN)</option><option value="vi">Giọng tiếng Việt</option><option value="en">Giọng tiếng Anh</option></select></label>
  <label>Mẫu riêng cho âm phản ứng<input id="reaction-reference" type="file" accept=".wav,.mp3,.flac,.ogg,.m4a"><small>Không thay mẫu clone lời thoại. Nên dùng 8–15 giây, tối đa 20 MB.</small></label>
  <div class="cmsActions"><button type="button" class="btn" id="reaction-upload">Lưu mẫu riêng</button><button type="button" class="btn" id="reaction-remove-reference">Xoá mẫu riêng / dùng mẫu clone</button></div>
  <small id="reaction-reference-info"></small><audio id="reaction-reference-preview" controls preload="none" hidden></audio>
  <label><input id="reaction-repeat" type="checkbox" checked> Cho phép lặp mẫu ngắn 2–3 lần để đủ hơn 5 giây</label>
  <small>Lặp chỉ tăng thời lượng, không thêm thông tin về giọng. Mẫu quá ngắn vẫn cần upload lại.</small>
  <label>Âm lượng <output id="reaction-volume-label">65%</output><input id="reaction-volume" type="range" min="0" max="100" value="65"></label>
  <div class="cmsActions"><button type="button" class="btn" id="reaction-fill">Tạo bù clip còn thiếu</button><button type="button" class="btn" id="reaction-generate">Tạo / tạo lại âm phản ứng</button><button type="button" class="btn" id="reaction-save">Lưu âm lượng</button><button type="button" class="btn danger" id="reaction-delete">Xoá bộ clip</button><button type="button" class="btn" id="reaction-backfill">Tạo bộ clip còn thiếu cho nhân vật hệ thống</button></div>
  <small id="reaction-status" role="status"></small><div id="reaction-clips" class="cmsReactionClips"></div></fieldset>`);
  const host=document.querySelector<HTMLElement>("#character-reactions")!;
  const target=host.querySelector<HTMLSelectElement>("#reaction-target")!;
  const reference=host.querySelector<HTMLInputElement>("#reaction-reference")!;
  const preview=host.querySelector<HTMLAudioElement>("#reaction-reference-preview")!;
  const repeat=host.querySelector<HTMLInputElement>("#reaction-repeat")!;
  const volume=host.querySelector<HTMLInputElement>("#reaction-volume")!;
  const status=host.querySelector<HTMLElement>("#reaction-status")!;
  const list=host.querySelector<HTMLElement>("#reaction-clips")!;
  let epoch=0,timer:number|undefined;
  const endpoint=(id:string)=>"/v1/admin/characters/"+encodeURIComponent(id)+"/reactions";
  async function request(url:string,options?:RequestInit){
    const response=await fetch(url,options);const body=await response.json();
    if(!response.ok)throw new Error(typeof body.detail==="string"?body.detail:"Request failed ("+response.status+")");
    return body;
  }
  function label(){host.querySelector("#reaction-volume-label")!.textContent=volume.value+"%";}
  volume.oninput=()=>{label();list.querySelectorAll<HTMLAudioElement>("audio").forEach(audio=>audio.volume=Number(volume.value)/100);};
  refresh=()=>{
    window.clearTimeout(timer);++epoch;
    reference.value="";preview.pause();preview.removeAttribute("src");preview.hidden=true;
    list.querySelectorAll<HTMLAudioElement>("audio").forEach(audio=>audio.pause());list.replaceChildren();
    void load();
  };
  async function load(){
    const item=current();if(!item)return;
    const version=epoch,assignment=target.value;
    try{
      const [data,sample]=await Promise.all([request(endpoint(item.id)+"?target="+assignment),request(endpoint(item.id)+"/reference?target="+assignment)]);
      if(epoch!==version||current()?.id!==item.id||target.value!==assignment)return;
      host.querySelector("#reaction-reference-info")!.textContent=sample.available
        ?(sample.source==="separate"?"Đang dùng mẫu riêng: ":"Đang dùng mẫu clone lời thoại: ")+sample.filename:"Chưa có mẫu cho lựa chọn giọng này.";
      if(sample.available&&preview.getAttribute("src")!==sample.url){preview.src=sample.url;preview.hidden=false;}
      if(!sample.available){preview.pause();preview.removeAttribute("src");preview.hidden=true;}
      volume.value=String(Math.round(data.volume*100));label();
      const names:Record<string,string>={no_sample:"Chưa có mẫu clone cho lựa chọn này.",missing:"Chưa có bộ clip cho giọng hiện tại.",partial:"Bộ clip còn thiếu.",stale:"Giọng đã đổi. Hãy tạo lại clip.",generating:"Đang tạo clip trên worker Chatterbox…",ready:"Bộ clip đã sẵn sàng.",failed:"Tạo clip thất bại. Kiểm tra worker character-reactions rồi thử lại."};
      status.textContent=(names[data.status]||"Chưa có bộ clip.")+(data.status==="failed"&&typeof data.error==="string"?" "+data.error:"");
      status.textContent+=" "+data.clips.length+"/12 clip · còn thiếu "+data.missing_count+".";
      host.querySelector<HTMLButtonElement>("#reaction-generate")!.disabled=data.status==="no_sample"||data.status==="generating";
      host.querySelector<HTMLButtonElement>("#reaction-fill")!.disabled=data.status==="no_sample"||data.status==="generating"||data.missing_count===0;
      list.querySelectorAll<HTMLAudioElement>("audio").forEach(audio=>audio.pause());list.replaceChildren();
      for(const clip of data.clips){
        const card=document.createElement("div"),name=document.createElement("b"),audio=document.createElement("audio");
        name.textContent=clip.emotion+" · "+(clip.variant+1);
        audio.controls=true;audio.preload="none";audio.src=clip.url;audio.volume=data.volume;
        const remove=document.createElement("button");remove.type="button";remove.className="btn danger";remove.textContent="Xoá clip";
        remove.onclick=()=>{void request(endpoint(item.id)+"/"+encodeURIComponent(clip.id),{method:"DELETE"}).then(()=>{if(epoch===version)refresh();}).catch(error=>{if(epoch===version)status.textContent=String(error);});};
        card.append(name,audio,remove);list.append(card);
      }
      if(data.status==="generating")timer=window.setTimeout(()=>{if(host.isConnected&&host.offsetParent!==null)void load();},3000);
    }catch(error){if(epoch===version)status.textContent=String(error);}
  }
  target.onchange=refresh;
  const run=async(kind:string)=>{
    const item=current();if(!item)return;
    const version=epoch,assignment=target.value;
    try{
      if(kind==="upload"){
        const file=reference.files?.[0];
        if(!file)throw new Error("Chọn file mẫu trước.");
        if(file.size>20*1024*1024)throw new Error("Mẫu riêng tối đa 20 MB.");
        const form=new FormData();form.append("audio",file);
        await request(endpoint(item.id)+"/reference?target="+assignment,{method:"POST",body:form});
        if(version===epoch)refresh();
      }else if(kind==="remove-reference"){
        await request(endpoint(item.id)+"/reference?target="+assignment,{method:"DELETE"});
        if(version===epoch)refresh();
      }else if(kind==="backfill"){
        const result=await request("/v1/admin/system-characters/reactions/backfill?repeat_short="+repeat.checked,{method:"POST"});
        if(version!==epoch)return;
        status.textContent="Đã xử lý "+result.characters.length+" lựa chọn giọng; "+result.missing_samples.length+" lựa chọn chưa có mẫu clone.";
      }else if(kind==="save"){
        await request(endpoint(item.id),{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({volume:Number(volume.value)/100})});
        if(version===epoch)status.textContent="Đã lưu âm lượng.";
      }else{
        await request(endpoint(item.id)+(kind==="generate"||kind==="fill"?"/generate":"")+"?target="+assignment+(kind==="generate"||kind==="fill"?"&repeat_short="+repeat.checked+"&missing_only="+(kind==="fill"):""),{method:kind==="generate"||kind==="fill"?"POST":"DELETE"});
        if(version===epoch&&target.value===assignment)refresh();
      }
    }catch(error){if(version===epoch)status.textContent=String(error);}
  };
  for(const kind of ["generate","fill","save","delete","backfill","upload","remove-reference"])
    host.querySelector<HTMLButtonElement>("#reaction-"+kind)!.onclick=()=>void run(kind);
  const observer=new MutationObserver(()=>{if(!host.isConnected){window.clearTimeout(timer);observer.disconnect();}else if(host.offsetParent===null){preview.pause();list.querySelectorAll<HTMLAudioElement>("audio").forEach(audio=>audio.pause());}});
  observer.observe(document.body,{attributes:true,childList:true,subtree:true});
}
