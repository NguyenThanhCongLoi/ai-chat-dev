import {useEffect,useRef,useState} from "react";
import {introCueBlob} from "./introNarrationMedia";
import {introVoiceRate} from "./introTiming";
import {hubText} from "./worldHubCopy";
import {local,type LocalText} from "./moonfallTypes";
export type IntroNarrationConfig={audio_version?:string;revision:number;enabled:boolean;music_gain:number;duck_gain:number;voice_gain:number;duration_seconds?:number;silent_windows?:{id:string;start:number;end:number;label:string}[];cues:{id:string;start:number;end:number;text:LocalText}[]};
export default function IntroNarration({player,config,active,volume,subtitleLanguage,clipId,onReady}:{player:HTMLVideoElement|null;config:IntroNarrationConfig;active:boolean;volume:number;subtitleLanguage:string;clipId:string;onReady:(ready:boolean)=>void}){
 const [language,setLanguage]=useState(subtitleLanguage==="vi"?"vi":"en"),[caption,setCaption]=useState(""),[available,setAvailable]=useState(true);
 const mix=useRef(volume);mix.current=volume;
 const voice=useRef<HTMLAudioElement|null>(null);
 const t=(vi:string,en:string)=>hubText(vi,en,subtitleLanguage);
 useEffect(()=>{
  const video=player;if(!video)return;
  if(!config.enabled||!active){onReady(!config.enabled);video.volume=volume;setCaption("");return;}
  onReady(false);setAvailable(true);
  const controller=new AbortController(),urls=new Map<string,string>(),done=new Set<string>();
  let live=true,current="",speaking=false,lastTime=video.currentTime,attempting=false;
  const music=()=>{video.volume=Math.max(0,Math.min(1,mix.current*(speaking?config.duck_gain:config.music_gain)));if(voice.current)voice.current.volume=mix.current*config.voice_gain;};
  function stop(){voice.current?.pause();voice.current=null;speaking=false;attempting=false;music();}
  async function fetchCue(id:string){
   try{
    const blob=await introCueBlob(config,id,language,controller.signal);
    if(!live)return;
    urls.set(id,URL.createObjectURL(blob));
   }catch{if(live)setAvailable(false);}
  }
  if(config.enabled&&active){
   let cursor=0;
   const worker=async()=>{while(live&&cursor<config.cues.length){const cue=config.cues[cursor++];await fetchCue(cue.id);}};
   // Wait for every fixed cue before starting the shared video timeline.
   void Promise.all([worker(),worker()]).finally(()=>{if(live)onReady(true);});
  }
  function update(){
   if(!live)return;
   const time=video!.currentTime;
   if(time<lastTime-.5){for(const cue of config.cues)if(cue.end>time)done.delete(cue.id);}
   lastTime=time;
   const silent=config.silent_windows?.some(w=>time>=w.start&&time<w.end);
   const cue=silent?undefined:config.cues.find(c=>time>=c.start&&time<c.end);
   setCaption(cue?local(cue.text,subtitleLanguage):"");
   if(!active||video!.paused||!cue){if(voice.current)stop();current="";music();return;}
   if(current!==cue.id){stop();current=cue.id;}
   if(!voice.current&&urls.has(cue.id)&&!done.has(cue.id)){
    const audio=new Audio(urls.get(cue.id));voice.current=audio;
    audio.onloadedmetadata=()=>{
     let rate:number;try{rate=introVoiceRate(audio.duration,cue);}catch{done.add(cue.id);stop();setAvailable(false);return;}
     audio.playbackRate=rate;audio.currentTime=Math.min(Math.max(0,(video!.currentTime-cue.start)*rate),Math.max(0,audio.duration-.05));
    };
    audio.onplaying=()=>{speaking=true;setAvailable(true);music();};
    audio.onended=()=>{done.add(cue.id);stop();};
    audio.onerror=()=>{done.add(cue.id);stop();setAvailable(false);};
   }
   const audio=voice.current;
   if(audio&&audio.paused&&!attempting){attempting=true;void audio.play().catch(()=>{done.add(cue.id);setAvailable(false);stop();}).finally(()=>{attempting=false;});}
   music();
  }
  const timer=window.setInterval(update,150);
  video.addEventListener("timeupdate",update);video.addEventListener("pause",update);video.addEventListener("playing",update);
  const levels=()=>music();window.addEventListener("world-intro-volume",levels);
  update();
  return()=>{live=false;controller.abort();clearInterval(timer);stop();video.removeEventListener("timeupdate",update);video.removeEventListener("pause",update);video.removeEventListener("playing",update);window.removeEventListener("world-intro-volume",levels);urls.forEach(url=>URL.revokeObjectURL(url));video.volume=mix.current;};
 },[player,clipId,config,active,language,subtitleLanguage,onReady]);
 useEffect(()=>{window.dispatchEvent(new Event("world-intro-volume"));},[volume]);
 return <><div className="whSubtitles" aria-live="off" lang={subtitleLanguage}>{caption&&<span>{caption}</span>}</div><label className="whNarrationChoice">{t("Thuyết minh","Narration")} <select aria-label={t("Ngôn ngữ thuyết minh","Narration language")} value={language} onChange={e=>setLanguage(e.target.value)}><option value="vi">Tiếng Việt</option><option value="en">English</option></select>{!available&&<small>{t("Chưa có giọng đọc — vẫn hiển thị phụ đề","Voice unavailable — subtitles remain available")}</small>}</label></>;
}
