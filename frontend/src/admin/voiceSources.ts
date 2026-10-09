type ApiVoice={id:string;name:string;gender:string;language:string};
let voices:ApiVoice[]=[];
let catalogStatus="Đang tải danh sách giọng từ API…";
const prefixes=["character","new-character"];
function field<T extends HTMLElement>(prefix:string,suffix:string){return document.querySelector<T>("#"+prefix+"-tts-"+suffix);}
function activeSlot(prefix:string){
    return field<HTMLSelectElement>(prefix,"mode")?.value==="separate"
        ? field<HTMLSelectElement>(prefix,"language")?.value||"vi" : "shared";
}
function voiceField(prefix:string,slot:string){
    return field<HTMLInputElement>(prefix,slot==="shared"?"voice":slot);
}
function sourceField(prefix:string,slot:string){
    return field<HTMLInputElement>(prefix,slot==="shared"?"source-value":"source-"+slot);
}
export function selectVoiceSource(prefix:string,slot:string,source:"clone"|"catalog"){
    const input=sourceField(prefix,slot);if(input)input.value=source;
    refreshVoiceSources(prefix);
}
export function inferCloneSource(prefix:string,slot:string){
    if(sourceField(prefix,slot)?.value==="auto")selectVoiceSource(prefix,slot,"clone");
}
export function setApiVoices(value:ApiVoice[],status?:string){
    voices=value;catalogStatus=status??(value.length?"":"API chưa trả danh sách giọng.");
    for(const prefix of prefixes)refreshVoiceSources(prefix);
}
export function refreshVoiceSources(prefix="character"){
    const source=field<HTMLSelectElement>(prefix,"source");
    if(!source)return;
    const slot=activeSlot(prefix),stored=sourceField(prefix,slot)?.value;
    if(prefix==="character")for(const key of ["mode","language"])field<HTMLSelectElement>(prefix,key)!.closest<HTMLElement>("label")!.style.display="none";
    source.value=stored==="clone"?"clone":"catalog";
    const clone=prefix==="character"?document.querySelector<HTMLElement>("#character-voice-clone"):null;
    if(clone){
        clone.style.display=source.value==="clone"?"":"none";
        if(source.value!=="clone")for(const audio of Array.from(clone.querySelectorAll("audio")))audio.pause();
    }
    field<HTMLElement>(prefix,"catalog-field")!.style.display=source.value==="catalog"?"flex":"none";
    const hint=field<HTMLElement>(prefix,"clone-hint");
    if(hint)hint.style.display=source.value==="clone"?"":"none";
    // IDs remain stored per slot; only the API select or clone workflow edits them.
    for(const key of ["voice","vi","en"]) {
        const input=field<HTMLInputElement>(prefix,key);
        if(input)input.closest<HTMLElement>("label")!.style.display="none";
    }
    const select=field<HTMLSelectElement>(prefix,"catalog")!;
    const configured=voiceField(prefix,slot)?.value||"";
    const gender=field<HTMLSelectElement>(prefix,"gender")?.value;
    const aliases:Record<string,string[]>={vi:["vi","vietnamese","vietnam","tiếng việt"],en:["en","english"]};
    const candidates=voices.filter(voice=>
        (slot==="shared"||!voice.language||aliases[slot]?.some(alias=>voice.language.trim().toLowerCase().startsWith(alias))) &&
        (gender!=="male"&&gender!=="female"||voice.gender===gender||!["male","female"].includes(voice.gender)));
    select.replaceChildren(new Option("Tự chọn giọng phù hợp theo giới tính",""));
    for(const voice of candidates)select.add(new Option(voice.name+" · "+voice.language+" · "+(voice.gender==="male"?"Nam":voice.gender==="female"?"Nữ":"Khác"),voice.id));
    if(configured&&!candidates.some(voice=>voice.id===configured)){
        const current=voices.find(voice=>voice.id===configured);
        select.add(new Option("Giọng đang gán: "+(current?.name||configured),configured));
    }
    select.value=configured;
    field<HTMLElement>(prefix,"catalog-status")!.textContent=catalogStatus||(candidates.length?"": "Không có giọng khớp giới tính và ngôn ngữ đang chọn.");
}
export function bindVoiceSources(prefix:string,loadVoices:()=>Promise<void>){
    const anchor=field<HTMLInputElement>(prefix,"voice")?.closest("label");
    if(!anchor)return;
    const sourceLabel=document.createElement("label");
    sourceLabel.className="field";
    sourceLabel.innerHTML='Nguồn giọng<select id="'+prefix+'-tts-source"><option value="catalog">Giọng có sẵn từ API</option><option value="clone">Clone giọng</option></select>';
    anchor.before(sourceLabel);
    const host=document.createElement("div");host.className="field full";
    host.innerHTML='<input type="hidden" id="'+prefix+'-tts-source-value" value="auto"><input type="hidden" id="'+prefix+'-tts-source-vi" value="auto"><input type="hidden" id="'+prefix+'-tts-source-en" value="auto"><label class="field" id="'+prefix+'-tts-catalog-field">Danh sách giọng<select id="'+prefix+'-tts-catalog"></select><small id="'+prefix+'-tts-catalog-status" role="status"></small><button class="btn sm" id="'+prefix+'-tts-catalog-reload" type="button">Tải lại danh sách giọng</button></label>';
    if(prefix==="new-character")host.innerHTML+='<small id="'+prefix+'-tts-clone-hint">Lưu nhân vật trước, sau đó mở Sửa để upload và cắt mẫu clone.</small>';
    sourceLabel.after(host);
    const reload=field<HTMLButtonElement>(prefix,"catalog-reload")!;
    reload.onclick=async()=>{
        reload.disabled=true;
        try{await loadVoices();}finally{reload.disabled=false;}
    };
    field<HTMLSelectElement>(prefix,"source")!.addEventListener("change",event=>{
        selectVoiceSource(prefix,activeSlot(prefix),(event.target as HTMLSelectElement).value as "clone"|"catalog");
    });
    field<HTMLSelectElement>(prefix,"catalog")!.addEventListener("change",event=>{
        const input=voiceField(prefix,activeSlot(prefix));
        if(input){input.value=(event.target as HTMLSelectElement).value;input.dispatchEvent(new Event("input"));}
        selectVoiceSource(prefix,activeSlot(prefix),"catalog");
    });
    for(const suffix of ["mode","language","gender"])
        field<HTMLSelectElement>(prefix,suffix)?.addEventListener("change",()=>refreshVoiceSources(prefix));
    refreshVoiceSources(prefix);
}
