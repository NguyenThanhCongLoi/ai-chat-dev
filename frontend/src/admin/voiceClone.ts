import {inferCloneSource,refreshVoiceSources,selectVoiceSource} from "./voiceSources";
import { bindVoiceClipEditor } from "./voiceClipEditor";
let refreshCurrentVoice:(resetTarget:boolean)=>void=()=>{};
export function refreshVoiceClone(resetTarget=true){refreshCurrentVoice(resetTarget);}
export function bindVoiceClone(current:()=>{id:string;spec:{name:string;tts_gender?:string}}|undefined,updated:(value:unknown)=>void,loadVoices:()=>Promise<void>) {
    const anchor=document.querySelector("#character-tts-gender")?.closest("label");
    if(!anchor)return;
    anchor.insertAdjacentHTML("afterend",`<fieldset id="character-voice-clone" class="field wide"><legend>Clone giọng cho nhân vật</legend>
        <label class="field">Tên giọng<input id="clone-voice-name" maxlength="120" placeholder="Để trống để dùng tên nhân vật"></label>
        <label class="field">Mẫu âm thanh<input id="clone-voice-audio" type="file" accept=".wav,.mp3,.flac,.ogg,.m4a"><small>Tối đa 20 MB. Dùng mẫu giọng rõ, ít tạp âm.</small></label>
        <label class="field">Ngôn ngữ mẫu<select id="clone-voice-language"><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
        <label class="field">Lời đọc trong mẫu (tuỳ chọn)<textarea id="clone-voice-text" maxlength="20000" rows="2" placeholder="Để trống để API tự nhận diện"></textarea></label>
        <label><input id="clone-voice-enhance" type="checkbox"> Khử nhiễu mẫu giọng</label>
        <button class="btn" id="clone-voice-submit" type="button">Upload và gán giọng</button>
        <small id="clone-voice-status" role="status">Dùng model TTS và API key đã cấu hình trong CMS. Giọng mới được lưu ngay cho nhân vật.</small></fieldset>`);
    document.querySelector("#clone-voice-name")?.closest("label")?.insertAdjacentHTML("beforebegin",'<label class="field">Gán giọng cho<select id="clone-voice-target"><option value="shared">Dùng chung (VI / EN)</option><option value="vi">Riêng tiếng Việt</option><option value="en">Riêng tiếng Anh</option></select></label>');
    document.querySelector("#clone-voice-audio")?.closest("label")?.before(document.querySelector("#clone-voice-language")!.closest("label")!);
    const clipEditor=bindVoiceClipEditor();
    document.querySelector("#clone-voice-target")?.closest("label")?.insertAdjacentHTML("afterend",`
      <section class="voiceSavedSample" aria-label="Mẫu giọng hiện tại">
        <strong>Mẫu giọng hiện tại</strong>
        <p id="clone-voice-current-file" role="status"></p>
        <small id="clone-voice-current-id"></small>
        <audio id="clone-voice-current-preview" controls preload="none" style="width:100%" hidden></audio>
      </section>`);
    const targetSelect=document.querySelector<HTMLSelectElement>("#clone-voice-target")!;
    document.querySelector("#character-tts-source")?.closest("label")?.before(targetSelect.closest("label")!);
    const savedAudio=document.querySelector<HTMLAudioElement>("#clone-voice-current-preview")!;
    const savedFile=document.querySelector<HTMLElement>("#clone-voice-current-file")!;
    const savedId=document.querySelector<HTMLElement>("#clone-voice-current-id")!;
    let sampleRequest:AbortController|undefined;
    const clearSaved=()=>{
        savedAudio.pause();savedAudio.removeAttribute("src");savedAudio.load();savedAudio.hidden=true;
        savedFile.textContent="";savedId.textContent="";
    };
    refreshCurrentVoice=(resetTarget)=>{
        sampleRequest?.abort();clearSaved();clipEditor.reset();
        document.querySelector<HTMLInputElement>("#clone-voice-name")!.value="";
        document.querySelector<HTMLTextAreaElement>("#clone-voice-text")!.value="";
        const item=current();if(!item)return;
        if(resetTarget){
            const mode=document.querySelector<HTMLSelectElement>("#character-tts-mode")!.value;
            const vi=document.querySelector<HTMLInputElement>("#character-tts-vi")!.value;
            const en=document.querySelector<HTMLInputElement>("#character-tts-en")!.value;
            targetSelect.value=mode==="shared"?"shared":!vi&&en?"en":"vi";
        }
        const target=targetSelect.value,id=item.id,controller=new AbortController();
        sampleRequest=controller;savedFile.textContent="Đang tải mẫu giọng…";
        if(target!=="shared"){
            document.querySelector<HTMLSelectElement>("#clone-voice-language")!.value=target;
            const view=document.querySelector<HTMLSelectElement>("#character-tts-language")!;
            view.value=target;view.dispatchEvent(new Event("change"));
        }
        const endpoint="/v1/admin/characters/"+encodeURIComponent(id)+"/voice/sample/"+target;
        void fetch(endpoint,{signal:controller.signal,cache:"no-store"}).then(async response=>{
            if(!response.ok)throw Error("Không tải được mẫu giọng hiện tại.");
            return response.json();
        }).then(data=>{
            if(controller.signal.aborted||current()?.id!==id||targetSelect.value!==target)return;
            savedId.textContent=data.voice_id?"Mã giọng: "+data.voice_id:"";
            if(data.available){
                inferCloneSource("character",target);
                savedFile.textContent=data.filename;
                savedAudio.src=endpoint+"/audio?v="+encodeURIComponent(data.updated_at);savedAudio.hidden=false;
                if(data.sample_language)document.querySelector<HTMLSelectElement>("#clone-voice-language")!.value=data.sample_language;
                document.querySelector<HTMLTextAreaElement>("#clone-voice-text")!.value=data.ref_text||"";
            }else savedFile.textContent=data.voice_id?"Giọng đã được gán nhưng chưa có file mẫu lưu trên server. Upload lại mẫu để lưu.":"Chưa có giọng hoặc file mẫu cho lựa chọn này.";
        }).catch(error=>{if(!controller.signal.aborted)savedFile.textContent=String(error);});
    };
    savedAudio.onplay=()=>{
        document.querySelector<HTMLAudioElement>("#voice-original-preview")?.pause();
        document.querySelector<HTMLAudioElement>("#voice-clip-preview")?.pause();
    };
    document.querySelector("#clone-voice-audio")?.addEventListener("change",()=>{sampleRequest?.abort();savedAudio.pause();document.querySelector<HTMLTextAreaElement>("#clone-voice-text")!.value="";});
    const modal=anchor.closest(".scrim");
    if(modal)new MutationObserver(()=>{if(modal.hasAttribute("hidden")){sampleRequest?.abort();savedAudio.pause();}}).observe(modal,{attributes:true,attributeFilter:["hidden"]});

    const button=document.querySelector<HTMLButtonElement>("#clone-voice-submit")!;
    button.onclick=async()=>{
        const item=current(),file=document.querySelector<HTMLInputElement>("#clone-voice-audio")!.files?.[0];
        const status=document.querySelector<HTMLElement>("#clone-voice-status")!;
        if(!item||!file){status.textContent="Chọn nhân vật và mẫu giọng trước.";return;}
        if(file.size>20*1024*1024){status.textContent="Mẫu giọng tối đa 20 MB.";return;}
        let selected:File;
        try{selected=clipEditor.selectedFile();}
        catch(error){status.textContent=String(error);return;}
        const form=new FormData();
        form.append("audio",selected);form.append("name",document.querySelector<HTMLInputElement>("#clone-voice-name")!.value.trim()||item.spec.name);
        form.append("gender",document.querySelector<HTMLSelectElement>("#character-tts-gender")!.value);
        const target=document.querySelector<HTMLSelectElement>("#clone-voice-target")!.value;
        form.append("target",target);
        form.append("language",document.querySelector<HTMLSelectElement>("#clone-voice-language")!.value);
        form.append("ref_text",document.querySelector<HTMLTextAreaElement>("#clone-voice-text")!.value);
        form.append("enhance_audio",String(document.querySelector<HTMLInputElement>("#clone-voice-enhance")!.checked));
        button.disabled=true;targetSelect.disabled=true;
        const save=document.querySelector<HTMLButtonElement>("#save-character");
        if(save)save.disabled=true;
        status.textContent="Đang clone giọng và lưu cho nhân vật…";
        try {
            const response=await fetch("/v1/admin/characters/"+encodeURIComponent(item.id)+"/voice/clone",{method:"POST",body:form});
            const result=await response.json();
            if(!response.ok)throw new Error(typeof result.detail==="string"?result.detail:"Không clone được giọng.");
            updated(result.character);
            if(current()?.id===item.id) {
                document.querySelector<HTMLInputElement>("#character-tts-"+(target==="shared"?"voice":target))!.value=result.voice_id;
                const language=document.querySelector<HTMLSelectElement>("#character-tts-language");
                if(language && target!=="shared"){language.value=target;language.dispatchEvent(new Event("change"));}
                const mode=document.querySelector<HTMLSelectElement>("#character-tts-mode");
                if(mode){mode.value=target==="shared"?"shared":"separate";mode.dispatchEvent(new Event("change"));}
                selectVoiceSource("character",target,"clone");
                if(targetSelect.value===target)refreshVoiceClone(false);
                status.textContent="Đã lưu giọng: "+result.voice_id;
            }
            await loadVoices();
        }catch(error){status.textContent=String(error);}
        finally {button.disabled=false;targetSelect.disabled=false;if(save)save.disabled=false;}
    };
    document.querySelector<HTMLSelectElement>("#clone-voice-target")?.addEventListener("change",event=>{
        const target=(event.target as HTMLSelectElement).value;
        const language=document.querySelector<HTMLSelectElement>("#character-tts-language");
        const mode=document.querySelector<HTMLSelectElement>("#character-tts-mode");
        if(language && target!=="shared")language.value=target;
        if(mode){mode.value=target==="shared"?"shared":"separate";mode.dispatchEvent(new Event("change"));}
        refreshVoiceClone(false);
    });
    for(const suffix of ["mode","language"]){
        document.querySelector("#character-tts-"+suffix)?.addEventListener("change",()=>{
            const mode=document.querySelector<HTMLSelectElement>("#character-tts-mode")!;
            const language=document.querySelector<HTMLSelectElement>("#character-tts-language")!;
            const target=mode.value==="separate"?language.value:"shared";
            if(targetSelect.value!==target){targetSelect.value=target;refreshVoiceClone(false);}
        });
    }
    refreshVoiceSources();
}
