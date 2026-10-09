import {bindMusicClipEditor} from "./musicClipEditor";
let uploadClip:ReturnType<typeof bindMusicClipEditor>|undefined;
type MusicConfig = { volume: number; selected_ids: string[] | null; tracks: {id:string;title:string;url:string;uploaded:boolean}[] };
const escapeHtml = (value: string) => value.replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]!));
export async function renderBackgroundMusic() {
    uploadClip?.dispose();uploadClip=undefined;
    const host = document.querySelector<HTMLElement>("#background-music")!;
    host.querySelectorAll<HTMLAudioElement>("audio").forEach(audio=>audio.pause());
    host.innerHTML = '<div class="panel">Đang tải nhạc…</div>';
    try {
        const response = await fetch("/v1/admin/background-music");
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json() as MusicConfig;
        host.innerHTML = `<section class="panel"><header><h3>Nhạc nền</h3><span>${data.tracks.length} bài</span></header>
        <div style="padding:20px">
        <p>Nhạc phát tại trang chủ, danh sách nhân vật và trong các cuộc hội thoại. Chọn một bài để lặp bài đó, hoặc nhiều bài để phát ngẫu nhiên.</p>
        <button class="btn" id="music-select-all">Chọn tất cả</button> <button class="btn" id="music-select-none">Bỏ chọn tất cả</button>
        <button class="btn pri" id="music-save">Lưu thiết lập</button>
        <label class="btn">Thêm nhạc<input id="music-upload" type="file" accept=".mp3,.ogg,.wav,.m4a" hidden></label>
        <button class="btn pri" id="music-upload-submit" type="button">Upload nhạc đã chọn</button>
        <p id="music-status" role="status"></p>
        <div style="display:grid;gap:12px">${data.tracks.map(track => `<div class="row"><label style="flex:1"><input type="checkbox" data-music-id="${escapeHtml(track.id)}" ${data.selected_ids===null || data.selected_ids.includes(track.id) ? "checked" : ""}> ${escapeHtml(track.title)}${track.uploaded ? " · Đã tải lên" : ""}</label><audio controls preload="none" src="${escapeHtml(track.url)}"></audio><button class="btn sm danger" data-music-delete="${escapeHtml(track.id)}" data-music-title="${escapeHtml(track.title)}">Xoá</button></div>`).join("")}</div></div></section>`;
        const checks=()=> Array.from(host.querySelectorAll<HTMLInputElement>("[data-music-id]"));
        host.querySelector<HTMLButtonElement>("#music-select-all")!.onclick=()=> checks().forEach(input=>input.checked=true);
        host.querySelector<HTMLButtonElement>("#music-select-none")!.onclick=()=> checks().forEach(input=>input.checked=false);
        const status=host.querySelector<HTMLElement>("#music-status")!;
        host.querySelector<HTMLButtonElement>("#music-save")!.onclick=async(event)=> {
            const button=event.currentTarget as HTMLButtonElement; button.disabled=true;
            try {
                const result=await fetch("/v1/admin/background-music",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({selected_ids:checks().filter(input=>input.checked).map(input=>input.dataset.musicId)})});
                if (!result.ok) throw new Error(await result.text());
                status.textContent="Đã lưu. Áp dụng khi người dùng tải lại Role Play hoặc quay về từ màn hình chat.";
            } catch(error) {status.textContent=String(error);} finally {button.disabled=false;}
        };
        const uploadInput=host.querySelector<HTMLInputElement>("#music-upload")!;
        uploadClip=bindMusicClipEditor(uploadInput,"home-music-clip");
        host.querySelector<HTMLButtonElement>("#music-upload-submit")!.onclick=async(event)=>{
            const button=event.currentTarget as HTMLButtonElement,input=uploadInput;
            let file:File;
            try{file=uploadClip!.selectedFile();}catch(error){status.textContent=String(error);return;}
            if(file.size>20*1024*1024){status.textContent="Bài nhạc tối đa 20 MB.";return;}
            input.disabled=true;button.disabled=true;uploadClip?.pause();status.textContent="Đang tải nhạc lên…";
            try {
                const form=new FormData();form.append("file",file);
                const result=await fetch("/v1/admin/background-music/upload",{method:"POST",body:form});
                if(!result.ok)throw new Error(await result.text());
                await renderBackgroundMusic();
            }catch(error){status.textContent=String(error);input.disabled=false;button.disabled=false;}
        };
        host.querySelectorAll<HTMLButtonElement>("[data-music-delete]").forEach(button=>button.onclick=async()=>{
            if(!confirm("Xoá bài nhạc “"+button.dataset.musicTitle+"” khỏi danh sách?"))return;
            button.disabled=true;
            host.querySelectorAll<HTMLAudioElement>("audio").forEach(audio=>audio.pause());
            try {
                const response=await fetch("/v1/admin/background-music/"+button.dataset.musicDelete,{method:"DELETE"});
                if(!response.ok)throw new Error(await response.text());
                await renderBackgroundMusic();
            }catch(error){status.textContent=String(error);button.disabled=false;}
        });
        host.querySelectorAll<HTMLAudioElement>("audio").forEach(audio=>audio.onplay=()=>host.querySelectorAll<HTMLAudioElement>("audio").forEach(other=>{if(other!==audio)other.pause();}));
    } catch(error) {host.textContent=String(error);}
}
