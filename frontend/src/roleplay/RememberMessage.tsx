import {useEffect,useState} from "react";
import {api} from "./api";
import {storedLanguage,translateUiText} from "../i18n";

// A whole room shares one request. Never fetch once per message bubble.
const requests=new Map<string,Promise<Set<string>>>();
const eventName="roleplay-memories-changed";
window.addEventListener(eventName,()=>requests.clear());
function roomPins(roomId:string){
 const key=(localStorage.getItem("auth_token")||"")+"|"+roomId;
 let pending=requests.get(key);
 if(!pending){
  if(requests.size>20)requests.clear();
  pending=api<{message_ids:string[]}>("/v1/roleplay/rooms/"+encodeURIComponent(roomId)+"/pins").then(r=>new Set(r.message_ids));
  requests.set(key,pending);
 }
 return pending;
}
export function RememberMessage({roomId,messageId,busy}:{roomId:string;messageId:string;busy:boolean}){
 const[pinned,setPinned]=useState(false),[pending,setPending]=useState(false),[error,setError]=useState("");
 const t=(s:string)=>translateUiText(s,storedLanguage());
 useEffect(()=>{let live=true;const refresh=()=>{void roomPins(roomId).then(ids=>{if(live)setPinned(ids.has(messageId));}).catch(()=>{});};refresh();window.addEventListener(eventName,refresh);return()=>{live=false;window.removeEventListener(eventName,refresh);};},[roomId,messageId]);
 async function remember(){if(pending||busy)return;const next=!pinned;setPinned(next);setPending(true);setError("");try{
  await api("/v1/roleplay/rooms/"+encodeURIComponent(roomId)+"/remember","POST",{message_id:messageId,pinned:next});
  window.dispatchEvent(new Event(eventName));
 }catch(e){setPinned(!next);setError(e instanceof Error?e.message:String(e));}finally{setPending(false);}}
 return <span className="rpMessagePin"><button type="button" className="regenerate" disabled={busy||pending} title={error||t(pinned?"Bỏ ghim":"Ghim vào ký ức")} aria-label={t(pinned?"Bỏ ghim":"Ghim vào ký ức")} onClick={()=>void remember()}>{pinned?"★":"☆"} {pending?"…":t(pinned?"Đã ghim":"Ghim")}</button>{error&&<small role="alert">{error}</small>}</span>;
}
