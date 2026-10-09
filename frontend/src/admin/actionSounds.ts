type Sound={id:string;title:string;url:string;triggers:string[];enabled:boolean;volume:number;uploaded:boolean};
type Library={volume:number;sounds:Sound[]};
const esc=(text:string)=>text.replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]!));
async function checked(response:Response){
  if(!response.ok){
    let message="Không xử lý được thư viện âm thanh.";
    try{const data=await response.json();if(typeof data.detail==="string")message=data.detail;}catch{}
    throw Error(message);
  }
  return response.json();
}
export async function renderActionSounds(){
  const host=document.querySelector<HTMLElement>("#action-sounds")!;
  host.querySelectorAll("audio").forEach(audio=>audio.pause());
  host.innerHTML='<section class="panel">Đang tải thư viện âm hành động…</section>';
  try{
    const data=await checked(await fetch("/v1/admin/action-sounds")) as Library;
    host.innerHTML=`<section class="panel"><h2>Âm hành động</h2>
    <p>Phát song song với âm phản ứng khi nhận diện mô tả *hành động* trong câu trả lời đang stream. Không gọi thêm LLM.</p>
    <div class="fields" style="margin:18px 0"><label class="field">Âm lượng tổng
    <input id="sfx-volume" type="range" min="0" max="100" value="${Math.round(data.volume*100)}"><output id="sfx-volume-value">${Math.round(data.volume*100)}%</output></label>
    <label class="field">Thêm sound (WAV / MP3 / OGG, tối đa 20 MB)<input id="sfx-upload" type="file" accept=".wav,.mp3,.ogg"><button class="btn" id="sfx-upload-submit">Upload sound</button></label></div>
    <p>Mỗi dòng là một cách nhận diện. Dùng dấu + để yêu cầu đủ từ, ví dụ: đặt+bút+xuống, quạ+kêu, turn+page. Có thể thêm từ khóa ở các ngôn ngữ khác. Sound mới mặc định tắt cho đến khi cấu hình.</p>
    <button class="btn primary" id="sfx-save" style="margin:14px 0">Lưu thiết lập</button><p id="sfx-status" role="status"></p>
    <div class="actionSoundGrid">${data.sounds.map(sound=>`<article class="panel" data-sfx="${esc(sound.id)}">
    <label><input type="checkbox" data-enabled ${sound.enabled?"checked":""}> <strong>${esc(sound.title)}</strong></label>
    <audio controls preload="none" src="${esc(sound.url)}"></audio>
    <label class="field">Âm lượng sound<input type="range" data-volume min="0" max="100" value="${Math.round(sound.volume*100)}"><output>${Math.round(sound.volume*100)}%</output></label>
    <label class="field">Từ khóa hành động<textarea data-triggers rows="3">${esc(sound.triggers.join("\n"))}</textarea></label>
    ${sound.uploaded?'<button class="btn sm danger" data-delete>Xoá sound</button>':"<small>Sound có sẵn: bỏ dấu chọn để ngừng sử dụng.</small>"}</article>`).join("")}</div></section>`;
    const status=host.querySelector<HTMLElement>("#sfx-status")!;
    const overall=host.querySelector<HTMLInputElement>("#sfx-volume")!;
    overall.oninput=()=>{host.querySelector("#sfx-volume-value")!.textContent=overall.value+"%";};
    host.querySelectorAll<HTMLInputElement>("[data-volume]").forEach(input=>input.oninput=()=>{input.nextElementSibling!.textContent=input.value+"%";});
    host.querySelectorAll<HTMLAudioElement>("audio").forEach(audio=>audio.onplay=()=>host.querySelectorAll("audio").forEach(other=>{if(other!==audio)other.pause();}));
    host.querySelector<HTMLButtonElement>("#sfx-save")!.onclick=async event=>{
      const button=event.currentTarget as HTMLButtonElement;button.disabled=true;
      try{
        const sounds=Array.from(host.querySelectorAll<HTMLElement>("[data-sfx]")).map(card=>({
          id:card.dataset.sfx,enabled:card.querySelector<HTMLInputElement>("[data-enabled]")!.checked,
          volume:Number(card.querySelector<HTMLInputElement>("[data-volume]")!.value)/100,
          triggers:card.querySelector<HTMLTextAreaElement>("[data-triggers]")!.value.split("\n").map(text=>text.trim()).filter(Boolean)
        }));
        await checked(await fetch("/v1/admin/action-sounds",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({volume:Number(overall.value)/100,sounds})}));
        status.textContent="Đã lưu. Áp dụng khi người dùng mở lại phòng.";
      }catch(error){status.textContent=String(error);}finally{button.disabled=false;}
    };
    host.querySelector<HTMLButtonElement>("#sfx-upload-submit")!.onclick=async event=>{
      const file=host.querySelector<HTMLInputElement>("#sfx-upload")!.files?.[0];
      if(!file){status.textContent="Chọn file âm thanh trước.";return;}
      const button=event.currentTarget as HTMLButtonElement;button.disabled=true;
      try{
        const form=new FormData();form.append("file",file);
        await checked(await fetch("/v1/admin/action-sounds/upload",{method:"POST",body:form}));
        await renderActionSounds();
      }catch(error){status.textContent=String(error);button.disabled=false;}
    };
    host.querySelectorAll<HTMLButtonElement>("[data-delete]").forEach(button=>button.onclick=async()=>{
      const card=button.closest<HTMLElement>("[data-sfx]")!;
      if(!confirm("Xoá sound đã upload?"))return;
      button.disabled=true;
      try{
        await checked(await fetch("/v1/admin/action-sounds/"+encodeURIComponent(card.dataset.sfx!),{method:"DELETE"}));
        await renderActionSounds();
      }catch(error){status.textContent=String(error);button.disabled=false;}
    });
  }catch(error){host.textContent=String(error);}
}
