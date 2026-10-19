import {useEffect,useState} from "react";
import {RolePlayLoadingCat} from "../roleplay/RolePlayLoadingCat";
import {prepareWorldEntryResources} from "./worldIntroMedia";
import {storedLanguage} from "../i18n";
import {worldUi} from "./worldUi";
import "../assistant/home-preparation.css";
import StoryExperience from "./StoryExperience";
import MoonfallAdmin from "./MoonfallAdmin";
import WorldHub from "./WorldHub";
import type {WorldProps} from "./moonfallTypes";
function ReadyWorld(props:WorldProps){
 const character=props.characterId||new URLSearchParams(location.search).get("character")||undefined;
 if(location.pathname==="/worlds/admin")return <MoonfallAdmin/>;
 return character?<StoryExperience {...props} characterId={character} adminPreview={new URLSearchParams(location.search).get("preview")==="1"} previewRunId={new URLSearchParams(location.search).get("run")||undefined} chapterId={props.chapterId||new URLSearchParams(location.search).get("chapter")||undefined}/>:<WorldHub {...props}/>;
}


export default function WorldApp(props:WorldProps){
 const [ready,setReady]=useState(false),[progress,setProgress]=useState(0),[error,setError]=useState(false),[attempt,setAttempt]=useState(0);
 const direct=!!(props.characterId||new URLSearchParams(location.search).get("character"));
 useEffect(()=>{
  if(direct||props.active===false||location.pathname==="/worlds/admin")return;
  let live=true;setError(false);setProgress(0);
  void prepareWorldEntryResources(value=>{if(live)setProgress(Math.max(0,Math.min(100,Math.floor(value*100))));}).then(()=>{if(live)setReady(true);}).catch(()=>{if(live)setError(true);});
  return()=>{live=false;};
 },[direct,props.active,attempt]);
 if(!direct&&!ready&&location.pathname!=="/worlds/admin")return <div className="assistantGate" role="status"><RolePlayLoadingCat/><p>{worldUi("Sắp xong rùi, tới ngay đây nhé!","Almost ready — we’ll be right with you!",storedLanguage())}</p><div className="homePreparationProgress"><progress aria-label={worldUi("Đang chuẩn bị cảnh…","Preparing the scene…",storedLanguage())} max={100} value={progress}/><span>{progress}%</span></div>{error&&<button onClick={()=>setAttempt(n=>n+1)}>{worldUi("Thử lại","Retry",storedLanguage())}</button>}</div>;
 return <ReadyWorld {...props}/>;
}
