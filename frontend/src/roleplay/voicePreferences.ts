import { useEffect, useRef, useState } from "react";
import type { Message } from "./types";
export function shouldAutoplaySpeech(characterCount: number) {
  return characterCount === 1;
}
export function playbackMessage(id:string, automatic:boolean, messages:Message[], prepared:Message|undefined, greeting:Message|null) {
  const rendered=messages.find(item=>item.id===id);
  // Stream metadata arrives before React commits the updated draft.
  // An explicit interruption always wins over cached preparation.
  if(rendered?.interrupted)return rendered;
  return (automatic ? prepared || rendered : rendered || prepared) ||
    (greeting?.id===id ? greeting : undefined);
}
export function canSpeak(message:Message) {
  if(message.interrupted)return false;
  if(typeof message.speech_supported==="boolean")return message.speech_supported;
  // Compatibility with older responses; never assume Latin text is English.
  const text=message.text.replace(/\*\*[^*]+\*\*|\*[^*]+\*/g," ");
  if(/[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af\u1000-\u109f\u0600-\u06ff\u0400-\u04ff]/u.test(text))return false;
  return /[ăâđêôơư]|\b(hello|thanks|please|what|how|you|the|and|are)\b/iu.test(text);
}
export function useCharacterVolumes(userId:string|undefined,api:string,headers:()=>Record<string,string>) {
  const [volumes,setVolumes]=useState<Record<string,number>>({});
  const timers=useRef(new Map<string,ReturnType<typeof setTimeout>>());
  const scope=useRef(userId);scope.current=userId;
  useEffect(()=>{
    setVolumes({});const controller=new AbortController();
    if(userId)void fetch(api+"/v1/roleplay/voice-preferences",{headers:headers(),signal:controller.signal})
      .then(async response=>response.ok?response.json():{}).then(data=>{
        if(controller.signal.aborted)return;
        const valid:Record<string,number>={};
        for(const [key,val] of Object.entries(data))if(typeof val==="number"&&val>=0&&val<=1)valid[key]=val;
        setVolumes(current=>({...valid,...current}));
      }).catch(()=>{});
    return ()=>{controller.abort();for(const timer of timers.current.values())clearTimeout(timer);timers.current.clear();};
  },[userId,api]);
  function update(id:string,value:number) {
    const volume=Math.max(0,Math.min(1,value));setVolumes(current=>({...current,[id]:volume}));
    const previous=timers.current.get(id);if(previous)clearTimeout(previous);
    const owner=userId;
    timers.current.set(id,setTimeout(()=>{
      timers.current.delete(id);if(scope.current!==owner)return;
      void fetch(api+"/v1/roleplay/characters/"+encodeURIComponent(id)+"/volume",{method:"PUT",headers:{...headers(),"Content-Type":"application/json"},body:JSON.stringify({volume})}).catch(()=>{});
    },300));
  }
  return {volumes,update};
}
