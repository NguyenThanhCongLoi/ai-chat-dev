import type {ReactNode} from "react";
import {useEffect,useRef} from "react";
import {worldUi} from "./worldUi";
export function ChapterConclusion({language,title,text,hint,final,share,preview,onShare,busy,error,onReturn,onArchive,onStay,children,scroll,onNext}:{language:string;title:string;text:string;hint?:string;final?:boolean;share:boolean;preview?:boolean;onShare:(value:boolean)=>void;busy:boolean;error:string;onReturn:()=>void;onArchive:()=>void;onStay:()=>void;children?:ReactNode;onNext?:()=>void;scroll?:{chapter_end:string;scroll_title:string;scroll_body:string}}){
 const dialog=useRef<HTMLDialogElement>(null);
 const t=(vi:string,en:string)=>worldUi(vi,en,language);
 useEffect(()=>{const d=dialog.current;if(d&&!d.open)d.showModal();return()=>{d?.close();};},[]);
 return <dialog ref={dialog} className="maChapterConclusion" onCancel={e=>{e.preventDefault();if(!busy)onStay();}} aria-labelledby="maConclusionTitle">
  <small>{final?t("HỒI TRUYỆN KHÉP LẠI","ARC COMPLETE"):t("CHƯƠNG HOÀN THÀNH","CHAPTER COMPLETE")}</small><h2 id="maConclusionTitle">{title}</h2>{scroll?<div className="maScrollSequence"><p className="maEndSentence">{scroll.chapter_end}</p><section className="maParchment"><h3>{scroll.scroll_title}</h3><p>{scroll.scroll_body}</p></section></div>:<blockquote>{text}</blockquote>}
  {hint&&<p>{hint}</p>}
  {!preview&&<label className="maShareMemory"><input type="checkbox" checked={share} onChange={e=>onShare(e.target.checked)}/>{t("Cho Selene nhớ trải nghiệm này trong chat thường","Let Selene remember this in normal chat")}</label>}
  {children}
  {error&&<p role="alert">{error}</p>}
  {onNext&&<button type="button" disabled={busy} onClick={onNext}>{t("Sang chương tiếp theo","Next chapter")} →</button>}
  <button type="button" className="maPrimary" autoFocus disabled={busy} onClick={onReturn}>{t("Trở lại trò chuyện với Selene","Return to Selene chat")} →</button>
  <button type="button" disabled={busy} onClick={onStay}>{t("Ở lại chương này","Stay in this chapter")}</button>
  <button type="button" disabled={busy} onClick={onArchive}>{t("Xem ký ức đã giữ","View recovered memories")}</button>
 </dialog>;
}
