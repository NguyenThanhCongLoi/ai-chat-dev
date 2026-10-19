/** Shared chat playlist; existing MusicAudio mixer with scoped World channels. */
import {useEffect,useRef,useState} from "react";
import {storedLanguage} from "../i18n";
import {worldUi} from "./worldUi";
import {MusicAudio} from "../roleplay/musicAudio";
import {ActionSoundDetector,type ActionSound} from "../roleplay/actionSoundDetector";
import {api} from "./types";
import type {ChapterRun} from "./moonfallTypes";

type Channel={audio:HTMLAudioElement;engine:MusicAudio;url:string};
type Levels={master:number;music:number;ambient:number;effects:number;narrator:number;character:number};
const defaults:Levels={master:.85,music:.45,ambient:.2,effects:.22,narrator:.9,character:.9};
type Track={id:string;title:string;url:string};
function levels():Levels{try{const stored=JSON.parse(localStorage.getItem("moonfall_audio_levels")||"{}");return Object.fromEntries(Object.entries(defaults).map(([k,v])=>[k,typeof stored[k]==="number"?Math.max(0,Math.min(1,stored[k])):v])) as Levels;}catch{return defaults;}}
function channel(url:string,loop=false){const audio=new Audio();audio.preload="auto";const engine=new MusicAudio(audio);audio.src=url;audio.loop=loop;return {audio,engine,url};}
function dispose(c:Channel|null){if(!c)return;c.audio.onended=c.audio.onerror=null;c.audio.pause();c.engine.dispose();c.audio.removeAttribute("src");c.audio.load();}
export function MoonfallSound({run,active,playingVoice,cinematicPlaying=false}:{run:ChapterRun|null;active:boolean;playingVoice:boolean;cinematicPlaying?:boolean}){
 const [enabled,setEnabled]=useState(true),[vol,setVol]=useState<Levels>(levels),[tracks,setTracks]=useState<Track[]>([]),[trackId,setTrackId]=useState(""),[expanded,setExpanded]=useState(false),[visible,setVisible]=useState(document.visibilityState==="visible");
 const music=useRef<Channel|null>(null),fading=useRef<Channel|null>(null),ambient=useRef<Channel|null>(null),effects=useRef<Channel|null>(null),fade=useRef(0);
 const failedTracks=useRef(0);
 const duckGain=run?.music_levels?.duck_gain??.35;
 useEffect(()=>{try{if(!localStorage.getItem("moonfall_audio_levels")&&run?.music_levels)setVol({...defaults,...run.music_levels} as Levels);}catch{}},[run?.id,run?.music_levels]);
 const latest=useRef({enabled,active,vol,playingVoice,cinematicPlaying,duckGain});latest.current={enabled,active,vol,playingVoice,cinematicPlaying,duckGain};
 const library=useRef<{volume:number;sounds:ActionSound[]}>({volume:.35,sounds:[]});
 const seen=useRef(new Set<string>()),seenRun=useRef("");
 const t=(vi:string,en:string)=>worldUi(vi,en,run?.content_language||storedLanguage());
 useEffect(()=>{const change=()=>setVisible(document.visibilityState==="visible");document.addEventListener("visibilitychange",change);return()=>document.removeEventListener("visibilitychange",change);},[]);
 useEffect(()=>{if(!active)return;let live=true;void api<{tracks:Track[]}>("/v1/roleplay/background-music").then(r=>{if(live)setTracks(r.tracks);}).catch(()=>{});return()=>{live=false;};},[active]);
 useEffect(()=>{if(!active)return;let live=true;void api<{volume:number;sounds:ActionSound[]}>("/v1/roleplay/action-sounds").then(data=>{if(live)library.current=data;}).catch(()=>{});return()=>{live=false;};},[active]);
 // Match normal chat: each new visit starts enabled; mute remains available during the visit.
 useEffect(()=>{if(active)setEnabled(true);},[active,run?.id]);
 useEffect(()=>{
  const unlock=()=>{const s=latest.current;if(!s.enabled||!s.active||document.hidden)return;const c=music.current;if(c)void c.engine.play().catch(()=>{});};
  window.addEventListener("pointerdown",unlock);window.addEventListener("keydown",unlock);
  return()=>{window.removeEventListener("pointerdown",unlock);window.removeEventListener("keydown",unlock);};
 },[]);
 useEffect(()=>{
  const preferred=run?.bgm?.startsWith("shared:")?run.bgm.slice(7):"";
  failedTracks.current=0;
  setTrackId(current=>(preferred&&tracks.some(t=>t.id===preferred)?preferred:tracks.some(t=>t.id===current)?current:tracks[0]?.id)||"");
 },[tracks,run?.bgm]);
 const selected=tracks.find(x=>x.id===trackId)||tracks[0];
 const playlist=useRef(tracks);playlist.current=tracks;
 const place=run?.locations.find(p=>p.id===run.location),ambientUrl=place?.ambient?run?.assets[place.ambient]?.url:undefined;
 useEffect(()=>{
  if(!selected){dispose(music.current);dispose(fading.current);music.current=fading.current=null;return;}
  if(!enabled||!active||!visible)return;
  if(music.current?.url===selected.url){dispose(fading.current);fading.current=null;music.current.audio.loop=tracks.length===1;music.current.engine.setVolume(vol.master*vol.music*(playingVoice?duckGain:1));void music.current.engine.play().catch(()=>{});return;}
  cancelAnimationFrame(fade.current);dispose(fading.current);fading.current=music.current;
  const next=channel(selected.url,tracks.length===1);music.current=next;
  const advance=()=>{
   const rows=playlist.current,index=rows.findIndex(t=>t.id===selected.id);
   setTrackId(rows[(index+1)%rows.length]?.id||"");
  };
  next.audio.onended=()=>{failedTracks.current=0;advance();};
  next.audio.onerror=()=>{if(++failedTracks.current<tracks.length)advance();};
  next.engine.setVolume(0);void next.engine.play().catch(()=>{});
  const start=performance.now();
  function step(now:number){
   const k=Math.min(1,(now-start)/900),s=latest.current,level=s.vol.master*s.vol.music*(s.playingVoice?s.duckGain:1);
   next.engine.setVolume(level*k);fading.current?.engine.setVolume(level*(1-k));
   if(k<1)fade.current=requestAnimationFrame(step);else{dispose(fading.current);fading.current=null;}
  }
  fade.current=requestAnimationFrame(step);
 },[selected?.url,tracks.length,enabled,active,visible]);
 useEffect(()=>{
  if(!enabled||!active||!visible){music.current?.audio.pause();fading.current?.audio.pause();ambient.current?.audio.pause();effects.current?.audio.pause();cancelAnimationFrame(fade.current);return;}
  if(ambientUrl&&ambient.current?.url!==ambientUrl){dispose(ambient.current);ambient.current=channel(ambientUrl,true);}
  if(!ambientUrl){dispose(ambient.current);ambient.current=null;}
  if(ambient.current){ambient.current.engine.setVolume(vol.master*vol.ambient*(playingVoice?duckGain:1));void ambient.current.engine.play().catch(()=>{});}
 },[ambientUrl,enabled,active,visible]);
 useEffect(()=>{
  const duck=playingVoice?duckGain:1;
  music.current?.engine.setVolume(vol.master*vol.music*(playingVoice?duckGain:1));
  ambient.current?.engine.setVolume(vol.master*vol.ambient*duck);
  effects.current?.engine.setVolume(vol.master*vol.effects);
  window.dispatchEvent(new CustomEvent("moonfall-voice-volume",{detail:vol.master}));
 },[vol,playingVoice,cinematicPlaying]);
 useEffect(()=>{
  if(!run)return;
  if(seenRun.current!==run.id){seenRun.current=run.id;seen.current=new Set(run.events.map(e=>e.id));return;}
  for(const event of run.events){
   if(seen.current.has(event.id))continue;seen.current.add(event.id);
   // Consume new event IDs once, even when muted. Never replay history or clicks.
   // Cinematic narration and character thoughts do not trigger action sounds.
   if(!enabled||!active||!visible||cinematicPlaying||event.type==="USER"||event.type==="CHARACTER_THOUGHT")continue;
   const id=run.visual_events[event.visual_event]?.audio;
   let url=id?run.assets[id]?.url:undefined,gain=1;
   if(!url&&(event.action_sound||event.character_action)){
    const detector=new ActionSoundDetector();
    const candidates=detector.feed("*"+(event.action_sound||event.character_action)+"*",library.current.sounds.filter(s=>s.enabled))[0];
    const sound=candidates?.[Math.floor(Math.random()*candidates.length)];
    if(sound){url=sound.url;gain=library.current.volume*sound.volume;}
   }
   if(url){dispose(effects.current);effects.current=channel(url);effects.current.engine.setVolume(vol.master*vol.effects*gain);void effects.current.engine.play().catch(()=>{});}

  }
 },[run?.events,enabled,active,visible,vol,cinematicPlaying]);
 useEffect(()=>()=>{cancelAnimationFrame(fade.current);dispose(music.current);dispose(fading.current);dispose(ambient.current);dispose(effects.current);},[]);
 function change(k:keyof Levels,n:number){const value={...vol,[k]:n};setVol(value);localStorage.setItem("moonfall_audio_levels",JSON.stringify(value));window.dispatchEvent(new CustomEvent("moonfall-levels",{detail:value}));}
 const names:Record<keyof Levels,string>={master:t("Tổng","Master"),music:t("Nhạc nền","Music"),ambient:t("Môi trường","Ambient"),effects:t("Hiệu ứng","Effects"),narrator:t("Giọng kể","Narrator"),character:t("Giọng nhân vật","Character voice")};
 return <div className="mfSound"><button type="button" aria-pressed={enabled} onClick={()=>{setEnabled(!enabled);try{localStorage.setItem("moonfall_music_enabled",String(!enabled));}catch{}}}>{enabled?"♫":"♪"} {t("Nhạc & âm thanh","Music & sound")}</button><button type="button" aria-label={t("Chỉnh âm lượng World","World mixer")} aria-expanded={expanded} onClick={()=>setExpanded(!expanded)}>☷</button>
 {expanded&&<div className="mfMixer"><small>{t("Dùng chung kho nhạc của chat thường","Uses the normal chat music library")}</small>{(Object.keys(names) as (keyof Levels)[]).map(k=><label key={k}>{names[k]}<input aria-label={names[k]} type="range" min="0" max="100" value={Math.round(vol[k]*100)} onChange={e=>change(k,Number(e.target.value)/100)}/></label>)}
 <button type="button" onClick={()=>{localStorage.removeItem("moonfall_audio_levels");const next={...defaults,...run?.music_levels};setVol(next);window.dispatchEvent(new CustomEvent("moonfall-levels",{detail:next}));}}>{t("Dùng âm lượng từ CMS","Use CMS volume defaults")}</button>
 <small>{selected?.title||t("Chưa chọn nhạc trong CMS","No curated music available")}</small></div>}</div>;
}
