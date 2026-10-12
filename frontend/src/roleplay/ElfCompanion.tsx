import {useEffect,useRef,useState} from "react";
import {API} from "./api";
import "./elf-companion.css";

export function ElfCompanion({talking,name}:{talking:boolean;name:string}) {
  const normal=useRef<HTMLVideoElement>(null),talk=useRef<HTMLVideoElement>(null);
  const [failed,setFailed]=useState(false);
  useEffect(()=>{
    const active=talking?talk.current:normal.current;
    const inactive=talking?normal.current:talk.current;
    inactive?.pause();
    if(active)active.currentTime=0;
    const resume=()=>{
      if(document.visibilityState==="hidden"||window.frameElement?.getAttribute("aria-hidden")==="true"){
        active?.pause();return;
      }
      void active?.play().catch(()=>{});
    };
    const observer=new MutationObserver(resume);
    if(window.frameElement)observer.observe(window.frameElement,{attributes:true,attributeFilter:["aria-hidden"]});
    resume();
    document.addEventListener("pointerdown",resume);
    document.addEventListener("visibilitychange",resume);
    return ()=>{active?.pause();observer.disconnect();document.removeEventListener("pointerdown",resume);document.removeEventListener("visibilitychange",resume);};
  },[talking]);
  return <div className="elfCompanion" data-companion-state={talking?"talk":"normal"} aria-label={name}>
    <video ref={normal} className={!talking?"active":""}
      src={API+"/character-images/elf_normal.webm"} loop muted playsInline preload="auto"
      aria-hidden="true" onError={()=>setFailed(true)}/>
    <video ref={talk} className={talking?"active":""}
      src={API+"/character-images/elf_talk.webm"} loop muted playsInline preload="auto"
      aria-hidden="true" onError={()=>setFailed(true)}/>
    {failed && <button className="btn" onClick={()=>{
      setFailed(false);normal.current?.load();talk.current?.load();
      void (talking?talk.current:normal.current)?.play().catch(()=>{});
    }}>Thử lại</button>}
  </div>;
}
