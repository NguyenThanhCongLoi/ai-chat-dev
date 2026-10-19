import {readWorldJson} from "./worldHttp";
/** Prepared fixed speech is decoded before the chapter becomes interactive. */
import type {ChapterRun,WorldEvent} from "./moonfallTypes";
import {MusicAudio} from "../roleplay/musicAudio";
export class ChapterSpeechPreparationError extends Error{
 constructor(public reason:"unprepared"|"unavailable"){super(reason==="unprepared"?"Fixed chapter speech is not prepared in CMS":"Fixed chapter speech is not ready");this.name="ChapterSpeechPreparationError";}
}
type Clip={url:string;element:HTMLAudioElement;mixer:MusicAudio};
const clips=new Map<string,Clip>(),versions=new Map<string,string>(),pending=new Map<string,Promise<void>>();
let owner="";
let speechContext:AudioContext|undefined;
function sharedContext(){
 const Constructor=window.AudioContext||(window as unknown as {webkitAudioContext:typeof AudioContext}).webkitAudioContext;
 if(!speechContext||speechContext.state==="closed")speechContext=new Constructor();
 return speechContext;
}
function scope(run:ChapterRun){return run.id+":"+((run as ChapterRun&{chapter_id?:string}).chapter_id||"")+":"+run.content_language;}
function selectOwner(){
 const token=localStorage.getItem("auth_token")||"";
 if(owner!==token){for(const c of clips.values()){c.element.pause();c.mixer.dispose();URL.revokeObjectURL(c.url);}clips.clear();versions.clear();pending.clear();if(speechContext)void speechContext.close().catch(()=>{});speechContext=undefined;owner=token;}
 return token;
}
export function preparedChapterClip(run:ChapterRun,event:WorldEvent){
 selectOwner();const key=(event as WorldEvent&{audio_key?:string}).audio_key;
 return key?clips.get(scope(run)+":"+versions.get(scope(run))+":"+key):undefined;
}
export async function prepareChapterSpeech(run:ChapterRun,progress:(value:number)=>void){
 if(!["vi","en"].includes(run.content_language)){progress(1);return;}
 const token=selectOwner(),headers={...(token?{Authorization:"Bearer "+token}:{})};
 const response=await fetch("/v1/moonfall/"+run.id+"/chapter-audio",{headers,signal:AbortSignal.timeout(30000)});
 if(!response.ok)throw Error("Chapter audio configuration unavailable");
 const plan=await readWorldJson(response) as {enabled:boolean;version:string;clips:{id:string;version:string;ready:boolean}[]};
 if(!plan.enabled){progress(1);return;}
 versions.set(scope(run),plan.version);
 // Missing authored clips must be prepared once in CMS/server maintenance,
 // never requested repeatedly as if downloading them could create TTS.
 const missing=plan.clips.filter(clip=>clip.ready===false);
 const downloadable=plan.clips.filter(clip=>clip.ready!==false);
 let cursor=0,complete=0;
 await Promise.all(Array.from({length:Math.min(2,downloadable.length)},async()=>{
  while(cursor<downloadable.length){
   const entry=downloadable[cursor++],key=scope(run)+":"+plan.version+":"+entry.id;
   if(!clips.has(key)){
    let work=pending.get(key);
    if(!work){
     work=(async()=>{
      let r:Response|undefined;
      for(let n=0;n<4;n++){
       r=await fetch("/v1/moonfall/"+run.id+"/chapter-audio/"+entry.id,{method:"POST",headers,signal:AbortSignal.timeout(40000)});
       if(r.status!==429)break;
       await new Promise(resolve=>setTimeout(resolve,1500));
      }
      if(!r?.ok)throw new ChapterSpeechPreparationError(r?.status===409?"unprepared":"unavailable");
      const blob=await r.blob();if(token!==owner)return;
      const url=URL.createObjectURL(blob),element=new Audio(),mixer=new MusicAudio(element,sharedContext);element.src=url;element.preload="auto";
      try{
       await new Promise<void>((resolve,reject)=>{
        const timer=setTimeout(()=>done(Error("Audio decode timeout")),12000);
        const done=(error?:Error)=>{clearTimeout(timer);element.oncanplay=element.onerror=null;if(error)reject(error);else resolve();};
        element.oncanplay=()=>done();element.onerror=()=>done(Error("Audio decode failed"));
        if(element.readyState>=3)done();else element.load();
       });
       if(token!==owner){URL.revokeObjectURL(url);return;}
       clips.set(key,{url,element,mixer});
       while(clips.size>180){const first=clips.keys().next().value!;const c=clips.get(first)!;c.element.pause();c.mixer.dispose();URL.revokeObjectURL(c.url);clips.delete(first);}
      }catch(e){mixer.dispose();URL.revokeObjectURL(url);throw e;}
     })().finally(()=>pending.delete(key));
     pending.set(key,work);
    }
    await work;
   }
   complete++;progress(complete/Math.max(1,plan.clips.length));
  }
 }));
 if(missing.length)throw new ChapterSpeechPreparationError("unprepared");
 progress(1);
}
