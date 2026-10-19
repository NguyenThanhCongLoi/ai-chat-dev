import {preparationErrorMessage} from "./preparationErrorMessage";
import {MapArrivalNotice} from "./MapArrivalNotice";
import {stageCaption} from "./stageCaption";
import {preparedImageSource} from "./chapterImageMedia";
import {useMagicPose} from "./useMagicPose";
import {WorldEffects} from "./WorldEffects";
import {RolePlayLoadingCat} from "../roleplay/RolePlayLoadingCat";
import {useChapterResources} from "./useChapterResources";
import {ReplayControls} from "./ReplayControls";
import EmbeddedScene from "./EmbeddedScene";
import {useEffect,useRef,useState,useCallback} from "react";
import {storedLanguage,UI_LANGUAGES} from "../i18n";
import {api} from "./types";
import {type Catalog,type WorldProps} from "./moonfallTypes";
import type {AdventureRun} from "./adventureTypes";
import {AdventurePuzzle} from "./AdventurePuzzle";
import {AdventureArchive} from "./AdventureArchive";
import {MoonfallSound} from "./MoonfallSound";
import {useStorySpeech} from "./useStorySpeech";
import {WorldCinematics,CinematicPlayer,cinematicCue,type CinematicCue} from "./WorldCinematics";
import "./adventure.css";
import {prepareIntroVideo} from "./worldIntroMedia";
import {ChapterConclusion} from "./ChapterConclusion";
import {MemoryCinematic} from "./MemoryCinematic";
import {worldUi} from "./worldUi";
import {MemoryLocationEffects} from "./MemoryLocationEffects";
export default function AdventureApp({characterId,chapterId,adminPreview=false,previewRunId,active=true,onBack,onChat}:WorldProps){
 const [sceneRatio,setSceneRatio]=useState("1440 / 804");
 const [run,setRun]=useState<AdventureRun|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(""),[panel,setPanel]=useState(""),[text,setText]=useState(""),[pendingSay,setPendingSay]=useState(""),[writingBusy,setWritingBusy]=useState(false),[detail,setDetail]=useState<{asset:string;title:string}|null>(null);
 const [videoDismissed,setVideoDismissed]=useState(""),[eventVideoPlaying,setEventVideoPlaying]=useState(false),[memoryVideoPlaying,setMemoryVideoPlaying]=useState(false),[eventVideoPending,setEventVideoPending]=useState(false);
 const [sequenceMovie,setSequenceMovie]=useState<CinematicCue|null>(null);
 const moviePending=useRef<{cue:CinematicCue;resolve:()=>void}|null>(null);
 const cancelSequenceMovie=useCallback(()=>{const pending=moviePending.current;moviePending.current=null;setSequenceMovie(null);setEventVideoPlaying(false);pending?.resolve();},[]);
 const playSequenceMovie=useCallback(async(event:import("./moonfallTypes").WorldEvent)=>{
  const s=current.current;if(!s)return;const cue=cinematicCue(s,event);if(!cue)return;
  await new Promise<void>(resolve=>{moviePending.current={cue,resolve};setSequenceMovie(cue);});
 },[]);
 const media=useChapterResources(run);
 const videoPlaying=eventVideoPlaying||memoryVideoPlaying;
 const magicPose=useMagicPose(run,active&&media.ready&&!run?.reviewing);
 const [share,setShare]=useState(true),[chapterWhite,setChapterWhite]=useState(false);
 const sceneScope=useRef<HTMLDivElement>(null);
 const scope=useRef<HTMLDivElement>(null),live=useRef(true),working=useRef(false),current=useRef(run);current.current=run;
 const transcript=useRef<HTMLDivElement>(null);
 const dialog=useRef<HTMLDialogElement>(null),generated=useRef(new Set<string>());
 const speech=useStorySpeech(run,active,!media.ready||run?.phase==="intro"||run?.phase==="gate_cinematic"||memoryVideoPlaying?"silent":"characters",{play:playSequenceMovie,cancel:cancelSequenceMovie});
 const voiceSupported=!!run&&["vi","en"].includes(run.content_language);
 const blocked=speech.waitingForDialogue||!!sequenceMovie||eventVideoPending||!media.ready||run?.phase==="intro"||busy||!!run?.completed&&!run?.reviewing||speech.narrating||run?.phase==="memory"||run?.phase==="gate_cinematic"||videoPlaying;
 const language=run?.content_language||storedLanguage(),t=(vi:string,en:string)=>worldUi(vi,en,language);
 useEffect(()=>{live.current=true;return()=>{live.current=false;};},[]);
 async function load(){
  try{
   const c=await api<Catalog>("/v1/moonfall");if(!live.current)return;
   const actor=characterId||c.character?.id;
   if(!actor||actor.startsWith("preset:"))throw Error(t("Hãy trò chuyện với Selene để mở cốt truyện.","Talk to Selene to unlock her story."));
   const s=previewRunId?await api<AdventureRun>("/v1/moonfall/"+encodeURIComponent(previewRunId)):await api<AdventureRun>("/v1/moonfall","POST",{character_id:actor,content_language:storedLanguage(),...(chapterId?{chapter_id:chapterId}:{}),...(adminPreview?{preview:true}:{})});
   if(live.current){setRun(s);setError("");}
  }catch(e){if(live.current)setError(e instanceof Error?e.message:String(e));}
 }
 useEffect(()=>{speech.stop();setRun(null);setVideoDismissed("");void load();},[characterId,chapterId,adminPreview,previewRunId]);
 async function act(action:string,value=""){
  if(!current.current||working.current||speech.narrating&&!(["chapter","preview_ending"].includes(action)&&current.current.admin_preview)&&!["intro_complete","finish_memory_cinematic","finish_gate_cinematic"].includes(action))return;
  working.current=true;setBusy(true);setError("");if(action==="say")setPendingSay(value);
  try{
   const s=current.current;
   const send=(state:AdventureRun)=>api<AdventureRun>("/v1/moonfall/"+state.id+"/act","POST",{revision:state.revision,request_id:crypto.randomUUID(),action,value});
   let next:AdventureRun;
   try{next=await send(s);}
   catch(e){
    // Retry rejected stale navigation/preview commands once. Choices and
    // rewards are never automatically resubmitted.
    const review=action==="review",preview=action==="chapter"&&s.admin_preview;
    if(!review&&!preview||!(e instanceof Error)||!/reload|changed/i.test(e.message))throw e;
    const latest=await api<AdventureRun>("/v1/moonfall/"+s.id);
    if(review&&!latest.completed||preview&&!latest.admin_preview)throw e;
    next=review&&latest.reviewing?latest:await send(latest);
   }
   if(live.current){if(action==="restart"||["chapter","preview_ending"].includes(action)&&s.admin_preview){speech.stop();setChapterWhite(false);setVideoDismissed("");setPanel("");generated.current.clear();}setRun(existing=>existing&&existing.id===next.id&&existing.revision>next.revision?existing:next);if(action==="say")setText(draft=>draft.trim()===value?"":draft);}
  }catch(e){
   if(live.current)setError(e instanceof Error?e.message:String(e));
   if(current.current)try{setRun(await api<AdventureRun>("/v1/moonfall/"+current.current.id));}catch{}
  }finally{working.current=false;if(live.current){setBusy(false);setPendingSay("");}}
 }
 const textOnlyMemory=useRef("");
 useEffect(()=>{
  if(!run||run.phase!=="memory"||run.memory_video||!media.ready||!active||busy||speech.waitingForDialogue)return;
  const key=run.id+":"+run.chapter_id+":"+run.revision;
  if(textOnlyMemory.current===key)return;
  textOnlyMemory.current=key;void act("finish_memory_cinematic");
 },[run?.id,run?.chapter_id,run?.revision,run?.phase,run?.memory_video,media.ready,active,busy,speech.waitingForDialogue]);
 useEffect(()=>setDetail(null),[run?.location,run?.chapter_id]);
 useEffect(()=>{if(run?.reviewing||run?.phase==="intro"||run?.chapter_id!=="selene_01")setChapterWhite(false);},[run?.reviewing,run?.phase,run?.chapter_id]);
 useEffect(()=>{const el=transcript.current;if(el)el.scrollTop=el.scrollHeight;},[run?.events.length,pendingSay]);
 useEffect(()=>{
  if(!run||!active||run.phase!=="explore"||(navigator as Navigator&{connection?:{saveData?:boolean}}).connection?.saveData)return;
  const id="memory_video_"+run.chapter_id.slice(-2),asset=run.assets[id];
  if(asset)void prepareIntroVideo(asset.url).catch(()=>{});
 },[run?.id,run?.chapter_id,run?.phase,active]);
 useEffect(()=>{
  if(!run?.choice_refresh_at||!active)return;
  const timer=window.setTimeout(()=>{void api<AdventureRun>("/v1/moonfall/"+run.id).then(s=>{if(live.current)setRun(existing=>existing&&existing.id===s.id&&existing.revision>s.revision?existing:s);}).catch(()=>{});},Math.max(0,(run.choice_refresh_at-Date.now()/1000)*1000)+80);
  return()=>clearTimeout(timer);
 },[run?.choice_refresh_at,active]);
 useEffect(()=>{
  if(panel&&active)dialog.current?.showModal();else dialog.current?.close();
 },[panel,active]);
 useEffect(()=>{
  if(!run?.completed||run.reviewing||run.ending_is_new===false||!active||working.current||writingBusy)return;
  const kind=run.phase==="arc_complete"&&!run.chronicle?"chronicle":!run.reflection?"reflection":"";
  if(!kind)return;
  const key=run.id+":"+run.chapter_id+":"+kind;if(generated.current.has(key))return;
  generated.current.add(key);
  setWritingBusy(true);
  void api<AdventureRun>("/v1/moonfall/"+run.id+"/"+kind,"POST").then(s=>{if(live.current)setRun(existing=>existing&&existing.id===s.id&&existing.revision>s.revision?existing:s);}).catch(()=>{/* Authored reflection remains visible; manual retry is available. */}).finally(()=>{if(live.current)setWritingBusy(false);});
 },[run?.id,run?.chapter_id,run?.completed,run?.chronicle,run?.reflection,active]);
 async function writing(kind:string){
  if(!run||working.current)return;working.current=true;setBusy(true);
  try{setRun(await api<AdventureRun>("/v1/moonfall/"+run.id+"/"+kind,"POST"));}
  catch(e){setError(e instanceof Error?e.message:String(e));}
  finally{working.current=false;setBusy(false);}
 }
 async function backToChat(){
  if(!run||working.current)return;speech.stop();working.current=true;setBusy(true);
  try{
   const go=()=>api<{url:string}>("/v1/moonfall/"+run.id+"/return-to-chat","POST",{sync_memory:share&&run.completed&&!run.admin_preview});
   let r;try{r=await go();}catch(e){if(e instanceof Error&&/reload|changed/i.test(e.message))r=await go();else throw e;}
   dialog.current?.close();if(onChat)onChat(r.url);else location.href=r.url;
  }
  catch(e){setError(e instanceof Error?e.message:String(e));}finally{working.current=false;setBusy(false);}
 }
 if(!run)return <main className="maLoading"><h1>Echoes of Moonfall</h1><p role={error?"alert":"status"}>{error||t("Đang mở ký ức…","Opening a memory…")}</p><button onClick={()=>void load()}>{t("Thử lại","Retry")}</button><button onClick={onBack}>{t("Trở về","Back")}</button></main>;
 const place=run.locations.find(p=>p.id===run.location),background=run.assets[run.phase==="memory"?(run.memory_video?.fallback||"memory_space"):(run.embedded_scene?.background||place?.background||"memory_space")];
 const visibleEvents=run.events.filter(e=>!speech.hiddenEventIds.has(e.id));
 const visibleRun={...run,events:visibleEvents};
 const effectEvent=visibleEvents.slice().reverse().find(e=>e.visual_event);
 const latest=visibleEvents.filter(e=>e.presentation!=="archive").slice().reverse().find(e=>(e.type==="CHARACTER_SPEECH"||e.type==="CHARACTER_THOUGHT")&&(!e.speaker||e.speaker==="selene"));
 const sceneCaption=stageCaption({...run,events:visibleEvents});
 const expression=magicPose?"magic":latest?.expression||"neutral";
 const expressionId=run.assets["selene_"+expression]?"selene_"+expression:expression==="serious"?"selene_thinking":expression==="worried"||expression==="fear"?"selene_sad":"selene_happy";
 const portrait=run.assets[expressionId]?.url||run.character.avatar_url;
 const portraitOverlap=(x:number)=>run.objects.filter(o=>!o.removed).reduce((sum,o)=>sum+Math.max(0,Math.min(x+.18,o.x+o.width)-Math.max(x,o.x))*Math.max(0,Math.min(.47,o.y+o.height)-Math.max(.02,o.y)),0);
 const portraitLeft=portraitOverlap(.01)<portraitOverlap(.81);
 const video=run.memory_video,showVideo=media.ready&&!!video&&videoDismissed!==video.key&&active&&!speech.waitingForDialogue;

 return <div ref={scope} className="mfRoot maRoot" data-no-translate="true" lang={language} data-world="echoes-of-moonfall" data-chapter={run.chapter_id}>
  <header className="maHeader"><button onClick={()=>{speech.stop();if(onBack)onBack();else location.href="/worlds";}}>← {t("Bản đồ ký ức","Memory Atlas")}</button><strong>ECHOES OF MOONFALL</strong><MoonfallSound run={run} active={active} playingVoice={!!speech.playing} cinematicPlaying={videoPlaying}/></header>
  {(error||speech.error)&&<div className="maError" role="alert">{error||speech.error}<button onClick={()=>{setError("");speech.clearError();}}>×</button></div>}
  {run.admin_preview&&<div role="status">ADMIN PREVIEW · {t("Bản xem thử riêng, không đồng bộ sang chat thường.","Private preview; memories are not shared with normal chat.")}<select aria-label="Admin preview chapter" value={run.chapter_id} disabled={busy} onChange={e=>{speech.stop();void act("chapter",e.target.value);}}>{run.preview_chapters?.map(ch=><option key={ch.id} value={ch.id}>{ch.title}</option>)}</select><select aria-label="Admin preview ending" value="" disabled={busy} onChange={e=>{speech.stop();cancelSequenceMovie();void act("preview_ending",e.target.value);}}><option value="">{t("Xem thử kết truyện","Preview an ending")}</option>{run.preview_endings?.map(ending=><option key={ending.id} value={ending.id}>{ending.title}</option>)}</select><button type="button" disabled={busy} onClick={()=>{speech.stop();void act("chapter",run.chapter_id);}}>{t("Bắt đầu lượt chơi mới","Start a new attempt")}</button><button type="button" disabled={busy} onClick={()=>{speech.stop();void act("chapter","selene_01");}}>{t("Chơi lại từ chương 1","Replay from Chapter 1")}</button></div>}
  <div className="maLayout">
   <main className="maStage">
    <div className="maChapter"><small>{run.chapter_title}</small><h1>{place?.name}</h1><p>{run.objective}</p>{run.scene_note&&<p className="maSceneNote">{run.scene_note}</p>}{run.story_stages&&<ol className="maStoryStages">{run.story_stages.map(stage=><li key={stage.id} aria-current={stage.current?"step":undefined} data-complete={stage.complete}>{stage.complete?"✓":"◇"} {stage.title}</li>)}</ol>}</div>
    {!media.ready&&<div className="maPreparation" role="status"><RolePlayLoadingCat/><p>{t("Sắp xong rùi, tới ngay đây nhé!","Almost ready — we’ll be right with you!")}</p><progress value={media.progress} max={1}/><strong>{Math.round(media.progress*100)}%</strong>{media.failed>0&&<p role="alert">{preparationErrorMessage(media.errorKind,language)}</p>}{media.failed>0&&<button type="button" onClick={media.retry}>{t("Thử lại","Retry")}</button>}</div>}
    <div ref={sceneScope} className="maScene" data-world-target="scene" data-phase={run.phase} data-ready={media.ready} data-embedded={!!run.embedded_scene} data-portrait-side={portraitLeft?"left":"right"} data-background={place?.background} style={{aspectRatio:sceneRatio}}>
     {background&&<img className="maBackground" src={preparedImageSource(background.url)} alt="" onLoad={e=>{const im=e.currentTarget;if(im.naturalWidth&&im.naturalHeight)setSceneRatio(im.naturalWidth+" / "+im.naturalHeight);}} onError={e=>{e.currentTarget.style.opacity=".2";}}/>}
     <div className="maSceneShade"/>
     <MapArrivalNotice mapKey={run.attempt_number+":"+run.chapter_id+":"+place?.background} title={place?.name||""} active={active&&media.ready&&!videoPlaying&&run.phase==="explore"}/>
     {["explore","gate_ready"].includes(run.phase)&&<EmbeddedScene run={run} blocked={blocked||run.phase==="gate_ready"&&speech.waitingForDialogue||!["explore","gate_ready"].includes(run.phase)||run.reviewing} onInspect={(id,action)=>void act(action||"inspect",id)} inspectLabel={t("Quan sát ","Inspect ")}/>}
     {run.phase==="explore"&&!run.reviewing&&run.objects.filter(o=>o.mode!=="embedded").map(o=><button type="button" key={o.id} data-world-target={o.id} data-hint={o.optional?"hidden":"visible"} data-prop-mode={o.mode||"floor"} data-prop-asset={o.asset} className={"maHotspot"+(o.discovered?" maFound":"")} style={{left:o.x*100+"%",top:o.y*100+"%",width:o.width*100+"%",height:o.height*100+"%"}} aria-label={t("Quan sát ","Inspect ")+o.title} data-collected={o.collectible&&o.discovered?"true":undefined} aria-disabled={blocked||o.interactive===false||o.discovered&&o.mode!=="detail"} onClick={()=>{if(blocked||o.interactive===false)return;if(o.mode==="detail"&&o.asset)setDetail({asset:o.asset,title:o.title});if(!o.discovered)void act("inspect",o.id);}}>{o.mode!=="detail"&&!(o.collectible&&o.discovered)&&o.asset&&run.assets[o.asset]&&<img src={preparedImageSource(run.assets[o.asset].url)} alt="" loading="eager"/>}<span>{o.discovered?"✓":"✦"}</span><b>{o.title}</b></button>)}
     {!(run.phase==="memory"&&run.memory_video?.fallback.startsWith("memory_location_"))&&<div className={"maCharacter"+(speech.playing&&run.events.some(e=>e.id===speech.playing&&e.type==="CHARACTER_SPEECH")?" maSpeaking":"")} data-world-target="character">{portrait&&<img src={preparedImageSource(portrait)} alt={run.character.name} onError={e=>{e.currentTarget.src=run.assets.selene_thinking?.url||"";e.currentTarget.onerror=null;}}/>}<small>{run.character.name}</small></div>}
     <WorldCinematics run={media.ready?run:null} active={active&&media.ready&&run.phase==="intro"&&!run.reviewing} hold={speech.waitingForDialogue} onPending={setEventVideoPending} onPlaying={setEventVideoPlaying} onDone={()=>{if(run.phase==="intro"){speech.stop();void act("intro_complete");}}}/>

     {sequenceMovie&&<CinematicPlayer key={sequenceMovie.key} cue={sequenceMovie} active={active} language={language} onPlaying={setEventVideoPlaying} onDone={cancelSequenceMovie}/>}
     {run.phase==="gate_cinematic"&&run.chapter_one_flow&&media.ready&&<CinematicPlayer key={run.chapter_one_flow.key} cue={{key:run.chapter_one_flow.key,asset:run.assets[run.chapter_one_flow.cinematic],skippable:true,duration:run.assets[run.chapter_one_flow.cinematic]?.duration||8}} active={active} language={language} onPlaying={setEventVideoPlaying} onDone={()=>{speech.stop();void act("finish_gate_cinematic");}}/>}
     {showVideo&&<MemoryCinematic key={video!.key} run={run} active={active} onPlaying={setMemoryVideoPlaying} onDone={()=>{speech.stop();if(run.chapter_id==="selene_01"&&!run.reviewing)setChapterWhite(true);setVideoDismissed(video!.key);void act("finish_memory_cinematic");}}/>}
     {chapterWhite&&!run.reviewing&&!speech.waitingForDialogue&&!videoPlaying&&run.completed&&<div className="maChapterWhite" role="status"><p>{run.chapter_one_flow?.chapter_end}</p>{error&&<button onClick={()=>void act("finish_memory_cinematic")}>{t("Thử lại","Retry")}</button>}</div>}
     {!run.reviewing&&!showVideo&&sceneCaption&&<div className="maSceneSubtitle" aria-live="off"><small>{sceneCaption.type==="NARRATION"?t("DẪN TRUYỆN","NARRATION"):run.character.name}</small><p>{sceneCaption.text}</p></div>}

     {run.corner_asset&&run.assets[run.corner_asset]&&<div className="maCornerSeal" aria-hidden="true"><img src={preparedImageSource(run.assets[run.corner_asset].url)} alt=""/></div>}
     <WorldEffects run={visibleRun} active={active&&media.ready&&!videoPlaying&&!run.reviewing} scope={sceneScope}/>
     <MemoryLocationEffects eventKey={effectEvent?.id} eventType={effectEvent?.visual_event} profile={run.scene_effect||1} active={active} transitionKey={run.location+":"+run.phase}/>
    </div>
    {detail&&run.assets[detail.asset]&&<figure className="maPropDetail"><img src={preparedImageSource(run.assets[detail.asset].url)} alt={detail.title}/><figcaption>{detail.title}</figcaption><button type="button" onClick={()=>setDetail(null)} aria-label={t("Đóng","Close")}>×</button></figure>}
    {run.phase==="gate_ready"&&run.chapter_one_flow&&<p className="maGatePrompt" role="status">{run.chapter_one_flow.gate_prompt}</p>}
    {run.reviewing&&<section className="maReview"><p>{t("Đang xem lại chương đã hoàn thành","Revisiting a completed chapter")}</p><button onClick={()=>void backToChat()} disabled={busy}>{t("Trở lại trò chuyện với Selene","Return to Selene chat")}</button>{run.has_next&&run.next_chapter_id&&<button disabled={blocked} onClick={()=>{speech.stop();void act("chapter",run.next_chapter_id!);}}>{t("Sang chương tiếp theo","Next chapter")} →</button>}{run.can_replay_memory&&<button onClick={()=>void act("review_memory")} disabled={blocked||run.phase!=="explore"}>{t("Xem lại đoạn ký ức","Replay memory")}</button>}</section>}
    {run.reviewing&&<ReplayControls run={run} busy={busy} onRestart={()=>void act("restart")}/>}
    <nav className="maTools">{run.locations.map(p=><button key={p.id} disabled={blocked||run.phase!=="explore"||p.locked} aria-current={p.id===run.location?"location":undefined} data-world-target={"map:"+p.id} onClick={()=>void act("go",p.id)}>{p.name}</button>)}<button onClick={()=>setPanel("archive")}>◈ {t("Kho ký ức","Memory Archive")}</button><button onClick={()=>void act("hint")} disabled={blocked||run.phase!=="explore"}>✧ {t("Gợi ý","Hint")}</button></nav>
    {run.puzzles.map(p=><AdventurePuzzle language={language} key={p.id} puzzle={p} busy={blocked} onSolve={v=>void act("solve",v)}/>)}
    {run.choices.length>0&&<section className="maChoices"><h2>{run.choice_prompt}</h2>{run.choices.map(c=><button key={c.id} className={c.unexpected?"maUnexpected":""} disabled={blocked} onClick={()=>void act("choice",c.id)}>{c.label}</button>)}</section>}
    {run.phase==="intro"&&<button className="maPrimary" disabled={!media.ready||busy} onClick={()=>{speech.stop();void act("intro_complete");}}>{t("Bước vào câu chuyện","Enter the story")} →</button>}
    {run.phase==="memory"&&!showVideo&&error&&<button className="maPrimary" disabled={busy} onClick={()=>void act("finish_memory_cinematic")}>{t("Thử lại","Retry")}</button>}
    {run.phase==="confirm"&&<section className="maChoices"><p>{t("Bạn có thể cân nhắc lại trước khi quyết định.","You may reconsider before making this final.")}</p><button disabled={busy} onClick={()=>void act("reconsider")}>← {t("Xem lại lựa chọn","Reconsider")}</button><button disabled={busy} onClick={()=>void act("confirm_ending")}>{t("Tôi chọn điều này","This is my choice")}</button></section>}
    {active&&run.completed&&!run.reviewing&&media.ready&&!videoPlaying&&!eventVideoPending&&!showVideo&&!speech.waitingForDialogue&&<ChapterConclusion language={language} title={run.ending?.title||run.chapter_title} scroll={run.chapter_scroll||run.chapter_one_flow||undefined} text={run.chapter_outro||run.reflection_fallback} hint={run.return_hint} final={!!run.ending} share={share} preview={run.admin_preview} onShare={setShare} busy={busy} error={error} onNext={run.has_next&&run.next_chapter_id?()=>{speech.stop();setChapterWhite(false);void act("chapter",run.next_chapter_id!);}:undefined} onReturn={()=>void backToChat()} onArchive={()=>setPanel("archive")} onStay={()=>{speech.stop();cancelSequenceMovie();setChapterWhite(false);void act("review");}}><ReplayControls run={run} busy={busy} onRestart={()=>void act("restart")}/></ChapterConclusion>}

   </main>
   <aside className="maConversation"><div className="maAudioSettings">{voiceSupported&&<><select aria-label={t("Ngôn ngữ giọng đọc","Voice language")} value={speech.language} onChange={e=>speech.setLanguage(e.target.value)}><option value="off">{t("Tắt giọng","Voice off")}</option><option value="vi">Tiếng Việt</option><option value="en">English</option></select><label><input type="checkbox" checked={speech.automatic} onChange={e=>speech.setAutomatic(e.target.checked)}/>{t("Tự đọc lời nhân vật","Auto-read character dialogue")}</label><button onClick={speech.stop}>■</button></>}<select aria-label={t("Ngôn ngữ văn bản","Text language")} value={language} onChange={e=>void act("language",e.target.value)}>{UI_LANGUAGES.map(l=><option key={l.code} value={l.code}>{l.label}</option>)}</select></div>
    {run.story_language!==language&&<small>{t("Nội dung đang dùng bản tiếng Anh dự phòng.","Story text currently uses the English fallback.")}</small>}
    <div ref={transcript} className="maTranscript" aria-live="polite">{visibleEvents.filter(e=>e.presentation!=="archive"&&e.type!=="SYSTEM").slice(-16).map(e=><article key={e.id} data-world-target={"event:"+e.id} data-output-type={e.type} data-voice-role={e.voice_role||undefined} className={"maEvent maType"+e.type+(speech.playing===e.id?" maReading":"")}><small>{e.type==="NARRATION"?t("DẪN TRUYỆN","NARRATION"):e.type==="CHARACTER_SPEECH"?(e.speaker_name||run.character.name)+" · "+t("lời thoại","dialogue"):e.type==="CHARACTER_THOUGHT"?run.character.name+" · "+t("suy nghĩ","thought"):e.type==="USER"?t("Bạn","You"):t("Thế giới","World")}</small><p>{e.type==="CHARACTER_SPEECH"?<q>{e.text}</q>:e.text}</p>{voiceSupported&&(e.type==="NARRATION"||e.type==="CHARACTER_SPEECH"&&e.voice_role==="CHARACTER")&&<button aria-label={t("Nghe ","Listen to ")+(e.type==="NARRATION"?t("lời dẫn","narration"):run.character.name)} disabled={speech.language==="off"||speech.narrating&&speech.playing!==e.id} onClick={()=>speech.listen(e)}>{speech.playing===e.id?"■":"▷"}</button>}</article>)}{pendingSay&&<><article className="maEvent maTypeUSER"><small>{t("Bạn","You")}</small><p>{pendingSay}</p></article><div className="maThinking" role="status" aria-label={run.character.name+" …"}><small>{run.character.name}</small><span aria-hidden="true"><i/><i/><i/></span></div></>}</div>
    <form onSubmit={e=>{e.preventDefault();if(!blocked&&run.phase!=="gate_ready"&&!working.current&&text.trim())void act("say",text.trim());}}><textarea aria-label={t("Trò chuyện với Selene","Talk to Selene")} value={text} readOnly={!media.ready||!!run.completed&&!run.reviewing||speech.narrating||["memory","gate_ready","gate_cinematic"].includes(run.phase)||videoPlaying} maxLength={1800} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey&&!e.nativeEvent.isComposing&&e.keyCode!==229){e.preventDefault();if(!blocked&&run.phase!=="gate_ready"&&!working.current&&text.trim())e.currentTarget.form?.requestSubmit();}}} onChange={e=>setText(e.target.value)} placeholder={t("Hỏi Selene, chia sẻ điều bạn nghĩ…","Ask Selene, share a thought…")}/><button disabled={blocked||run.phase==="gate_ready"||!text.trim()}>{t("Gửi","Send")} →</button></form>
   </aside>
  </div>
  <dialog className="maDialog" ref={dialog} onCancel={()=>setPanel("")}><button className="maClose" onClick={()=>setPanel("")}>×</button>{panel==="archive"?<AdventureArchive run={run}/>:<section><h2>{t("Biên niên ký của bạn","Your Chronicle")}</h2>{run.chronicle?<div className="maChronicle">{run.chronicle.text}</div>:<button disabled={busy||writingBusy} onClick={()=>void writing("chronicle")}>{t("Viết lại hành trình của tôi","Write my journey")}</button>}</section>}</dialog>
 </div>;
}
