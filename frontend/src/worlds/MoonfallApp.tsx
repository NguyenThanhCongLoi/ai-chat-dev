import {readWorldJson} from "./worldHttp";
import {useEffect,useRef,useState} from "react";
import {storedLanguage,UI_LANGUAGES,translateUiText} from "../i18n";
import {loadExpressionPortrait} from "../roleplay/EmotionPortrait";
import {MusicAudio} from "../roleplay/musicAudio";
import type {Message} from "../roleplay/types";
import {api,WorldError} from "./types";
import {ChapterVoiceQueue} from "./ChapterVoiceQueue";
import {MoonfallSound} from "./MoonfallSound";
import {local,type Catalog,type ChapterRun,type WorldEvent,type WorldProps} from "./moonfallTypes";
import "./moonfall.css";
import {WorldEffects} from "./WorldEffects";
import {WorldCinematics,CinematicPlayer,cinematicCue} from "./WorldCinematics";

function Landscape({place="overview"}:{place?:string}){
 return <div className="mfScenery" data-place={place} aria-hidden="true"><div className="mfMoon"/><div className="mfStars"/>
 <svg className="mfRuins" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice"><defs><linearGradient id="mfStone" x2=".3" y2="1"><stop stopColor="#5b6075"/><stop offset="1" stopColor="#131e35"/></linearGradient><radialGradient id="mfLight"><stop stopColor="#abd6e7" stopOpacity=".4"/><stop offset="1" stopColor="#7599c4" stopOpacity="0"/></radialGradient></defs>
 <path d="M0 600L150 430 300 530 490 350 710 570 870 400 1020 490 1260 320 1450 490 1600 410V900H0Z" fill="#172640"/><path d="M0 710L190 590 370 660 600 530 800 660 1040 540 1230 640 1420 500 1600 600V900H0Z" fill="#101c31"/>
 <g fill="url(#mfStone)" stroke="#8e9ab0" strokeOpacity=".2"><path d="M565 735V365L625 330 640 365V735ZM965 735V350L1025 330 1040 370V735Z"/><path d="M625 380Q800 120 980 380L966 440Q800 220 640 440Z"/><path d="M512 741V535H552V741ZM1073 740V500H1112V740Z"/><path d="M390 760V550H420V760ZM1168 750V520H1202V750Z"/><path d="M488 735H1123L1210 900H385Z"/></g>
 <path d="M680 735V450Q800 295 920 450V735Z" fill="#0b1426" stroke="#b1c9df" strokeOpacity=".3"/><ellipse cx="800" cy="575" rx="180" ry="240" fill="url(#mfLight)"/>
 <g data-world-target="scenery-rune" className="mfRuneDrawing" fill="none" stroke="#8de2e8" strokeWidth="2"><circle cx="800" cy="515" r="50"/><path d="M800 450L850 540H750ZM775 470L825 550M825 470L775 550"/></g>
 <path d="M0 820Q400 750 800 805T1600 780V900H0Z" fill="#101a2d"/></svg><div className="mfMist mfMistOne"/><div className="mfMist mfMistTwo"/><div className="mfVignette"/></div>;
}
function MediaScene({run}:{run:ChapterRun|null}){
 const [failed,setFailed]=useState("");const place=run?.locations.find(p=>p.id===run.location),asset=place?run?.assets[place.background]:{url:"/v1/moonfall/assets/moonfall_overview"};
 return <><Landscape place={run?.location}/>{asset&&failed!==asset.url&&<img className="mfBackground" src={asset.url} alt="" loading="eager" onError={()=>setFailed(asset.url)}/>}</>;
}

