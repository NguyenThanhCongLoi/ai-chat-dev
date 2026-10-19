import {prepareChapterSpeech} from "./chapterSpeechMedia";
import {useEffect,useState} from "react";
import type {AdventureRun} from "./adventureTypes";
import {prepareIntroVideo} from "./worldIntroMedia";
import {prepareChapterImage} from "./chapterImageMedia";
export function chapterResourcePlan(run:AdventureRun){
 const videos=new Set<string>(run.chapter_media||[]);
 if(!run.intro_seen)videos.add(run.intro_asset);
 const memory="memory_video_"+run.chapter_id.slice(-2);videos.add(memory);
 const perChapter:Record<string,string[]>={selene_01:["enter_ruins_video"]};
 for(const id of perChapter[run.chapter_id]||[])videos.add(id);
 for(const key of (run.chapter_id==="selene_08"?["CHAPTER_COMPLETE"]:[])){
  const id=run.visual_events[key]?.cinematic;if(id)videos.add(id);
 }
 // Decode all backgrounds/portraits/patches in this chapter; do not download later chapters.
 const tasks:{url:string;type:"image"|"video"}[]=Object.values(run.assets).filter(a=>a.type==="IMAGE").map(a=>({url:a.url,type:"image" as const}));
 const saveData=!!(navigator as Navigator&{connection?:{saveData?:boolean}}).connection?.saveData;
 if(!saveData&&!matchMedia("(prefers-reduced-motion: reduce)").matches){
  for(const id of videos){const asset=run.assets[id];if(asset?.type==="VIDEO"&&!run.reviewing)tasks.push({url:asset.url,type:"video"});}
 }
 return tasks;
}
export function chapterPreparationKey(run:AdventureRun|null){return run?[run.id,run.attempt_number,run.chapter_id,run.config_revision,run.speech_revision,run.content_language].join(":"):"";}
export function useChapterResources(run:AdventureRun|null){
 const key=chapterPreparationKey(run);
 const [state,setState]=useState({key:"",progress:0,ready:false,failed:0,audioFailed:false,errorKind:""});
 const [retry,setRetry]=useState(0);
 useEffect(()=>{
  if(!run)return;
  let live=true;const tasks=chapterResourcePlan(run),progress=Array(tasks.length+1).fill(0);let failed=0,audioFailed=false,errorKind="";
  const update=()=>{if(live)setState({key,progress:Math.min(.99,progress.reduce((a,b)=>a+b,0)/progress.length),ready:false,failed,audioFailed,errorKind});};
  update();
  let cursor=0;
  const workers=Array.from({length:Math.min(4,tasks.length)},async()=>{
   while(cursor<tasks.length){
    const i=cursor++,task=tasks[i];
    try{
     if(task.type==="video")await prepareIntroVideo(task.url,value=>{progress[i]=value;update();});
     else await prepareChapterImage(task.url);
    }catch(error){console.warn("World media preparation failed",task.type,task.url,error);failed++;errorKind||=task.type;}
    finally{progress[i]=1;update();}
   }
  });
  void Promise.all([...workers,(run.reviewing?Promise.resolve():prepareChapterSpeech(run,value=>{progress[tasks.length]=value;update();})).catch(error=>{audioFailed=true;failed++;errorKind=error?.reason==="unprepared"?"audio_unprepared":"audio";}).finally(()=>{progress[tasks.length]=1;})]).then(()=>{
   if(live)setState({key,progress:failed?Math.min(.99,progress.reduce((a,b)=>a+b,0)/progress.length):1,ready:failed===0,failed,audioFailed,errorKind});
  });
  return()=>{live=false;};
 },[key,retry]);
 // Only recheck the prepared catalog; entering World never starts TTS generation.
 useEffect(()=>{
  if(state.key!==key||state.errorKind!=="audio_unprepared"||retry>=4)return;
  const timer=setTimeout(()=>setRetry(n=>n+1),3000);
  return()=>clearTimeout(timer);
 },[state.key,state.errorKind,key,retry]);
 return {ready:!!run&&state.key===key&&state.ready,progress:state.key===key?state.progress:0,failed:state.failed,audioFailed:state.key===key&&state.audioFailed,errorKind:state.key===key?state.errorKind:"",retry:()=>setRetry(v=>v+1)};
}
