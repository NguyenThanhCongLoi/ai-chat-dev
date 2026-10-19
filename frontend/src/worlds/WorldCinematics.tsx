import {chapterCinematicAllowed} from "./chapterPresentation";
import {useEffect,useRef,useState,type ReactNode} from "react";
import type {Asset,ChapterRun} from "./moonfallTypes";
import "./worldCinematics.css";
import {prepareIntroVideo,preparedVideoSource} from "./worldIntroMedia";
import {storedLanguage} from "../i18n";
import {worldUi} from "./worldUi";
export type CinematicCue={key:string;asset:Asset;skippable:boolean;duration:number};
export function cinematicCue(run:ChapterRun,event:{id:string;visual_event:string}):CinematicCue|null{
 const config=run.visual_events[event.visual_event];
 const id=event.visual_event==="LOCATION_ENTER"?(run.locations.find(p=>p.id===run.location)?.cinematic||config?.cinematic):config?.cinematic;
 const asset=id?run.assets[id]:undefined;
 if(!asset||asset.type!=="VIDEO"||!config)return null;
 return {key:event.id,asset,skippable:config.skippable,duration:Math.max(.5,Math.min(30,asset.duration||config.duration||8))};
}
/** React-owned presentation. Completion never modifies quests, clues or rewards. */
export function CinematicPlayer({cue,active,onDone,onPlaying,onDuration,children,endTone,language=storedLanguage()}:{endTone?:"white";language?:string;cue:CinematicCue;active:boolean;onDone:()=>void;onPlaying:(value:boolean)=>void;children?:ReactNode;onDuration?:(seconds:number)=>void}){
 const video=useRef<HTMLVideoElement>(null),finishRef=useRef(onDone);finishRef.current=onDone;
 const playingRef=useRef(onPlaying);playingRef.current=onPlaying;
 const [failed,setFailed]=useState(false),[finished,setFinished]=useState(false),[source,setSource]=useState(()=>preparedVideoSource(cue.asset.url)),[fading,setFading]=useState(false);
 const ended=useRef(false),fadeTimer=useRef<number|undefined>(undefined);
 const finish=()=>{if(ended.current)return;ended.current=true;video.current?.pause();const complete=()=>{setFinished(true);playingRef.current(false);finishRef.current();};if(endTone==="white"&&!matchMedia("(prefers-reduced-motion: reduce)").matches&&active){setFading(true);fadeTimer.current=window.setTimeout(complete,550);}else complete();};
 useEffect(()=>{
  let live=true;
  if(!active||matchMedia("(prefers-reduced-motion: reduce)").matches||(navigator as Navigator&{connection?:{saveData?:boolean}}).connection?.saveData)return;
  setSource(preparedVideoSource(cue.asset.url));
  void prepareIntroVideo(cue.asset.url).then(url=>{if(live)setSource(url);}).catch(()=>{if(live){setFailed(true);finish();}});
  return()=>{live=false;};
 },[cue.asset.url]);
 const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
 const saveData=(navigator as Navigator&{connection?:{saveData:boolean}}).connection?.saveData;
 useEffect(()=>()=>clearTimeout(fadeTimer.current),[]);
 useEffect(()=>{
  if(!active||reduced||saveData){finish();return;}
  if(!source)return;
  playingRef.current(true);
  let lastProgress=Date.now();
  const time=()=>{lastProgress=Date.now();};
  video.current?.addEventListener("timeupdate",time);
  const timeout=window.setInterval(()=>{if(Date.now()-lastProgress>15000)finish();},1000);
  const hide=()=>{if(document.hidden){finish();}};
  document.addEventListener("visibilitychange",hide);
  return()=>{clearInterval(timeout);video.current?.removeEventListener("timeupdate",time);document.removeEventListener("visibilitychange",hide);playingRef.current(false);};
 },[cue.key,active,reduced,saveData,source]);
 if(!active||reduced||saveData||finished)return null;
 return <div className={"worldCinematic"+(failed?" worldCinematicFallback":"")+(fading?" worldCinematicWhite":"")} data-cinematic={cue.asset.id}>
  {!source&&!failed&&<span role="status">…</span>}
  {!failed&&source&&<video ref={video} src={source} autoPlay muted playsInline loop={cue.asset.loop} preload="auto" aria-hidden="true"
   onPlaying={()=>playingRef.current(true)} onEnded={finish} onError={()=>{setFailed(true);finish();}}
   onLoadedMetadata={()=>{onDuration?.(video.current?.duration||cue.duration);void video.current?.play().catch(()=>{setFailed(true);finish();});}}/>}
  {failed&&<div className="worldCinematicImageFallback" aria-hidden="true"/>}
  {children}{fading&&<div className="worldCinematicWhiteLayer" aria-hidden="true"/>}{cue.skippable&&!fading&&<button type="button" className="worldCinematicSkip" aria-label={worldUi("Bỏ qua đoạn phim","Skip cinematic",language)} onClick={finish}>{worldUi("Bỏ qua đoạn phim","Skip cinematic",language)} →</button>}
 </div>;
}
export function WorldCinematics({run,active,onPlaying,onDone,hold=false,onPending}:{run:ChapterRun|null;active:boolean;onPlaying:(value:boolean)=>void;onDone?:()=>void;hold?:boolean;onPending?:(value:boolean)=>void}){
 const cursor=useRef({run:"",ids:new Set<string>()}),[queue,setQueue]=useState<CinematicCue[]>([]);
 useEffect(()=>{
  if(!run){setQueue([]);return;}
  let events=run.events;
  const scope=run.id+":"+((run as ChapterRun&{chapter_id?:string}).chapter_id||"")+":"+((run as ChapterRun&{attempt_number?:number}).attempt_number||1);
  if(cursor.current.run!==scope){
   setQueue([]);cursor.current={run:scope,ids:new Set(run.events.map(e=>e.id))};
   events=run.intro_seen?[]:run.events.filter(e=>e.visual_event==="WORLD_INTRO");
  }else{
   events=events.filter(e=>!cursor.current.ids.has(e.id));
   cursor.current.ids=new Set(run.events.map(e=>e.id));
  }
  if(!active||document.hidden){setQueue([]);return;}
  const cues=events.filter(e=>chapterCinematicAllowed(run,e)).map(e=>cinematicCue(run,e)).filter((c):c is CinematicCue=>!!c).filter((c,i,all)=>all.findIndex(other=>other.asset.id===c.asset.id)===i);
  setQueue(old=>[...old.filter(c=>!(run.intro_seen&&c.asset.id===run.intro_asset)),...cues].filter((c,i,all)=>all.findIndex(other=>other.asset.id===c.asset.id)===i).slice(0,1));
 },[run,active]);
 useEffect(()=>{onPending?.(active&&queue.length>0);return()=>onPending?.(false);},[active,queue.length,onPending]);
 // Fetch metadata for at most one likely upcoming clip; no preload-everything.
 const likely=run?.locations.find(p=>!p.locked&&p.id!==run.location&&p.cinematic);
 const next=likely?.cinematic?run?.assets[likely.cinematic]:undefined;
 return <>{next&&active&&run?.intro_seen&&<video className="worldCinematicPreload" src={next.url} preload="metadata" muted aria-hidden="true"/>}
  {queue[0]&&active&&!hold&&<CinematicPlayer key={queue[0].key} cue={queue[0]} active={active} onPlaying={onPlaying} onDone={()=>{setQueue(old=>old.slice(1));onDone?.();}}/>}</>;
}
