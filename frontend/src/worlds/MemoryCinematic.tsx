import {useRef} from "react";
import {CinematicPlayer,type CinematicCue} from "./WorldCinematics";
import type {AdventureRun} from "./adventureTypes";
import {worldUi} from "./worldUi";

/** Video is presentation only. Narration is text-first and plays on explicit request. */
export function MemoryCinematic({run,active,onDone,onPlaying}:{
 run:AdventureRun;active:boolean;onDone:()=>void;onPlaying:(playing:boolean)=>void;
}){
 const video=run.memory_video!;
 const narration=run.events.slice().reverse().find(e=>e.type==="NARRATION"&&e.presentation!=="archive");
 const stopped=useRef(false);
 function finish(){if(stopped.current)return;stopped.current=true;onPlaying(false);onDone();}
 const t=(vi:string,en:string)=>worldUi(vi,en,run.content_language);
 const cue:CinematicCue={key:video.key,asset:{id:video.id,type:"VIDEO",url:video.url,fallback:video.fallback,loop:false,duration:video.duration},duration:video.duration,skippable:true};
 return <CinematicPlayer cue={cue} language={run.content_language} active={active} endTone={run.chapter_id==="selene_01"&&!run.reviewing?"white":undefined} onDone={finish} onPlaying={onPlaying}>
  {narration&&<div className="maCinematicNarration"><small>{t("DẪN TRUYỆN","NARRATION")}</small><p>{narration.text}</p></div>}
 </CinematicPlayer>;
}
