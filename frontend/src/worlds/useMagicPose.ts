import {useEffect,useRef,useState} from "react";
import type {ChapterRun} from "./moonfallTypes";
/** Use the supplied casting portrait briefly on a new magic event, never on history replay. */
export function useMagicPose(run:ChapterRun|null,active:boolean){
 const [casting,setCasting]=useState(false),cursor=useRef({scope:"",ids:new Set<string>()});
 const timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
 useEffect(()=>{
  const scope=run?run.id+":"+((run as ChapterRun&{chapter_id?:string}).chapter_id||""):"";
  if(!run||cursor.current.scope!==scope){
   cursor.current={scope,ids:new Set(run?.events.map(e=>e.id)||[])};
   clearTimeout(timer.current);setCasting(false);return;
  }
  const fresh=run.events.filter(e=>!cursor.current.ids.has(e.id));
  cursor.current.ids=new Set(run.events.map(e=>e.id));
  if(!active){clearTimeout(timer.current);setCasting(false);return;}
  if(fresh.some(e=>["MAGIC_ACTIVATED","MAGIC_SEAL_ACTIVATE","VAULT_AWAKEN"].includes(e.visual_event))){
   clearTimeout(timer.current);setCasting(true);timer.current=setTimeout(()=>setCasting(false),2200);
  }
 },[run,active]);
 useEffect(()=>()=>clearTimeout(timer.current),[]);
 return casting;
}
