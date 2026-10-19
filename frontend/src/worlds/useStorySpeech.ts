import {chapterSequence,isStoryMovie,concealedSequenceEvents} from "./chapterSequence";
import {spokenBeat} from "./chapterPresentation";
import {preparedChapterClip} from "./chapterSpeechMedia";
import {useEffect,useRef,useState} from "react";
import {ChapterVoiceQueue,autoVoiceEvents} from "./ChapterVoiceQueue";
import {MusicAudio} from "../roleplay/musicAudio";
import type {ChapterRun,WorldEvent} from "./moonfallTypes";
type ScopedEvent=WorldEvent&{chapter_id?:string};
export function useStorySpeech(run:(ChapterRun&{chapter_id?:string;reviewing?:boolean;attempt_number?:number})|null,active:boolean,mode:"all"|"narrator"|"characters"|"silent"="all",sequence?:{play:(event:WorldEvent)=>Promise<void>;cancel:()=>void}){
 const [queueBusy,setQueueBusy]=useState(false);
 const [revealed,setRevealed]=useState(new Set<string>());
 const sequenceRef=useRef(sequence);sequenceRef.current=sequence;
 const [language,setLanguageState]=useState("off"),[automatic,setAutomatic]=useState(true),[playing,setPlaying]=useState(""),[error,setError]=useState(""),[preparing,setPreparing]=useState("");
 const audio=useRef<{element:HTMLAudioElement;mixer:MusicAudio;url:string;persistent?:boolean;done:()=>void}|null>(null);
 const request=useRef<AbortController|null>(null),current=useRef(run);current.current=run;
 const refs=useRef({language,active,automatic,mode});refs.current={language,active,automatic,mode};
 const playRef=useRef<(e:WorldEvent)=>Promise<void>>(async()=>{});
 const deferred=useRef<WorldEvent[]>([]);
 const previousScope=useRef(""),newChapter=useRef(false);
 const belongs=(e:WorldEvent)=>!(e as ScopedEvent).chapter_id||(e as ScopedEvent).chapter_id===current.current?.chapter_id;
 const lane=useRef<ChapterVoiceQueue<WorldEvent>|null>(null),cursor=useRef({id:"",ids:new Set<string>()});
 function stop(){sequenceRef.current?.cancel();stopAudio();}
 function stopAudio(){request.current?.abort();request.current=null;const sound=audio.current;audio.current=null;if(sound){sound.element.pause();sound.element.onplay=sound.element.onended=sound.element.onerror=null;if(!sound.persistent){sound.mixer.dispose();URL.revokeObjectURL(sound.url);}sound.done();}setPlaying("");setPreparing("");}
 lane.current??=new ChapterVoiceQueue(e=>playRef.current(e),stop,setQueueBusy);
 playRef.current=async(event)=>{
  const s=current.current,settings=refs.current;if(!s||!settings.active||!belongs(event))return;
  if(sequenceRef.current){
   setRevealed(old=>new Set([...old,event.id]));
   if(isStoryMovie(s,event)){await sequenceRef.current.play(event);return;}
   if(!settings.automatic||settings.mode==="silent"||!autoVoiceEvents([event],settings.mode).length)return;
  }
  if(settings.language==="off")return;
  const controller=new AbortController();request.current=controller;setPreparing(event.id);
  try{
   const cached=settings.language===s.content_language?preparedChapterClip(s,event):undefined;
   let url:string,element:HTMLAudioElement,mixer:MusicAudio;
   if(cached){({url,element,mixer}=cached);element.pause();element.currentTime=0;}
   else{
   const token=localStorage.getItem("auth_token");
   const r=await fetch("/v1/moonfall/"+s.id+"/voice/"+event.id,{method:"POST",signal:AbortSignal.any([controller.signal,AbortSignal.timeout(35000)]),headers:{"Content-Type":"application/json",...(token?{Authorization:"Bearer "+token}:{})},body:JSON.stringify({voice_language:settings.language,explicit_user_choice:true})});
   if(!r.ok)throw Error(s.content_language==="vi"?"Chọn provider và giọng narrator/nhân vật trong CMS để bật lời đọc.":"Configure the narrator and character voices in CMS to enable speech.");
   const blob=await r.blob();if(controller.signal.aborted||!refs.current.active)return;
    url=URL.createObjectURL(blob);element=new Audio();mixer=new MusicAudio(element);element.src=url;
   }
   await new Promise<void>((resolve,reject)=>{
    audio.current={element,mixer,url,persistent:!!cached,done:resolve};
    const levels=()=>{try{const v=JSON.parse(localStorage.getItem("moonfall_audio_levels")||"{}");return(v.master??.65)*(event.type==="NARRATION"?(v.narrator??.8):(v.character??.8));}catch{return .5;}};
    mixer.setVolume(levels());element.onplay=()=>{setPreparing("");setPlaying(event.id);setError("");};
    element.onended=()=>resolve();element.onerror=()=>reject(Error("Không phát được đoạn giọng đọc này."));
    void mixer.play().catch(reject);
   });
  }catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:String(e));}
  finally{if(request.current===controller){request.current=null;setPreparing("");const a=audio.current;audio.current=null;if(a){a.element.pause();a.element.onplay=a.element.onended=a.element.onerror=null;if(!a.persistent){a.mixer.dispose();URL.revokeObjectURL(a.url);}}setPlaying("");}}
 };
 useEffect(()=>{if(!run)return;const scope=run.id+":"+run.chapter_id+":"+run.attempt_number;newChapter.current=!!previousScope.current&&previousScope.current!==scope;previousScope.current=scope;setLanguageState(["vi","en"].includes(run.content_language)?run.content_language:"off");lane.current?.reset();setRevealed(new Set());deferred.current=[];cursor.current={id:"",ids:new Set()};},[run?.id,run?.chapter_id,run?.attempt_number,run?.content_language]);
 useEffect(()=>{lane.current?.cancel();},[mode]);
 useEffect(()=>{
  if(!run||!sequenceRef.current&&language==="off"&&cursor.current.id==="")return;
  if(run.reviewing){
   lane.current?.cancel();deferred.current=[];cursor.current={id:run.id+":"+run.chapter_id+":"+run.attempt_number,ids:new Set(run.events.map(e=>e.id))};
   setRevealed(new Set(run.events.map(e=>e.id)));return;
  }
  let fresh=run.events.filter(e=>belongs(e)&&!cursor.current.ids.has(e.id));
  const scope=run.id+":"+run.chapter_id+":"+run.attempt_number;
  if(cursor.current.id!==scope){fresh=(run.revision===0||newChapter.current)&&!run.reviewing?run.events.filter(belongs):[];newChapter.current=false;}
  if(sequenceRef.current&&cursor.current.id!==scope){
   const freshIds=new Set(fresh.map(e=>e.id));
   setRevealed(old=>new Set([...old,...run.events.filter(e=>!freshIds.has(e.id)).map(e=>e.id)]));
  }
  cursor.current={id:scope,ids:new Set(run.events.map(e=>e.id))};
  if(sequenceRef.current){
   if(mode==="silent"){deferred.current=[...new Map([...deferred.current,...fresh].map(e=>[e.id,e])).values()];return;}
   if(active){const waiting=deferred.current.filter(belongs);deferred.current=[];const all=[...waiting,...fresh];const next=chapterSequence(run,all,automatic);
    const queued=new Set(next.map(e=>e.id));setRevealed(old=>new Set([...old,...all.filter(e=>!queued.has(e.id)).map(e=>e.id)]));
    if(next.length)lane.current?.enqueue(next);
   }
   return;
  }
  if(mode==="silent"){
   const next=spokenBeat(autoVoiceEvents(fresh,"characters"));
   if(next.length)deferred.current=next;
  }else if(automatic&&active&&language!=="off"){
   const waiting=deferred.current.filter(belongs);deferred.current=[];
   const next=spokenBeat([...autoVoiceEvents(fresh,mode),...waiting]);
   if(next.length){lane.current?.cancel();lane.current?.enqueue(next);}
  }
 },[run,automatic,active,language,mode]);
 useEffect(()=>{if(!active)lane.current?.cancel();},[active]);
 useEffect(()=>()=>lane.current?.cancel(),[]);
 useEffect(()=>{
  const update=()=>{const a=audio.current;if(!a)return;try{const v=JSON.parse(localStorage.getItem("moonfall_audio_levels")||"{}"),e=current.current?.events.find(e=>e.id===playing);a.mixer.setVolume((v.master??.65)*(e?.type==="NARRATION"?(v.narrator??.8):(v.character??.8)));}catch{}};
  window.addEventListener("moonfall-levels",update);return()=>window.removeEventListener("moonfall-levels",update);
 },[playing]);
 const pendingSequence=!!sequence&&!!run&&!run.reviewing&&active&&mode!=="silent"&&(queueBusy||!!playing||!!preparing||chapterSequence(run!,[...deferred.current,...(run?.events||[]).filter(e=>belongs(e)&&!cursor.current.ids.has(e.id))],automatic).length>0);
 const hiddenEventIds=new Set(sequence&&run&&!run.reviewing?concealedSequenceEvents(run,revealed):[]);
 const waitingForDialogue=pendingSequence||!run?.reviewing&&active&&automatic&&language!=="off"&&mode!=="silent"&&(queueBusy||!!playing||!!preparing||deferred.current.some(belongs)||spokenBeat(autoVoiceEvents((run?.events||[]).filter(e=>belongs(e)&&!cursor.current.ids.has(e.id)),mode)).length>0);
 return{hiddenEventIds,waitingForDialogue,narrating:!!run?.events.some(e=>(e.id===playing||e.id===preparing)&&e.type==="NARRATION"),language,setLanguage:(value:string)=>{if(sequenceRef.current)stopAudio();else lane.current?.cancel();setLanguageState(value);},automatic,setAutomatic:(value:boolean)=>{setAutomatic(value);if(!value){if(sequenceRef.current)stopAudio();else lane.current?.cancel();}},playing,error,clearError:()=>setError(""),listen:(e:WorldEvent)=>{if(playing===e.id){if(sequenceRef.current)stopAudio();else lane.current?.cancel();}else lane.current?.enqueue([e],true);},stop:()=>lane.current?.cancel()};
}
