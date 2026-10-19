import "./MoonfallHook.css";
import {useEffect,useRef,useState} from "react";
import {api} from "./types";
import {storedLanguage,translateUiText} from "../i18n";
import {local,type LocalText} from "./moonfallTypes";
type Chapter={id:string;order:number;title:LocalText;available:boolean;completed:boolean;started:boolean;lock_reason:string;conditions?:{kind:string;previous:number;preview:boolean;unlocked:boolean;replay?:boolean;enabled?:boolean;minimum_turns:number;minimum_days?:number;minimum_trust?:number;points?:number;topic_bonus_cap?:number;trust_bonus_cap?:number;progress?:{turns?:number;points?:number}}};
type Catalog={title:LocalText;enabled:boolean;chapters:Chapter[]};
function LockIcon({open=false}:{open?:boolean}){
 return <svg className="mfChapterLock" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path className="mfLockShackle" d={open?"M8 11V6a4 4 0 0 1 8 0":"M8 11V7a4 4 0 0 1 8 0v4"}/><rect x="5" y="11" width="14" height="10" rx="3"/><path d="M12 15v2"/></svg>;
}
export function MoonfallHook({characterId,characterName="",revision,busy,onSelect,autoOpen=false,onDismiss}:{characterId:string;characterName?:string;revision:string;busy:boolean;onSelect?:(id:string)=>void;autoOpen?:boolean;onDismiss?:()=>void}){
 const [catalog,setCatalog]=useState<Catalog|null>(null),[open,setOpen]=useState(false),[loading,setLoading]=useState(true),[error,setError]=useState(""),[attempt,setAttempt]=useState(0);
 const [newly,setNewly]=useState<string[]>([]),[supported,setSupported]=useState(false),[conditionsOpen,setConditionsOpen]=useState("");
 const dialog=useRef<HTMLDialogElement>(null);
 const lang=storedLanguage(),isSelene=characterName.trim().toLowerCase()==="selene moonbrook";
 const t=(vi:string,en:string)=>{if(lang==="vi")return vi;const result=translateUiText(vi,lang);return result===vi?en:result;};
 useEffect(()=>{
  setCatalog(null);setNewly([]);setError("");setSupported(false);setOpen(autoOpen);
 },[characterId]);
 useEffect(()=>{
  if(busy)return;let live=true;setLoading(true);
  void api<Catalog>("/v1/moonfall/chapters?character_id="+encodeURIComponent(characterId)).then(data=>{
   if(!live)return;setCatalog(data);setSupported(true);setError("");
   const ids=data.chapters.filter(c=>c.available).map(c=>c.id);
   try{
    const key="moonfall-chapter-access:"+characterId,saved=localStorage.getItem(key);
    const previous=saved?JSON.parse(saved):null;
    if(Array.isArray(previous)){
     const fresh=ids.filter(id=>!previous.includes(id));
     if(fresh.length)setNewly(old=>Array.from(new Set([...old,...fresh])));
    }
    localStorage.setItem(key,JSON.stringify(ids));
   }catch{/* Storage restrictions must not prevent playing. */}
  }).catch(e=>{if(live)setError(e instanceof Error?e.message:String(e));})
   .finally(()=>{if(live)setLoading(false);});
  return()=>{live=false;};
 },[characterId,revision,busy,attempt]);
 useEffect(()=>{if(open)dialog.current?.showModal();else dialog.current?.close();},[open]);
 useEffect(()=>{if(!open||!newly.length)return;const timer=window.setTimeout(()=>setNewly([]),1800);return()=>clearTimeout(timer);},[open,newly]);
 if(!isSelene&&!supported)return null;
 const close=()=>{setOpen(false);setNewly([]);onDismiss?.();};
 const reason=(code:string)=>({
  feature_disabled:t("Cốt truyện chưa được bật ở môi trường này.","Story mode is not enabled in this environment."),
  coming_soon:t("Sắp ra mắt — chương này chưa được triển khai.","Coming soon — this chapter is not implemented yet."),
  chapter_disabled:t("Chương này đang được tạm khóa.","This chapter is temporarily unavailable."),
  continue_chat:t("Tiếp tục trò chuyện riêng với Selene để mở chương này.","Keep talking privately with Selene to unlock this chapter.")
 }[code]||t("Chưa mở khóa.","Locked."));
 return <section style={autoOpen?{display:"contents"}:undefined} className="mfChatHook" aria-label={t("Cốt truyện","Story chapters")} data-no-translate="true">
  {!autoOpen&&<button type="button" className={"mfStoryToggle"+(newly.length?" mfStoryUnlocked":"")} aria-haspopup="dialog" aria-expanded={open} onClick={()=>{setOpen(true);setAttempt(n=>n+1);}}>
   <span className="mfStorySymbol" aria-hidden="true">☾</span><span><strong>{t("Cốt truyện","Story chapters")}</strong><small>Echoes of Moonfall</small></span>
   <span className="mfStoryCount">{loading?"…":catalog?catalog.chapters.filter(c=>c.available).length+"/"+catalog.chapters.length:"—"}</span>
   <span aria-hidden="true">›</span>
  </button>}
  {newly.length>0&&<small className="mfChapterNotice" role="status">{t("Một chương vừa được mở khóa","A chapter has just unlocked")}</small>}
  <dialog ref={dialog} className="mfChapterDialog" onCancel={close} aria-label={t("Các chương Echoes of Moonfall","Echoes of Moonfall chapters")}>
   <header><div><small>ECHOES OF MOONFALL</small><h2>{t("Cốt truyện của Selene","Selene’s story")}</h2></div><button type="button" onClick={close} aria-label={t("Đóng danh sách chương","Close chapters")}>×</button></header>
   <p>{t("Mỗi chương là một phần câu chuyện. Những chương đã mở có thể vào chơi hoặc tiếp tục.","Each chapter is part of the story. Enter or resume any unlocked chapter.")}</p>
   <button type="button" className="mfChapterRefresh" disabled={loading} onClick={()=>setAttempt(n=>n+1)}>{t("Cập nhật trạng thái","Refresh status")}</button>
   {loading&&<p role="status">{t("Đang kiểm tra các chương…","Checking chapters…")}</p>}
   {error&&<div className="mfChapterError" role="alert"><p>{t("Chưa tải được cốt truyện. Nếu bản mới chưa được triển khai hoặc World chưa được cấu hình, hãy kiểm tra lại môi trường chạy.","Could not load chapters. Check that this version is deployed and World is configured.")}</p><button type="button" onClick={()=>setAttempt(n=>n+1)}>{t("Thử lại","Retry")}</button></div>}
   <div className="mfChapterList">{catalog?.chapters.map(c=>{
    const content=<><span className="mfChapterNumber">{String(c.order).padStart(2,"0")}</span><span className="mfChapterText"><strong>{local(c.title,lang)}</strong><small>{c.available?(c.completed?t("Đã hoàn thành · Trở lại","Completed · Revisit"):c.started?t("Đang chơi · Tiếp tục","In progress · Continue"):t("Đã mở · Bắt đầu","Unlocked · Start")):reason(c.lock_reason)}</small></span><LockIcon open={c.available}/></>;
    const className="mfChapterRow"+(c.available?" mfChapterAvailable":" mfChapterLocked")+(newly.includes(c.id)?" mfChapterJustUnlocked":"");
    const row=c.available?<a key={c.id} className={className} href={"/worlds?character="+encodeURIComponent(characterId)+"&chapter="+encodeURIComponent(c.id)} onClick={e=>{
     if(onSelect){e.preventDefault();onSelect(c.id);close();return;}
     if(window.parent!==window&&!e.ctrlKey&&!e.metaKey){e.preventDefault();window.parent.postMessage({type:"avibi-worlds-open",characterId,chapterId:c.id},window.location.origin);}
     close();
    }}>{content}</a>:<button key={c.id} type="button" className={className} disabled aria-label={local(c.title,lang)+" · "+reason(c.lock_reason)}>{content}</button>;
     const q=c.conditions;
     return <div key={c.id} className="mfChapterItem">{row}<button type="button" className="mfConditionBook" aria-label={t("Điều kiện mở chương","Chapter requirements")+" "+c.order} aria-expanded={conditionsOpen===c.id} onClick={()=>setConditionsOpen(conditionsOpen===c.id?"":c.id)}><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" aria-hidden="true"><path d="M12 5v15M12 5C8 2 3 3 2 4v15c3-2 7-1 10 1 3-2 7-3 10-1V4c-3-2-7-1-10 1Z"/></svg></button>{conditionsOpen===c.id&&q&&<section className="mfConditions"><strong>{t("Điều kiện mở chương","Chapter requirements")}</strong>
     {q.preview&&<p>{t("Admin preview: các chương đều mở, không ảnh hưởng tài khoản khác.","Admin preview: all chapters are available; other accounts are unaffected.")}</p>}
     {q.kind==="entry"?<><p>{t("Lượt trò chuyện có ý nghĩa tối thiểu","Minimum meaningful chat turns")}: {q.minimum_turns}</p><p>{t("Số ngày trò chuyện tối thiểu","Minimum distinct chat days")}: {q.minimum_days}</p><p>{t("Tin tưởng tối thiểu","Minimum trust")}: {Math.round((q.minimum_trust||0)*100)}%</p></>:<><p>{t("Hoàn thành chương","Complete chapter")} {q.previous}.</p>{q.enabled&&!q.replay&&!q.unlocked&&<><p>{t("Lượt trò chuyện có ý nghĩa tối thiểu","Minimum meaningful chat turns")}: {q.progress?.turns||0}/{q.minimum_turns}</p><p>{t("Điểm mở chương","Chapter unlock points")}: {q.progress?.points||0}/{q.points}</p><p>{t("Mỗi lượt chat hợp lệ được 1 điểm; trò chuyện đúng chủ đề và tăng tin tưởng có thể giúp mở sớm hơn.","Each meaningful chat turn earns 1 point. Relevant topics and growing trust can unlock the chapter sooner.")} (+{q.topic_bonus_cap}, +{q.trust_bonus_cap})</p></>}{(q.unlocked||q.replay)&&<p>{t("Chương đã mở không yêu cầu tích điểm lại.","Unlocked chapters do not require earning points again.")}</p>}</>}
     </section>}</div>;

   })}</div>
   {!loading&&!catalog&&!error&&<p>{t("Chưa có chương truyện cho nhân vật này.","No chapters are available for this character yet.")}</p>}
  </dialog>
 </section>;
}
