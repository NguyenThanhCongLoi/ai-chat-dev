import {playReactionClip} from "./reactionPlayback";
import {useEffect,useRef,useState} from "react";
import {cachedReactions,clearReactionCache,prepareCharacterReactions,type PreparedReaction as Prepared} from "./reactionCache";
export function useReactionSounds(roomId:string|null,userId:string|undefined,characterIds:string[]){
  const signature=JSON.stringify(characterIds);
  const [ready,setReady]=useState(false),[revision,setRevision]=useState(0);
  const enabledRef=useRef<Record<string,boolean>>({});
  const clips=useRef(new Map<string,Prepared[]>());
  const requests=useRef(new Map<string,Promise<Prepared[]>>());
  const audio=useRef<HTMLAudioElement|null>(null);
  const seen=useRef(new Set<string>());
  const playbackTasks=useRef(new Map<string,Promise<void>>());
  const playbackQueue=useRef<Promise<void>>(Promise.resolve());
  const last=useRef<string|null>(null);
  const sequence=useRef(0);
  const playbackEpoch=useRef(0);
  const lastPlayed=useRef(0);
  const openingDone=useRef<(()=>void)|null>(null);
  const loaded=useRef(new Set<string>());
  function stopPlayer(){audio.current?.pause();audio.current=null;openingDone.current?.();openingDone.current=null;}
  function stop(){++playbackEpoch.current;playbackQueue.current=Promise.resolve();stopPlayer();}
  useEffect(()=>{
    const epoch=++sequence.current;
    setReady(false);stop();seen.current.clear();playbackTasks.current.clear();playbackQueue.current=Promise.resolve();lastPlayed.current=0;
    clips.current.clear();requests.current.clear();loaded.current.clear();
    enabledRef.current=Object.fromEntries(characterIds.map(id=>[id,localStorage.getItem("reaction:"+userId+":"+id)!=="off"]));
    if(!userId)clearReactionCache();
    if(roomId&&userId){
      for(const id of characterIds.slice(0,8)){
        const prepared=cachedReactions(userId,id);
        if(prepared){clips.current.set(id,prepared);loaded.current.add(id);}
        requests.current.set(id,prepareCharacterReactions(userId,id).then(result=>{
          if(sequence.current===epoch){clips.current.set(id,result);loaded.current.add(id);}
          return result;
        }).catch(()=>[]));
      }
      if(characterIds.every(id=>loaded.current.has(id)))setReady(true);
      void Promise.all(requests.current.values()).then(()=>{if(sequence.current===epoch)setReady(true);});
    }
    return()=>{++sequence.current;stop();clips.current.clear();requests.current.clear();loaded.current.clear();};
  },[roomId,userId,signature]);
  useEffect(()=>{
    const stopHidden=()=>{if(document.visibilityState==="hidden")stop();};
    document.addEventListener("visibilitychange",stopHidden);
    return()=>document.removeEventListener("visibilitychange",stopHidden);
  },[]);
  function react(messageId:string,characterId:string,emotion:string,language?:string,voiceId?:string):Promise<void>{
    const pending=playbackTasks.current.get(messageId);
    if(pending)return pending;
    const epoch=sequence.current, generation=playbackEpoch.current;
    const task=playbackQueue.current.catch(()=>{}).then(()=>{
      if(epoch!==sequence.current||generation!==playbackEpoch.current)return;
      return performReaction(messageId,characterId,emotion,language,voiceId,generation);
    });
    playbackQueue.current=task;
    playbackTasks.current.set(messageId,task);
    if(playbackTasks.current.size>128)playbackTasks.current.delete(playbackTasks.current.keys().next().value!);
    return task;
  }
  async function performReaction(messageId:string,characterId:string,emotion:string,language:string|undefined,voiceId:string|undefined,generation:number){
    const epoch=sequence.current;
    if(!roomId||seen.current.has(messageId))return;
    seen.current.add(messageId);
    if(seen.current.size>128)seen.current.delete(seen.current.values().next().value!);
    if(!enabledRef.current[characterId])return;
    const options=clips.current.get(characterId)||await requests.current.get(characterId)||[];
    if(epoch!==sequence.current||generation!==playbackEpoch.current||!enabledRef.current[characterId]||document.visibilityState==="hidden"||window.frameElement?.getAttribute("aria-hidden")==="true")return;
    // Group clips are serialized above, so each speaker keeps their own beat.
    if(characterIds.length===1&&Date.now()-lastPlayed.current<4000)return;
    const target=options.some(clip=>clip.target===language)?language:options.some(clip=>clip.target==="shared")?"shared":options.some(clip=>clip.target==="en")?"en":"vi";
    let candidates=options.filter(clip=>clip.emotion===emotion&&clip.target===target&&(!voiceId||clip.voice_id===voiceId));

    if(!candidates.length)return;
    const fresh=candidates.filter(clip=>clip.id!==last.current);
    if(fresh.length)candidates=fresh;
    const clip=candidates[Math.floor(Math.random()*candidates.length)];
    stopPlayer();
    const player=clip.player;player.currentTime=0;
    player.volume=clip.volume;audio.current=player;
    last.current=clip.id;lastPlayed.current=Date.now();
    const playback=playReactionClip(player);
    openingDone.current=playback.cancel;
    await playback.finished;
    if(audio.current===player)audio.current=null;
    if(openingDone.current===playback.cancel)openingDone.current=null;
  }
  async function opening(characterId:string,language?:string,voiceId?:string){
    const epoch=sequence.current;
    if(!roomId||!enabledRef.current[characterId])return;
    if(epoch!==sequence.current)return;
    const options=clips.current.get(characterId)||[];
    const target=options.some(clip=>clip.target===language)?language:options.some(clip=>clip.target==="shared")?"shared":options.some(clip=>clip.target==="en")?"en":"vi";
    const candidates=options.filter(clip=>clip.emotion==="neutral"&&clip.target===target&&(!voiceId||clip.voice_id===voiceId));
    if(!candidates.length||epoch!==sequence.current||document.visibilityState==="hidden"||window.frameElement?.getAttribute("aria-hidden")==="true")return;
    stop();
    const clip=candidates[Math.floor(Math.random()*candidates.length)];
    const player=clip.player;player.currentTime=0;player.volume=clip.volume*.75;
    audio.current=player;last.current=clip.id;lastPlayed.current=Date.now();
    await new Promise<void>(resolve=>{
      let timer:number|undefined;
      const done=()=>{
        window.clearTimeout(timer);player.onended=player.onerror=null;player.pause();
        if(audio.current===player)audio.current=null;
        if(openingDone.current===done)openingDone.current=null;
        resolve();
      };
      openingDone.current=done;
      player.onended=player.onerror=done;
      timer=window.setTimeout(done,850);
      void player.play().catch(done);
    });
  }
  const enabled=characterIds.every(id=>enabledRef.current[id]!==false);
  function toggle(){
    const next=!enabled;
    for(const id of characterIds){
      enabledRef.current[id]=next;
      localStorage.setItem("reaction:"+userId+":"+id,next?"on":"off");
    }
    if(!next)stop();
    setRevision(revision+1);
  }
  const available=Array.from(clips.current.values()).some(entries=>entries.length>0);
  return{enabled,ready,available,toggle,react,opening,stop};
}
