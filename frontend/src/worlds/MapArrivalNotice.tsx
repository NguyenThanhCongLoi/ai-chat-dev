import {useEffect,useRef,useState} from "react";
/** Navigation is a short visual notice, never a transcript or voice event. */
export function MapArrivalNotice({mapKey,title,active}:{mapKey:string;title:string;active:boolean}){
 const previous=useRef(""),[visible,setVisible]=useState(false);
 useEffect(()=>{
  if(!active){setVisible(false);return;}
  if(previous.current===mapKey)return;
  previous.current=mapKey;setVisible(true);
  const timer=window.setTimeout(()=>setVisible(false),1800);
  return()=>clearTimeout(timer);
 },[mapKey,active]);
 return visible?<div className="maMapArrival" role="status" aria-live="polite"><span>{title}</span></div>:null;
}
