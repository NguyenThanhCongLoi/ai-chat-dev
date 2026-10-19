import {readWorldJson} from "./worldHttp";
import "./entry.css";
import {useEffect,useState} from "react";
import {prepareWorldMetadata,playPreparedIntro} from "./worldIntroMedia";
let config:Promise<boolean>|undefined;
export function WorldEntry({characterId,className="",onOpen,active=false}:{characterId?:string;className?:string;onOpen?:(id?:string)=>void;active?:boolean}){
 const[enabled,setEnabled]=useState(false);
 useEffect(()=>{let live=true;config??=fetch("/v1/worlds/config").then(r=>r.ok?readWorldJson(r):null).then(v=>!!v?.enabled).catch(()=>false);void config.then(v=>{if(live)setEnabled(v);});return()=>{live=false;};},[]);
 useEffect(()=>{if(enabled&&!characterId)void prepareWorldMetadata().catch(()=>{});},[enabled,characterId]);
 if(!enabled)return null;
 const en=(localStorage.getItem("ui_language")||"vi")!=="vi";
 return <a className={"worldEntry "+className+(active?" active":"")} aria-current={active?"page":undefined} href={"/worlds"+(characterId?"?character="+encodeURIComponent(characterId):"")} onClick={e=>{
  if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
  if(onOpen){e.preventDefault();onOpen(characterId);if(!characterId&&!active)playPreparedIntro();}
  else if(window.parent!==window){e.preventDefault();window.parent.postMessage({type:"avibi-worlds-open",characterId},window.location.origin);}
 }}>✧ {en?(characterId?"Begin an adventure":"Worlds"):(characterId?"Bắt đầu phiêu lưu":"Thế giới")}</a>;
}
