import {bindVoiceSources,refreshVoiceSources} from "./voiceSources";
const speechLanguages:Record<string,string>={vi:"Tiếng Việt",en:"English",zh:"中文",ja:"日本語",ko:"한국어",my:"မြန်မာ",km:"ភាសាខ្មែរ"};
type VoiceLanguages=Record<string,{enabled:boolean;voice_id:string}>;
export function bindVoiceSettings(loadVoices:()=>Promise<void>) {
  for (const prefix of ["character","new-character"]) {
    const anchor=document.querySelector("#"+prefix+"-tts-gender")?.closest("label");
    anchor?.insertAdjacentHTML("afterend",`
      <label class="field">Chế độ giọng<select id="${prefix}-tts-mode"><option value="shared">Dùng chung (VI / EN)</option><option value="separate">Giọng Việt / Anh riêng</option></select></label>
      <label class="field" data-voice-language>Ngôn ngữ giọng<select id="${prefix}-tts-language"><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
      <label class="field">Giọng tiếng Việt<input id="${prefix}-tts-vi" list="tts-voice-options" maxlength="160" placeholder="Để trống để chọn từ danh sách giọng phù hợp"></label>
      <label class="field">Giọng tiếng Anh<input id="${prefix}-tts-en" list="tts-voice-options" maxlength="160" placeholder="Để trống để chọn từ danh sách giọng phù hợp"></label>
      <label class="field">Âm lượng giọng mặc định<input id="${prefix}-tts-volume" type="range" min="0" max="200" value="80"><output id="${prefix}-tts-volume-value">80%</output></label>`);
    const host=document.querySelector("#"+prefix+"-tts-volume")?.closest("label");
    host?.insertAdjacentHTML("afterend",'<fieldset class="field wide"><legend>Khả năng nói theo ngôn ngữ</legend><p>Việt / Anh bật sẵn và dùng cài đặt giọng phía trên. Ngôn ngữ khác cần Voice ID được API hỗ trợ trước khi bật. Đây là ngôn ngữ lời thoại, không phải ngôn ngữ giao diện.</p>'+Object.entries(speechLanguages).map(([code,label])=>'<label class="field"><span><input type="checkbox" id="'+prefix+'-speak-'+code+'" '+(["vi","en"].includes(code)?"checked":"")+'> '+label+' ('+code+')</span><input id="'+prefix+'-language-voice-'+code+'" maxlength="160" placeholder="'+(["vi","en"].includes(code)?"Để trống để dùng giọng đã gán":"Voice ID cho ngôn ngữ này")+'"></label>').join("")+'</fieldset>');
    const mode=document.querySelector<HTMLSelectElement>("#"+prefix+"-tts-mode");
    const language=document.querySelector<HTMLSelectElement>("#"+prefix+"-tts-language")!;
    const sync=()=>{
      for(const suffix of ["vi","en"]) {
        const field=document.querySelector<HTMLInputElement>("#"+prefix+"-tts-"+suffix)!;
        field.disabled=mode?.value!=="separate";
        field.closest("label")!.style.display=mode?.value!=="separate"||language.value!==suffix?"none":"";
      }
      const shared=document.querySelector<HTMLInputElement>("#"+prefix+"-tts-voice");
      if(shared){shared.disabled=mode?.value==="separate";shared.closest("label")!.style.display=mode?.value==="separate"?"none":"";}
      language.closest("label")!.style.display=mode?.value!=="separate"?"none":"";
    };
    mode?.addEventListener("change",sync);language.addEventListener("change",sync);sync();
    bindVoiceSources(prefix,loadVoices);
    const volume=document.querySelector<HTMLInputElement>("#"+prefix+"-tts-volume");
    volume?.addEventListener("input",()=>{document.querySelector("#"+prefix+"-tts-volume-value")!.textContent=volume.value+"%";});
  }
}
export function fillVoiceSettings(spec:{tts_languages?:VoiceLanguages;tts_voice_mode?:string;tts_voice_vi?:string;tts_voice_en?:string;tts_volume?:number;tts_voice_source?:string;tts_voice_source_vi?:string;tts_voice_source_en?:string}) {
  for(const [key,val] of Object.entries({mode:spec.tts_voice_mode||"shared",vi:spec.tts_voice_vi||"",en:spec.tts_voice_en||"","source-value":spec.tts_voice_source||"auto","source-vi":spec.tts_voice_source_vi||"auto","source-en":spec.tts_voice_source_en||"auto",volume:String(Math.round((spec.tts_volume??.8)*100))})) {
    const field=document.querySelector<HTMLInputElement|HTMLSelectElement>("#character-tts-"+key);
    if(field){field.value=val;if(key==="volume")field.dispatchEvent(new Event("input"));}
  }
  document.querySelector("#character-tts-mode")?.dispatchEvent(new Event("change"));
  for(const code of Object.keys(speechLanguages)) {
    const config=spec.tts_languages?.[code];
    const toggle=document.querySelector<HTMLInputElement>("#character-speak-"+code);
    const voice=document.querySelector<HTMLInputElement>("#character-language-voice-"+code);
    if(toggle)toggle.checked=config?.enabled??["vi","en"].includes(code);
    if(voice)voice.value=config?.voice_id||"";
  }
  refreshVoiceSources();
}
export function voiceSettings(prefix:string) {
  const get=(suffix:string)=>document.querySelector<HTMLInputElement|HTMLSelectElement>("#"+prefix+"-tts-"+suffix)?.value;
  const tts_languages:VoiceLanguages={};
  for(const code of Object.keys(speechLanguages)) {
    const enabled=document.querySelector<HTMLInputElement>("#"+prefix+"-speak-"+code)?.checked??["vi","en"].includes(code);
    const voice_id=document.querySelector<HTMLInputElement>("#"+prefix+"-language-voice-"+code)?.value.trim()||"";
    if(enabled&&!["vi","en"].includes(code)&&!voice_id)throw new Error("Cần gán Voice ID trước khi bật "+speechLanguages[code]+" ("+code+").");
    tts_languages[code]={enabled,voice_id};
  }
  return {tts_languages,tts_voice_mode:get("mode")||"shared",tts_voice_vi:get("vi")||"",tts_voice_en:get("en")||"",tts_voice_source:get("source-value")||"auto",tts_voice_source_vi:get("source-vi")||"auto",tts_voice_source_en:get("source-en")||"auto",tts_volume:Number(get("volume")??80)/100};
}
