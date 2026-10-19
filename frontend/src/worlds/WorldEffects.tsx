import {useEffect,useLayoutEffect,useRef,useState,type RefObject,type CSSProperties} from "react";
import type {ChapterRun} from "./moonfallTypes";
import {resolveWorldEffects,type EffectCue} from "./worldEffectRegistry";
import "./worldEffects.css";
/** Scoped layer. Saved history never replays on loading or returning to the World. */
export function WorldEffects({run,active,scope}:{run:ChapterRun|null;active:boolean;scope:RefObject<HTMLDivElement|null>}){
 const cursor=useRef<{run:string;ids:Set<string>}>({run:"",ids:new Set()});
 const [cues,setCues]=useState<EffectCue[]>([]);
 useEffect(()=>{
  if(!run){cursor.current={run:"",ids:new Set()};setCues([]);return;}
  if(cursor.current.run!==run.id){cursor.current={run:run.id,ids:new Set(run.events.map(e=>e.id))};setCues([]);return;}
  const fresh=run.events.filter(e=>!cursor.current.ids.has(e.id));
  cursor.current.ids=new Set(run.events.map(e=>e.id));
  if(!active||document.hidden){setCues([]);return;}
  const next=fresh.flatMap(e=>resolveWorldEffects(e,run));
  if(next.length)setCues(previous=>[...previous,...next].slice(-12));
 },[run,active]);
 useEffect(()=>{const hide=()=>{if(document.hidden)setCues([]);};document.addEventListener("visibilitychange",hide);return()=>document.removeEventListener("visibilitychange",hide);},[]);
 return active?<div className="worldEffects" aria-hidden="true">{cues.map(cue=><WorldEffect key={cue.id} cue={cue} scope={scope} onDone={()=>setCues(old=>old.filter(c=>c.id!==cue.id))}/>)}</div>:null;
}
export function WorldEffect({cue,scope,onDone}:{cue:EffectCue;scope:RefObject<HTMLDivElement|null>;onDone:()=>void}){
 const [position,setPosition]=useState({left:"50%",top:"42%"});
 const done=useRef(onDone);done.current=onDone;
 useEffect(()=>{const timer=window.setTimeout(()=>done.current(),cue.duration);return()=>clearTimeout(timer);},[cue.id,cue.duration]);
 useLayoutEffect(()=>{
  function locate(){
   const root=scope.current;if(!root)return;
   const target=Array.from(root.querySelectorAll<HTMLElement>("[data-world-target]")).find(e=>e.dataset.worldTarget===cue.target&&e.getClientRects().length);
   if(!target)return;
   const box=target.getBoundingClientRect(),base=root.getBoundingClientRect();
   const x=box.left-base.left+box.width/2,y=box.top-base.top+box.height/2;
   if(x>=0&&x<=base.width&&y>=0&&y<=base.height)setPosition({left:x+"px",top:y+"px"});
  }
  locate();window.addEventListener("resize",locate);return()=>window.removeEventListener("resize",locate);
 },[cue.target,scope]);
 return <div className={"worldEffect worldEffect--"+cue.type} data-effect={cue.type} data-reduced-motion={cue.reducedMotion} style={{...position,"--world-effect-duration":cue.duration+"ms"} as CSSProperties}>
  {cue.type==="MANGA_REACTION"||cue.type==="CHARACTER_REALIZATION"?<b>!</b>:cue.type==="THOUGHT_BUBBLE"?<span className="worldThoughtDots">···</span>:
  <svg viewBox="0 0 120 120" fill="none"><circle cx="60" cy="60" r="30"/><circle cx="60" cy="60" r="47"/><path d="M60 8V28M60 92V112M8 60H28M92 60H112M23 23L37 37M83 83L97 97M23 97L37 83M83 37L97 23"/><path className="worldEffectRune" d="M60 29L86 76H34ZM48 39L72 83M72 39L48 83"/></svg>}
 </div>;
}
