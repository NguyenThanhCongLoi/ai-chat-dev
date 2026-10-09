import {useEffect,useRef,useState} from "react";
import {API,authHeaders} from "./api";
import {ActionSoundDetector,type ActionSound} from "./actionSoundDetector";
let context:AudioContext|undefined;
let owner:string|undefined;
let sounds:ActionSound[]=[];
let volume=.35;
let pending:Promise<void>|undefined;
let version=0;
const buffers=new Map<string,AudioBuffer>();
function audioContext(){return context??=new AudioContext();}
export function activateActionSounds(){void audioContext().resume().catch(()=>{});}
export function prepareActionSounds(userId:string,refresh=false){
  if(owner!==userId){owner=userId;version++;pending=undefined;sounds=[];buffers.clear();}
  if(pending)return pending;
  if(sounds.length&&!refresh)return Promise.resolve();
  const epoch=version;
  pending=(async()=>{
    try{
      const response=await fetch(API+"/v1/roleplay/action-sounds",{headers:authHeaders(),cache:"no-store",signal:AbortSignal.timeout(12000)});
      if(!response.ok)return;
      const data=await response.json();
      if(epoch!==version)return;
      volume=data.volume;sounds=data.sounds.slice(0,120);
      const live=new Set(sounds.map(item=>item.url));
      for(const url of buffers.keys())if(!live.has(url))buffers.delete(url);
      let cursor=0;
      await Promise.all(Array.from({length:2},async()=>{
        while(cursor<sounds.length){
          const item=sounds[cursor++];
          if(buffers.has(item.url))continue;
          try{
            const response=await fetch(API+item.url,{signal:AbortSignal.timeout(15000)});
            if(!response.ok)continue;
            const bytes=await response.arrayBuffer();
            if(bytes.byteLength>20*1024*1024)continue;
            const buffer=await audioContext().decodeAudioData(bytes);
            if(epoch===version){
              if(buffer.duration<=3)buffers.set(item.url,buffer);
              else{
                const clip=audioContext().createBuffer(buffer.numberOfChannels,Math.ceil(buffer.sampleRate*3),buffer.sampleRate);
                for(let channel=0;channel<buffer.numberOfChannels;channel++)clip.copyToChannel(buffer.getChannelData(channel).subarray(0,clip.length),channel);
                buffers.set(item.url,clip);
              }
            }
          }catch{/* Unavailable sounds must never delay or fail the conversation. */}
        }
      }));
    }catch{/* The library is optional; retry on the next room opening. */}
    finally{if(epoch===version)pending=undefined;}
  })();
  return pending;
}
export function useActionSounds(roomId:string|null,userId:string|undefined,enabled=true){
  const allowed=useRef(enabled);allowed.current=enabled;
  const [available,setAvailable]=useState(false);
  const [ready,setReady]=useState(false);
  const detectors=useRef(new Map<string,ActionSoundDetector>());
  const playing=useRef(new Set<AudioBufferSourceNode>());
  const last=useRef(new Map<string,string>());
  const pendingSounds=useRef(new Map<string,number>());
  const epoch=useRef(0);
  const retry=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
  function stop(){
    epoch.current++;
    clearTimeout(retry.current);retry.current=undefined;
    pendingSounds.current.clear();
    for(const detector of detectors.current.values())detector.commit();
    for(const source of playing.current)try{source.stop();}catch{}
    playing.current.clear();
  }
  function drain(){
    if(!allowed.current||!roomId||owner!==userId||document.visibilityState==="hidden"||window.frameElement?.getAttribute("aria-hidden")==="true")return;
    for(const [id,expires] of pendingSounds.current){
      if(Date.now()>expires){pendingSounds.current.delete(id);continue;}
      if(playing.current.size>=1)break;
      const detector=detectors.current.get(id);
      if(!detector||detector.done){pendingSounds.current.delete(id);continue;}
      // Consider only decoded files. Missing clips never consume this reply's allowance.
      const group=detector.feed("",sounds.filter(item=>buffers.has(item.url)),false)[0];
      if(!group)continue;
      const ctx=audioContext();
      if(ctx.state!=="running")continue;
      const key=group.map(item=>item.id).sort().join(",");
      const fresh=group.filter(item=>item.id!==last.current.get(key));
      const candidates=fresh.length?fresh:group;
      const sound=candidates[Math.floor(Math.random()*candidates.length)];
      const source=ctx.createBufferSource(),gain=ctx.createGain();
      source.buffer=buffers.get(sound.url)!;
      gain.gain.value=Math.max(0,Math.min(1,volume*sound.volume));
      if(gain.gain.value===0){pendingSounds.current.delete(id);continue;}
      source.connect(gain);gain.connect(ctx.destination);
      const duration=Math.min(source.buffer.duration,3);
      const fade=Math.min(.05,duration/2);
      gain.gain.setValueAtTime(gain.gain.value,ctx.currentTime);
      gain.gain.setValueAtTime(gain.gain.value,ctx.currentTime+duration-fade);
      gain.gain.linearRampToValueAtTime(0,ctx.currentTime+duration);
      const playbackEpoch=epoch.current;
      source.onended=()=>{
        playing.current.delete(source);source.disconnect();gain.disconnect();
        if(playbackEpoch===epoch.current)drain();
      };
      try{
        source.start(0,0,duration);
        detector.commit();pendingSounds.current.delete(id);
        playing.current.add(source);last.current.set(key,sound.id);
      }catch{source.disconnect();gain.disconnect();}
    }
    if(pendingSounds.current.size&&!retry.current){
      const currentEpoch=epoch.current;
      retry.current=setTimeout(()=>{
        retry.current=undefined;
        if(currentEpoch===epoch.current)drain();
      },150);
    }
  }
  useEffect(()=>{
    stop();detectors.current.clear();last.current.clear();setReady(false);setAvailable(false);
    let active=true;
    if(roomId&&userId)void prepareActionSounds(userId,true).then(()=>{
      if(active){setReady(true);setAvailable(sounds.some(item=>buffers.has(item.url)));drain();}
    });
    return()=>{active=false;stop();};
  },[roomId,userId]);
  useEffect(()=>{if(!enabled)stop();},[enabled]);
  useEffect(()=>{
    const hidden=()=>{if(document.visibilityState==="hidden")stop();};
    document.addEventListener("visibilitychange",hidden);
    return()=>document.removeEventListener("visibilitychange",hidden);
  },[]);
  function record(messageId:string){
    let detector=detectors.current.get(messageId);
    if(!detector){
      if(detectors.current.size>=32){
        const first=detectors.current.keys().next().value!;
        detectors.current.delete(first);pendingSounds.current.delete(first);
      }
      detector=new ActionSoundDetector();detectors.current.set(messageId,detector);
    }
    return detector;
  }
  function feed(messageId:string,delta:string){
    if(!roomId||owner!==userId)return;
    const detector=record(messageId);
    if(!allowed.current){detector.commit();return;}
    if(detector.done)return;
    detector.feed(delta,sounds,false);
    if(!pendingSounds.current.has(messageId))pendingSounds.current.set(messageId,Date.now()+4000);
    drain();
  }
  function finish(messageId:string,text:string){
    if(!roomId||owner!==userId)return;
    const detector=record(messageId);
    if(!allowed.current){detector.commit();return;}
    if(detector.done)return;
    detector.replaceText(text);
    if(!pendingSounds.current.has(messageId))pendingSounds.current.set(messageId,Date.now()+4000);
    drain();
  }
  return{feed,finish,stop,available,ready};
}