type Recognizer={lang:string;continuous:boolean;interimResults:boolean;start:()=>void;abort:()=>void;onresult:((e:{results:{[index:number]:{[index:number]:{transcript:string}}}})=>void)|null;onend:(()=>void)|null;onerror:(()=>void)|null};
export default function MoonfallApp({active=true,embedded=false,characterId,onBack,onChat}:WorldProps){
 const [catalog,setCatalog]=useState<Catalog|null>(null),[run,setRun]=useState<ChapterRun|null>(null),[lang,setLang]=useState(storedLanguage);
 const [error,setError]=useState(""),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[text,setText]=useState("");
 const [panel,setPanel]=useState<"map"|"journal"|"sound"|"">(""),[memory,setMemory]=useState(false),[sync,setSync]=useState(true);
 const [portrait,setPortrait]=useState(""),[priorPortrait,setPriorPortrait]=useState(""),[failedPortrait,setFailedPortrait]=useState(""),[voiceLanguage,setVoiceLanguage]=useState("off"),[playing,setPlaying]=useState(""),[voiceBusy,setVoiceBusy]=useState(""),[autoVoice,setAutoVoice]=useState(false);
 const [cinematicPlaying,setCinematicPlaying]=useState(false);
 const [objective,setObjective]=useState(true),[listening,setListening]=useState(false);
 const current=useRef<ChapterRun|null>(null);current.current=run;
 const alive=useRef(true),working=useRef(false),voice=useRef<{audio:HTMLAudioElement;engine:MusicAudio;url:string}|null>(null),voiceRequest=useRef<AbortController|null>(null),voiceSequence=useRef(0),voiceDone=useRef<(()=>void)|null>(null);
 const speakRef=useRef<(event:WorldEvent)=>Promise<void>>(async()=>{});
 const speechLane=useRef<ChapterVoiceQueue<WorldEvent>|null>(null);
 speechLane.current??=new ChapterVoiceQueue<WorldEvent>(e=>speakRef.current(e),()=>stopVoice());
 function cancelSpeech(){speechLane.current?.cancel();}

 const portraitRef=useRef(""),portraitTimer=useRef<number|undefined>(undefined);
 const memoryDialog=useRef<HTMLDialogElement>(null);
 const effectScope=useRef<HTMLDivElement>(null);
 const activeRef=useRef(active);activeRef.current=active;const transcript=useRef<HTMLDivElement>(null),recognizer=useRef<Recognizer|null>(null);
 const t=(vi:string,en:string)=>{const selected=run?.content_language||lang;const translated=translateUiText(vi,selected);return selected==="vi"?vi:translated===vi?en:translated;};
 const Recognition=(window as unknown as {SpeechRecognition?:new()=>Recognizer;webkitSpeechRecognition?:new()=>Recognizer}).SpeechRecognition||(window as unknown as {webkitSpeechRecognition?:new()=>Recognizer}).webkitSpeechRecognition;
 function stopVoice(){voiceSequence.current++;voiceRequest.current?.abort();voiceRequest.current=null;voice.current?.audio.pause();voice.current?.engine.dispose();if(voice.current)URL.revokeObjectURL(voice.current.url);voice.current=null;voiceDone.current?.();voiceDone.current=null;setPlaying("");setVoiceBusy("");}
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;cancelSpeech();recognizer.current?.abort();voiceRequest.current?.abort();voice.current?.audio.pause();voice.current?.engine.dispose();if(voice.current)URL.revokeObjectURL(voice.current.url);};},[]);
 useEffect(()=>{if(!active){cancelSpeech();recognizer.current?.abort();setMemory(false);}},[active]);
 async function load(){
  speechLane.current?.reset();setRun(null);setLoading(true);try{
   const c=await api<Catalog>("/v1/moonfall");if(!alive.current)return;setCatalog(c);
   const saved=characterId?c.runs.find(s=>s.character_id===characterId):c.runs[0];
   if(saved){const value=await api<ChapterRun>("/v1/moonfall/"+saved.id);if(alive.current){setRun(value);setLang(value.content_language);setVoiceLanguage(["vi","en"].includes(value.content_language)?value.content_language:"off");}}
   else if(characterId){
    const value=await api<ChapterRun>("/v1/moonfall","POST",{character_id:characterId,content_language:lang});
    if(alive.current){setRun(value);setVoiceLanguage(["vi","en"].includes(lang)?lang:"off");}
   }
  }catch(e){if(alive.current)setError(e instanceof Error?e.message:String(e));}finally{if(alive.current)setLoading(false);}
 }
 useEffect(()=>{void load();},[characterId]);
 useEffect(()=>{if(memory)memoryDialog.current?.showModal();else memoryDialog.current?.close();},[memory]);
 useEffect(()=>{if(transcript.current)transcript.current.scrollTop=transcript.current.scrollHeight;},[run?.events.length,busy]);
 const last=run?.events.slice().reverse().find(e=>e.type==="CHARACTER_SPEECH"||e.type==="CHARACTER_THOUGHT");
 useEffect(()=>{
  if(!run)return;let live=true;
  const emotion=(last?.expression||"thinking") as NonNullable<Message["emotion"]>;
  const key=emotion==="neutral"?"happy":emotion==="shy"?"winking":emotion;
  const asset=run.assets["selene_"+key];
  const ready=asset?new Promise<string>((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(asset.url);image.onerror=()=>{void loadExpressionPortrait(run.character.id,emotion).then(resolve,reject);};image.src=asset.url;}):loadExpressionPortrait(run.character.id,emotion);
  void ready.then(url=>{if(live){setPriorPortrait(portraitRef.current);portraitRef.current=url;setPortrait(url);window.clearTimeout(portraitTimer.current);portraitTimer.current=window.setTimeout(()=>setPriorPortrait(""),450);}}).catch(()=>{});
  return()=>{live=false;window.clearTimeout(portraitTimer.current);};
 },[run?.character.id,last?.expression]);
 async function speak(event:WorldEvent):Promise<void>{
  const value=current.current;
  if(!value||voiceLanguage==="off"||!["NARRATION","CHARACTER_SPEECH"].includes(event.type))return;
  stopVoice();const sequence=voiceSequence.current,controller=new AbortController();voiceRequest.current=controller;setVoiceBusy(event.id);
  try{
   const token=localStorage.getItem("auth_token");
   const response=await fetch("/v1/moonfall/"+value.id+"/voice/"+event.id,{method:"POST",signal:controller.signal,
    headers:{"Content-Type":"application/json",...(token?{Authorization:"Bearer "+token}:{})},body:JSON.stringify({voice_language:voiceLanguage,explicit_user_choice:true})});
   if(!response.ok){const data=await readWorldJson(response).catch(()=>null);throw new Error(typeof data?.detail==="string"?data.detail:t("Chưa phát được giọng nói.","Voice unavailable."));}
   const blob=await response.blob();if(!alive.current||!activeRef.current||sequence!==voiceSequence.current)return;
   const url=URL.createObjectURL(blob),audio=new Audio(),engine=new MusicAudio(audio);audio.src=url;voice.current={url,audio,engine};
   const level=()=>{try{const l=JSON.parse(localStorage.getItem("moonfall_audio_levels")||"{}");return (l.master??.65)*(event.type==="NARRATION"?(l.narrator??.8):(l.character??.8));}catch{return .5;}};
   engine.setVolume(level());audio.onplay=()=>setPlaying(event.id);setVoiceBusy("");
   await new Promise<void>((resolve,reject)=>{voiceDone.current=resolve;audio.onended=()=>{setPlaying("");resolve();};audio.onerror=()=>reject(new Error(t("Không đọc được audio.","Could not play audio.")));void engine.play().catch(reject);});
  }catch(e){if(alive.current&&!(e instanceof DOMException&&e.name==="AbortError")){setError(e instanceof Error?e.message:String(e));setPlaying("");}}
  finally{if(sequence===voiceSequence.current){voiceDone.current=null;if(voice.current){voice.current.audio.pause();voice.current.engine.dispose();URL.revokeObjectURL(voice.current.url);voice.current=null;}if(alive.current){setVoiceBusy("");setPlaying("");}}}
 }
 speakRef.current=speak;
 useEffect(()=>{
  const update=()=>{if(!voice.current||!playing)return;try{const v=JSON.parse(localStorage.getItem("moonfall_audio_levels")||"{}");const e=current.current?.events.find(e=>e.id===playing);voice.current.engine.setVolume((v.master??.65)*(e?.type==="NARRATION"?(v.narrator??.8):(v.character??.8)));}catch{}};
  window.addEventListener("moonfall-levels",update);return()=>window.removeEventListener("moonfall-levels",update);
 },[playing]);
 async function action(action:string,value="",manual=true){
  if(working.current||!current.current)return;working.current=true;setBusy(true);setError("");
  const previous=current.current;
  try{
   const next=await api<ChapterRun>("/v1/moonfall/"+previous.id+"/act","POST",{revision:previous.revision,request_id:crypto.randomUUID(),action,value,manual});
   if(!alive.current)return;setRun(next);if(action==="say")setText("");
   if(!previous.completed&&next.completed){setMemory(true);setSync(next.memories.some(m=>m.scope==="NORMAL_CHAT_SHARED"));}
   if(autoVoice&&voiceLanguage!=="off"){
    const old=new Set(previous.events.map(e=>e.id)),added=next.events.filter(e=>!old.has(e.id)&&["NARRATION","CHARACTER_SPEECH"].includes(e.type));
    speechLane.current?.enqueue(added);
   }
  }catch(e){if(alive.current){setError(e instanceof Error?e.message:String(e));if(e instanceof WorldError&&e.status===409){try{setRun(await api<ChapterRun>("/v1/moonfall/"+previous.id));}catch{}}}}
  finally{working.current=false;if(alive.current)setBusy(false);}
 }
 useEffect(()=>{
  if(!run||run.intro_seen||!active)return;
  const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const timer=window.setTimeout(()=>void action("intro_complete"),reduce?800:Math.min(8,Math.max(5,run.visual_events.WORLD_INTRO.duration))*1000);
  return()=>clearTimeout(timer);
 },[run?.id,run?.intro_seen,active]);
 useEffect(()=>{
  if(!run||!run.intro_seen||run.completed||!active||!run.hints.enabled)return;
  const timer=window.setInterval(()=>{if(!working.current&&document.visibilityState==="visible")void action("hint","",false);},Math.max(15,run.hints.idle_seconds)*1000);
  return()=>clearInterval(timer);
 },[run?.id,run?.completed,run?.intro_seen,active]);
 async function enter(){
  if(!catalog?.character||working.current)return;working.current=true;setBusy(true);setError("");
  try{const r=await api<ChapterRun>("/v1/moonfall","POST",{character_id:characterId||catalog.character.id,content_language:lang});setRun(r);setVoiceLanguage(["vi","en"].includes(lang)?lang:"off");}
  catch(e){setError(e instanceof Error?e.message:String(e));}finally{working.current=false;setBusy(false);}
 }
 function navigate(url:string){cancelSpeech();if(onChat)onChat(url);else window.location.href=url;}
 async function normalChat(share=false){
  if(working.current)return;working.current=true;setBusy(true);cancelSpeech();
  try{
   const result=run?await api<{url:string}>("/v1/moonfall/"+run.id+"/return-to-chat","POST",{sync_memory:share}):
    await api<{url:string}>("/v1/moonfall/chat","POST",{character_id:catalog?.character?.id});
   navigate(result.url);
  }catch(e){setError(e instanceof Error?e.message:String(e));}finally{working.current=false;setBusy(false);}
 }
 function dictate(){
  if(!Recognition)return;
  if(listening){recognizer.current?.abort();setListening(false);return;}
  const r=new Recognition();r.lang=(run?.content_language||lang)==="vi"?"vi-VN":(run?.content_language||lang)==="en"?"en-US":run?.content_language||lang;
  r.continuous=false;r.interimResults=false;r.onresult=e=>setText(e.results[0][0].transcript);
  r.onend=()=>setListening(false);r.onerror=()=>{setListening(false);setError(t("Chưa nhận được giọng nói. Bạn có thể gõ tin nhắn.","Voice input unavailable; you can type instead."));};
  recognizer.current=r;r.start();setListening(true);
 }
 const voiceButton=(e:WorldEvent)=><button type="button" className="mfListen" disabled={voiceLanguage==="off"||!!voiceBusy} onClick={()=>{if(playing===e.id)cancelSpeech();else speechLane.current?.enqueue([e],true);}} aria-label={t("Nghe ","Listen to ")+(e.type==="NARRATION"?t("người kể chuyện","narration"):run?.character.name)}>{voiceBusy===e.id?"…":playing===e.id?"■":"▷"}</button>;

 useEffect(()=>{
  if(!run||run.completed||!autoVoice||voiceLanguage==="off"||!active)return;
  const e=run.events.find(e=>e.visual_event===(run.intro_seen?"CHARACTER_ENTER":"WORLD_INTRO"));
  if(e)speechLane.current?.enqueue([e]);
 },[run?.id,run?.intro_seen,autoVoice,voiceLanguage,active]);
 const place=run?.locations.find(p=>p.id===run.location),cold=!!run&&!run.intro_seen;
 const feedback=run?.events.slice().reverse().find(e=>e.type==="SYSTEM");
 const characterSrc=portrait||run?.character.avatar_url||"";
 return <div ref={effectScope} className={"mfRoot"+(embedded?" mfEmbedded":"")} data-no-translate="true" data-world="echoes-of-moonfall">
  <MediaScene run={run}/><WorldEffects run={run} active={active&&!loading} scope={effectScope}/><WorldCinematics run={run} active={active&&!loading} onPlaying={setCinematicPlaying}/><div className="mfSceneTransition" key={run?.location||"welcome"} aria-hidden="true"/>
  <header className="mfTop"><button type="button" className="mfBack" onClick={()=>{cancelSpeech();if(onBack)onBack();else window.location.href="/avibi-platform";}}>← {t("Trở về Chat","Back to Chat")}</button><span className="mfBrand">ECHOES <i>of</i> MOONFALL</span>
   <div className="mfTopActions"><MoonfallSound run={run} active={active&&!loading} playingVoice={!!playing} cinematicPlaying={cinematicPlaying}/><button type="button" onClick={()=>setPanel(panel==="sound"?"":"sound")}>◖ {t("Giọng nói","Voices")}</button></div></header>
  {error&&<div className="mfError" role="alert"><span>{error}</span><button aria-label={t("Đóng thông báo","Close message")} onClick={()=>setError("")}>×</button></div>}
  {loading?<main className="mfWelcome"><small>MOONFALL</small><h1>{t("Ánh trăng đang dẫn lối…","Following the moonlight…")}</h1></main>:!run?<main className="mfWelcome">
   <p className="mfEyebrow">SELENE · ARC I</p><h1>ECHOES<br/><em>of Moonfall</em></h1><p className="mfPitch">{catalog?local(catalog.pitch,lang):t("Đăng nhập và bật World để bước vào câu chuyện.","Sign in and enable World to begin.")}</p>
   <div className="mfWelcomeActions">{catalog?.eligible?<button className="mfPrimary" disabled={busy} onClick={()=>void enter()}>{t("Cùng Selene bước vào","Step inside with Selene")} <span>↗</span></button>:<button className="mfPrimary" disabled={busy||!catalog?.available} onClick={()=>void normalChat()}>{t("Trò chuyện cùng Selene trước","Spend time with Selene first")} ↗</button>}
    <label className="mfLanguage">{t("Ngôn ngữ nội dung","Content language")}<select value={lang} onChange={e=>setLang(e.target.value)}>{UI_LANGUAGES.map(l=><option key={l.code} value={l.code}>{l.label}</option>)}</select></label></div>
   {!catalog?.available&&<p className="mfMuted">{t("CMS cần được gắn với nhân vật Selene hiện có. Không tạo bản sao tính cách mới.","Assign the existing Selene character in World CMS. Her original persona is reused.")}</p>}
   {catalog?.available&&!catalog.eligible&&<p className="mfMuted">{t("Một lời hẹn sẽ xuất hiện trong chat khi hai bạn đã có những cuộc trò chuyện đủ ý nghĩa.","An invitation will appear in chat after you share meaningful conversations.")}</p>}
   <div className="mfChapterTease"><span>01</span><div><small>{t("CHƯƠNG ĐẦU TIÊN","THE FIRST CHAPTER")}</small><h2>{catalog?local(catalog.chapters.find(c=>c.id==="selene_01")?.title||{},lang):t("Tàn tích thức giấc","The Ruins That Woke")}</h2></div><b>☾</b></div>
   <small className="mfFootnote">{t("Một thế giới riêng · Cốt truyện tự chọn · Ký ức được chia sẻ có chọn lọc","A private world · An optional story · Selectively shared memories")}</small>
  </main>:cold?<main className="mfColdOpen" aria-label={t("Mở đầu Moonfall","Moonfall introduction")}>
   <div className="mfColdTitle"><small>{t("MỘT CÂU CHUYỆN CỦA SELENE","A SELENE STORY")}</small><h1>ECHOES <i>of</i><br/>MOONFALL</h1></div>
   <div className="mfNarration mfIntroNarration"><small>{t("DẪN TRUYỆN","NARRATION")}</small><p>{run.events.find(e=>e.visual_event==="WORLD_INTRO")?.text}</p>{run.events[0]&&voiceButton(run.events[0])}</div>
   <button type="button" className="mfSkip" disabled={busy} onClick={()=>void action("intro_complete")}>{t("Bỏ qua mở đầu","Skip introduction")} →</button>
  </main>:<main className="mfPlay">
   <div className="mfSceneTitle"><small>{run.chapter_title}</small><h1>{place?.name}</h1><button type="button" aria-expanded={objective} onClick={()=>setObjective(!objective)}>{t("Mục tiêu","Objective")} {objective?"−":"+"}</button>{objective&&<p>{run.objective}</p>}</div>
   <nav className="mfSceneNav"><button type="button" onClick={()=>setPanel(panel==="map"?"":"map")}>⌖ {t("Địa điểm","Locations")}</button><button type="button" onClick={()=>setPanel(panel==="journal"?"":"journal")}>▤ {t("Nhật ký","Journal")}</button><button type="button" disabled={busy||run.completed} onClick={()=>void action("hint")}>✧ {t("Xin gợi ý","Ask for a hint")}</button></nav>
   <div className="mfObjects" aria-label={t("Vật thể có thể khám phá","Objects to inspect")}>{run.objects.map(o=><button type="button" key={o.id} data-world-target={o.id} className={"mfHotspot"+(o.discovered?" mfFound":"")} style={{left:o.x+"%",top:o.y+"%"}} disabled={busy} onClick={()=>void action("inspect",o.id)} aria-label={t("Khám phá ","Inspect ")+o.title}><>{o.asset&&run.assets[o.asset]&&<img className="mfPropImage" src={run.assets[o.asset].url} alt="" onError={e=>{e.currentTarget.hidden=true;}}/>}</><span>{o.discovered?"✓":"✧"}</span><b>{o.title}</b></button>)}</div>
   {run.location==="overview"&&<button className="mfWalk mfPrimary" disabled={busy} onClick={()=>void action("go","outer_ruins")}>{t("Đi về phía tàn tích","Walk toward the ruins")} →</button>}
   <aside className={"mfSelene"+(run.events.some(e=>e.id===playing&&e.type==="CHARACTER_SPEECH")?" mfSpeaking":"")} aria-label={run.character.name}>
    {priorPortrait&&priorPortrait!==characterSrc&&<img className="mfPriorPortrait" src={priorPortrait} alt="" aria-hidden="true"/>}
    {characterSrc&&failedPortrait!==characterSrc?<img data-world-target="character" className="mfPortraitIncoming" key={characterSrc} src={characterSrc} alt={run.character.name} onError={()=>setFailedPortrait(characterSrc)}/>:<div className="mfCharacterSilhouette"><span>☽</span></div>}
    <span className="mfCharacterName">{run.character.name}</span>
   </aside>
   {feedback&&<div className="mfFeedback" key={feedback.id} role="status"><span>✦</span><div><small>{feedback.visual_event==="MEMORY_UNLOCKED"?t("KÝ ỨC MỚI","NEW MEMORY"):feedback.visual_event==="CHAPTER_COMPLETE"?t("CHƯƠNG HOÀN THÀNH","CHAPTER COMPLETE"):t("ĐÃ KHÁM PHÁ","DISCOVERED")}</small><p>{feedback.text}</p></div></div>}
   <section className="mfConversation">{playing&&<small className="mfVoiceNow" role="status">{run.events.find(e=>e.id===playing)?.type==="NARRATION"?t("Đang đọc lời dẫn…","Narration playing…"):t("Đang nói: ","Speaking: ")+run.character.name}</small>}<div className="mfDialogue" ref={transcript} aria-live="polite" aria-busy={busy}>
    {run.events.filter(e=>e.visual_event!=="WORLD_INTRO").slice(-12).map(e=><article className={"mfLine mfType"+e.type+" mfEvent-"+e.visual_event+(playing===e.id?" mfLinePlaying":"")} key={e.id} data-world-target={"event:"+e.id} data-output-type={e.type} data-voice-role={e.voice_role||undefined} aria-current={playing===e.id?"true":undefined}>
     {e.type==="NARRATION"?<><small>{t("DẪN TRUYỆN","NARRATION")}</small><p>{e.text}</p>{voiceButton(e)}</>:e.type==="CHARACTER_THOUGHT"?<><small>{run.character.name} · {t("suy nghĩ","thought")}</small><p>{e.text}</p><span className="mfThinkingDots" aria-hidden="true">· · ·</span></>:e.type==="SYSTEM"?<><small>✦ {t("Hệ thống","System")}</small><p>{e.text}</p></>:e.type==="USER"?<><small>{t("Bạn","You")}</small><p>{e.text}</p></>:<><small><span aria-hidden="true">❝ </span>{run.character.name} · {t("lời thoại","dialogue")}</small><p><q className="mfSpokenText">{e.text}</q></p>{voiceButton(e)}</>}
    </article>)}
    {busy&&<p className="mfPending" role="status">{t("Selene đang suy nghĩ…","Selene is thinking…")}</p>}
   </div><form className="mfComposer" onSubmit={e=>{e.preventDefault();void action("say",text);}}><textarea aria-label={t("Trò chuyện tự do với Selene","Talk freely with Selene")} placeholder={t("Hỏi Selene, kể điều bạn nghĩ, hoặc nhắc đến vật thể…","Ask Selene, share a thought, or mention an object…")} value={text} maxLength={1800} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();if(text.trim()&&!busy)void action("say",text);}}}/>
    {Recognition&&<button type="button" aria-label={t("Nhập bằng giọng nói","Dictate message")} aria-pressed={listening} onClick={dictate}>{listening?"■":"♩"}</button>}<button className="mfSend" disabled={busy||!text.trim()} aria-label={t("Gửi cho Selene","Send to Selene")}>↑</button></form></section>
   {run.completed&&<button type="button" data-world-target="memory" className="mfMemoryButton" onClick={()=>setMemory(true)}>☾ {t("Điều hai bạn giữ lại","What you carry together")} ↗</button>}
   {panel==="map"&&<aside className="mfPanel mfMapPanel" aria-label={t("Bản đồ Moonfall","Moonfall map")}><button className="mfPanelClose" onClick={()=>setPanel("")} aria-label={t("Đóng bản đồ","Close map")}>×</button><small>MOONFALL</small><h2>{t("Dưới cùng một vầng trăng","Under the same moon")}</h2><div className="mfMapField">{run.assets.map_world_select&&<img className="mfMapArt" src={run.assets.map_world_select.url} alt="" onError={e=>{e.currentTarget.hidden=true;}}/>}{run.locations.map(p=><button key={p.id} data-world-target={"map:"+p.id} disabled={busy||p.locked} style={{left:p.x+"%",top:p.y+"%"}} onClick={()=>{void action("go",p.id);setPanel("");}}><span>{p.locked?"◇":p.id===run.location?"☾":"✧"}</span><strong>{p.name}</strong>{p.locked&&<small>{t("Cần tìm thêm dấu vết","Follow another trace first")}</small>}</button>)}</div></aside>}
   {panel==="journal"&&<aside className="mfPanel mfJournal" aria-label={t("Nhật ký khám phá","Discovery journal")}><button className="mfPanelClose" onClick={()=>setPanel("")} aria-label={t("Đóng nhật ký","Close journal")}>×</button><small>{t("NHỮNG ĐIỀU ĐƯỢC GHI LẠI","WHAT YOU HAVE LEARNED")}</small><h2>{t("Dấu vết dưới trăng","Traces in moonlight")}</h2>{!run.journal.length&&<p>{t("Quan sát tàn tích để tìm dấu vết đầu tiên.","Look around the ruins for your first trace.")}</p>}{run.journal.map(c=><article key={c.id}><small>{c.kind==="RUMOR"?t("LỜI ĐỒN","RUMOR"):t("DỮ KIỆN","FACT")}</small><h3>{c.title}</h3><p>{c.text}</p></article>)}{run.memories.map(m=><article key={m.id}><small>{t("KÝ ỨC","MEMORY")}</small><h3>{m.title}</h3><p>{m.text}</p></article>)}</aside>}
  </main>}
  {panel==="sound"&&<aside className="mfPanel mfVoices" aria-label={t("Thiết lập giọng nói","Voice settings")}><button className="mfPanelClose" onClick={()=>setPanel("")} aria-label={t("Đóng cài đặt","Close settings")}>×</button><h2>{t("Lắng nghe câu chuyện","Listen to the story")}</h2>
   <label>{t("Ngôn ngữ audio","Audio language")}<select value={voiceLanguage} onChange={e=>{cancelSpeech();setVoiceLanguage(e.target.value);}}><option value="off">{t("Tắt","Off")}</option><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
   <label><input type="checkbox" checked={autoVoice} onChange={e=>{setAutoVoice(e.target.checked);if(!e.target.checked){cancelSpeech();}}}/>{t("Tự đọc lời kể và hội thoại mới","Automatically read new narration and speech")}</label>
   <p>{t("Người kể và Selene dùng hai giọng riêng. Suy nghĩ và thông báo không được đọc thành tiếng.","Narrator and Selene use distinct voices. Thoughts and system events are never spoken.")}</p>
   {run&&!run.voice_supported&&<p>{t("Ngôn ngữ văn bản này chưa hỗ trợ voice. Chỉ khi bạn chọn EN/VI, bản đọc dịch mới được tạo; phụ đề vẫn giữ nguyên.","This text language has no World voice. Choose EN/VI explicitly to hear a translated version; subtitles stay unchanged.")}</p>}
  </aside>}
  {memory&&run&&<div className="mfMemoryScrim"><dialog ref={memoryDialog} onCancel={()=>setMemory(false)} className="mfMemoryReveal" aria-label={t("Ký ức sau chương truyện","Chapter memory")}><button className="mfPanelClose" aria-label={t("Đóng ký ức","Close memory")} onClick={()=>setMemory(false)}>×</button>{cinematicCue(run,{id:"memory-reveal",visual_event:"MEMORY_RECONSTRUCTION"})&&<CinematicPlayer cue={cinematicCue(run,{id:"memory-reveal",visual_event:"MEMORY_RECONSTRUCTION"})!} active={active&&memory} onPlaying={setCinematicPlaying} onDone={()=>{}}/>}{run.assets.chapter_complete_background&&<img className="mfMemoryBackdrop" src={run.assets.chapter_complete_background.url} alt="" onError={e=>{e.currentTarget.hidden=true;}}/>}<span className="mfMemorySeal">☾</span><small>{t("MỘT TRẢI NGHIỆM CHUNG","A SHARED EXPERIENCE")}</small><h2>{run.memories[0]?.title||run.chapter_title}</h2><p>{run.memories[0]?.text||t("Khoảnh khắc này sẽ ở lại trong thế giới.","This moment stays in the World.")}</p><label><input type="checkbox" disabled={!run.memories.some(m=>m.scope==="NORMAL_CHAT_SHARED")} checked={sync} onChange={e=>setSync(e.target.checked)}/>{t("Để Selene nhớ điều này trong chat thường","Let Selene remember this in normal chat")}</label><small>{t("Chỉ ký ức này được chia sẻ, không sao chép lịch sử World.","Only this memory is shared, never the World transcript.")}</small>
   <button className="mfPrimary" disabled={busy} onClick={()=>void normalChat(sync)}>{t("Nói chuyện cùng Selene về điều vừa xảy ra","Talk to Selene about what happened")} →</button>
   <div className="mfEndingChoices">{run.choices.map(c=><button disabled={busy} key={c.id} onClick={()=>void action("choice",c.id)}>{c.label}</button>)}</div></dialog></div>}
  {run&&run.story_language!==run.content_language&&<small className="mfTranslationNote">{t("Nội dung truyện đang dùng bản dịch dự phòng; hội thoại AI vẫn theo ngôn ngữ đã chọn.","Authored story uses a fallback translation; AI dialogue follows your selected language.")}</small>}
 </div>;
}
