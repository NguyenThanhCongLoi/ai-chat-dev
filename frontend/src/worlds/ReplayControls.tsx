import {useState} from "react";
import type {AdventureRun} from "./adventureTypes";
import {worldUi} from "./worldUi";
export function ReplayControls({run,busy,onRestart}:{run:AdventureRun;busy:boolean;onRestart:()=>void}){
 const [confirm,setConfirm]=useState(false);
 const t=(vi:string,en:string)=>worldUi(vi,en,run.content_language);
 if(!run.can_restart&&!run.ending_collection?.some(e=>e.discovered))return null;
 return <section className="maReplayControls">
  <h3>{t("Các kết đã khám phá","Discovered endings")} · {run.ending_collection?.filter(e=>e.discovered).length||0}/{run.ending_collection?.length||4}</h3>
  <ul>{run.ending_collection?.map(e=><li key={e.id}>{e.discovered?"✓":"🔒"} {e.title}</li>)}</ul>
  {run.ending_is_new===false&&run.completed&&<p>{t("Bạn đã khám phá kết này ở lượt trước. Kết cũ được giữ nguyên và không phát lại.","You discovered this ending in an earlier attempt. It stays in your collection without playing again.")}</p>}
  {run.can_restart&&(confirm?<div><p>{t("Bắt đầu lại từ chương 1. Manh mối và lựa chọn của lượt này sẽ được làm mới; bộ sưu tập kết vẫn được giữ.","Start again from Chapter 1. This attempt's clues and choices will reset; your ending collection will stay.")}</p>
   <button disabled={busy} onClick={()=>{setConfirm(false);onRestart();}}>{t("Bắt đầu lượt chơi mới","Start a new attempt")}</button>
   <button disabled={busy} onClick={()=>setConfirm(false)}>{t("Đóng","Close")}</button></div>:<button disabled={busy} onClick={()=>setConfirm(true)}>{t("Chơi lại từ chương 1","Replay from Chapter 1")}</button>)}
 </section>;
}
