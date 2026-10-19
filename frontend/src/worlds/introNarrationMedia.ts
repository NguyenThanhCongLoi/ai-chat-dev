import {readWorldJson} from "./worldHttp";
import {introAudioDuration,introVoiceRate} from "./introTiming";
import type {IntroNarrationConfig} from "./IntroNarration";
const audio=new Map<string,Promise<Blob>>();
function auth(){const token=localStorage.getItem("auth_token");return {token,headers:token?{Authorization:"Bearer "+token}:undefined};}
/** A versioned blob cache shared by home prefetch and the intro player. Never generates TTS. */
export function introCueBlob(config:IntroNarrationConfig,id:string,language:string,signal?:AbortSignal){
 const {token,headers}=auth(),version=config.audio_version||String(config.revision);
 const url="/v1/moonfall/hub/narration/"+encodeURIComponent(id)+"?language="+language+"&v="+encodeURIComponent(version);
 const key=(token||"")+":"+url;
 let pending=audio.get(key);
 if(!pending){
  pending=fetch(url,{headers,cache:"no-cache",signal:AbortSignal.timeout(35000)}).then(async r=>{
   if(!r.ok)throw Error("Narration unavailable: "+r.status);
   return r.blob();
  }).catch(e=>{audio.delete(key);throw e;});
  audio.set(key,pending);
  // A bounded cache retains roughly two complete bilingual intro versions.
  if(audio.size>48)audio.delete(audio.keys().next().value!);
 }
 return pending.then(blob=>{if(signal?.aborted)throw new DOMException("Aborted","AbortError");return blob;});
}
export async function prepareIntroNarration(strict=false,progress:(value:number)=>void=()=>{}){
 progress(0);
 const {headers}=auth();if(!headers){progress(1);return;}
 const response=await fetch("/v1/moonfall/hub/narration-config",{headers,cache:"no-store",signal:AbortSignal.timeout(15000)});
 if(!response.ok)throw Error("Narration configuration unavailable");
 const config=await readWorldJson(response) as IntroNarrationConfig;
 if(!config.enabled){progress(1);return config;}
 const language=localStorage.getItem("ui_language")==="vi"?"vi":"en";
 let cursor=0,completed=0;
 const worker=async()=>{while(cursor<config.cues.length){const cue=config.cues[cursor++];try{const blob=await introCueBlob(config,cue.id,language);if(strict)introVoiceRate(await introAudioDuration(blob),cue);completed++;progress(completed/Math.max(1,config.cues.length));}catch(error){if(strict)throw error;}}};
 await Promise.all([worker(),worker()]);progress(1);
 return config;
}
