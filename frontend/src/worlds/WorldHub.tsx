import {useEffect,useRef,useState} from "react";
import {storedLanguage} from "../i18n";
import {api} from "./types";
import type {WorldProps} from "./moonfallTypes";
import {MoonfallHook} from "./MoonfallHook";
import StoryExperience from "./StoryExperience";
import {MoonfallSound} from "./MoonfallSound";
import IntroNarration,{type IntroNarrationConfig} from "./IntroNarration";
import "./worldHub.css";
import {hubText} from "./worldHubCopy";
import {introPlayer,parkIntro,introVolume,pauseIntroMedia,prepareIntroVideo} from "./worldIntroMedia";

type MemoryActor={id:string;name:string;avatar_url:string;character_id:string|null;unlocked:boolean;reason:string};
type Hub={narration:IntroNarrationConfig;standard_intro:{id:string;url:string}[];characters:MemoryActor[];background:string|null;intro:{id:string;url:string}[]};
export default function WorldHub(props:WorldProps){
 const [data,setData]=useState<Hub|null>(null),[error,setError]=useState(""),[attempt,setAttempt]=useState(0);
 const [stage,setStage]=useState<"intro"|"map">("intro"),[index,setIndex]=useState(0),[volume,setVolume]=useState(introVolume),[needsPlay,setNeedsPlay]=useState(false),[quality,setQuality]=useState("high");
 const [selected,setSelected]=useState<MemoryActor|null>(null),[playingActor,setPlayingActor]=useState<string>(),[playingChapter,setPlayingChapter]=useState<string>();
 const [videoReady,setVideoReady]=useState(false),[voiceReady,setVoiceReady]=useState(false);
 const [mountedVideo,setMountedVideo]=useState<HTMLVideoElement|null>(null);
 const video=useRef<HTMLVideoElement|null>(null),videoHost=useRef<HTMLDivElement>(null),lang=storedLanguage(),active=props.active!==false;
 const t=(vi:string,en:string)=>hubText(vi,en,lang);
 useEffect(()=>{
  if(!active){pauseIntroMedia();return;}let live=true;
  void api<Hub>("/v1/moonfall/hub").then(d=>{if(live){setData(d);setError("");if(!d.intro.length)setStage("map");}}).catch(e=>{if(live){pauseIntroMedia();setError(String(e.message||e));}});
  return()=>{live=false;};
 },[active,attempt,playingActor]);
 useEffect(()=>{const refresh=()=>{if(active&&!document.hidden)setAttempt(n=>n+1);};window.addEventListener("focus",refresh);return()=>window.removeEventListener("focus",refresh);},[active]);
 useEffect(()=>{if(active){setStage("intro");setIndex(0);setPlayingActor(undefined);setSelected(null);}},[active]);
 useEffect(()=>()=>pauseIntroMedia(),[]);
 const playlist=quality==="standard"&&data?.standard_intro.length?data.standard_intro:data?.intro;
 const clip=playlist?.[index];
 useEffect(()=>{
  if(!clip||stage!=="intro"||playingActor)return;
  let live=true;setVideoReady(false);setVoiceReady(false);
  const player=introPlayer(clip.url);player.pause();
  void prepareIntroVideo(clip.url).then(url=>{if(!live)return;player.src=url;player.load();if(player.readyState>=3)setVideoReady(true);}).catch(()=>{if(live){setError(t("Không tải được video. Vui lòng thử lại.","Could not load the video. Please retry."));}});
  const ready=()=>{if(live&&player.src.startsWith("blob:"))setVideoReady(true);};
  player.addEventListener("canplay",ready);
  video.current=player;setMountedVideo(player);player.hidden=false;
  player.setAttribute("aria-label",t("Giới thiệu thế giới","World introduction"));
  videoHost.current?.append(player);
  const end=()=>next();
  player.addEventListener("ended",end);player.addEventListener("error",end);
  if(player.error)queueMicrotask(end);
  // Warm only the next likely clip, and only its metadata.
  const upcoming=data?.intro[index+1];if(upcoming)introPlayer(upcoming.url,"metadata");
  return()=>{live=false;player.removeEventListener("canplay",ready);player.removeEventListener("ended",end);player.removeEventListener("error",end);parkIntro(player);video.current=null;setMountedVideo(null);};
 },[clip?.id,stage,playingActor]);
 useEffect(()=>{
  const player=video.current;if(!player)return;
  player.volume=volume*(data?.narration.enabled?data.narration.music_gain:1);
  if(!active||stage!=="intro"||!videoReady||!voiceReady){player.pause();return;}
  const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const saveData=(navigator as Navigator & {connection?:{saveData?:boolean}}).connection?.saveData;
  if(reduced||saveData){setNeedsPlay(true);return;}
  let live=true;setNeedsPlay(false);
  void player.play().catch(()=>{if(live)setNeedsPlay(true);});
  return()=>{live=false;player.pause();};
 },[clip?.id,active,stage,videoReady,voiceReady]);
 useEffect(()=>{if(video.current&&!data?.narration.enabled)video.current.volume=volume;try{localStorage.setItem("world_intro_volume",String(volume));}catch{}},[volume]);
 function finish(){video.current?.pause();setStage("map");setNeedsPlay(false);}
 function next(){if(data&&index+1<(playlist?.length||0)){setIndex(index+1);}else finish();}
 function back(){video.current?.pause();if(props.onBack)props.onBack();else location.href="/avibi-platform";}
 if(playingActor)return <StoryExperience {...props} chapterId={playingChapter} characterId={playingActor} onBack={()=>{setPlayingActor(undefined);setSelected(null);setStage("map");}}/>;
 return <section className={"whRoot"+(props.embedded?" whEmbedded":"")} data-no-translate="true" lang={lang} style={data?.background?{backgroundImage:'linear-gradient(180deg,#080d21a8,#080d21da),url("'+data.background+'")'}:undefined}>
  <header className="whHeader"><button onClick={back}>← {t("Trở về","Back")}</button><span>{t("BẢN ĐỒ KÝ ỨC","MEMORY ATLAS")}</span>{stage==="map"&&!!data?.intro.length?<button onClick={()=>{if(data?.intro[0])introPlayer(data.intro[0].url).currentTime=0;setIndex(0);setStage("intro");}}>{t("Xem intro","Replay intro")} ▷</button>:<span/>}{stage==="map"&&<MoonfallSound run={null} active={active&&!playingActor} playingVoice={false}/>}</header>
  {error?<div className="whStatus" role="alert"><p>{t("Chưa tải được bản đồ ký ức.","Could not load the memory atlas.")}</p><small>{error}</small><button onClick={()=>setAttempt(n=>n+1)}>{t("Thử lại","Retry")}</button></div>:!data?<p className="whStatus" role="status">{t("Đang mở bản đồ ký ức…","Opening the memory atlas…")}</p>:stage==="intro"&&clip?
   <div className="whCinema">
    <div ref={videoHost} className="whVideoHost"/>
    {data.narration&&<IntroNarration player={mountedVideo} config={data.narration} active={active&&stage==="intro"} volume={volume} subtitleLanguage={lang} clipId={clip.id} onReady={setVoiceReady}/>}
    <div className="whCinemaControls">
     <label>{t("Âm lượng","Volume")} <input aria-label={t("Âm lượng intro","Intro volume")} type="range" min="0" max="1" step=".01" value={volume} onChange={e=>setVolume(Number(e.target.value))}/><output>{Math.round(volume*100)}%</output></label>
     {!!data.standard_intro?.length&&<label>{t("Chất lượng","Quality")}<select aria-label={t("Chất lượng video","Video quality")} value={quality} onChange={e=>{setQuality(e.target.value);setIndex(0);}}><option value="high">{t("Cao · nguồn 720p","High · 720p source")}</option><option value="standard">{t("Tiết kiệm","Data saver")}</option></select></label>}
     <button onClick={finish}>{t("Bỏ qua intro","Skip intro")} →</button>
    </div>
    {(!videoReady||!voiceReady)&&<div className="whPlay" role="status">{t("Đang chuẩn bị video và giọng đọc…","Preparing video and narration…")}</div>}
    {videoReady&&voiceReady&&needsPlay&&<button className="whPlay" onClick={()=>{void video.current?.play().then(()=>setNeedsPlay(false)).catch(()=>setNeedsPlay(true));}}>▷ {t("Phát intro có nhạc","Play intro with sound")}</button>}
   </div>:
   <main className="whAtlas">
    <div className="whTitle"><small>{t("NHỮNG CÂU CHUYỆN ĐANG CHỜ BẠN","STORIES WAITING TO BE FOUND")}</small><h1>{t("Miền ký ức","The Memory Atlas")}</h1><p>{t("Mỗi người giữ một câu chuyện. Những ký ức đã mở sẽ sáng lên trên bản đồ.","Every character holds a story. Unlocked memories shine on the map.")}</p></div>
    <div className="whMap">
     <svg className="whPaths" viewBox="0 0 1000 550" preserveAspectRatio="none" aria-hidden="true"><path d="M90 140 Q300 30 500 140 T910 140 M90 140Q70 320 170 340 Q400 470 500 340 T830 340 Q950 270 910 140 M170 340Q300 520 400 490 L650 490 Q800 490 830 340" fill="none" stroke="currentColor" strokeDasharray="4 9"/></svg>
     {data.characters.map((c,i)=><button key={c.id} type="button" className={"whActor "+(c.unlocked?"whUnlocked":"whLocked")} disabled={!c.unlocked} style={{"--node":i} as React.CSSProperties} onClick={()=>setSelected(c)} title={c.unlocked?t("Chọn chương","Choose chapter"):c.reason==="continue_chat"?t("Tiếp tục chat để mở ký ức","Keep chatting to unlock"):t("Cốt truyện sắp ra mắt","Story coming soon")}>
      <span className="whPortrait">{c.avatar_url?<img src={c.avatar_url} alt="" loading="lazy" onError={e=>{e.currentTarget.style.visibility="hidden";}}/>:<span>{c.name.slice(0,1)}</span>}<span className="whLock" aria-hidden="true">{c.unlocked?"✦":"🔒"}</span></span><strong>{c.name}</strong><small>{c.unlocked?t("Chọn chương →","Choose chapter →"):c.reason==="continue_chat"?t("Chưa mở ký ức","Memory locked"):t("Sắp ra mắt","Coming soon")}</small>
     </button>)}
    </div>
    <p className="whLegend">✦ {t("Tiến trình thuộc tài khoản của bạn. Trò chuyện với nhân vật để mở những câu chuyện đã được phát hành.","Progress belongs to your account. Chat with a character to unlock their released stories.")}</p>
   </main>}
  {selected?.character_id&&<MoonfallHook key={selected.character_id} characterId={selected.character_id} characterName={selected.name} revision="" busy={false} autoOpen onDismiss={()=>setSelected(null)} onSelect={id=>{finish();setPlayingChapter(id);setPlayingActor(selected.character_id!);}}/>}
 </section>;
}
