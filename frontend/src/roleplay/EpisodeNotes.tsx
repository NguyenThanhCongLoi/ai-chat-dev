import {useEffect,useState} from "react";
import {api} from "./api";
import {storedLanguage,translateUiText} from "../i18n";

type Event={text:string;source_ids:string[];kind:string};
type Note={summary:string;perspective:string;events:Event[];source_ids:string[];created_at:string;revision:number};
type State={episode:Note|null;graph:{nodes:(Event&{id:string})[];edges:{from:string;to:string;relation:string}[]}};

export function EpisodeNotes({base,actor,busy}:{base:string;actor:string;busy:boolean}){
 const[data,setData]=useState<State|null>(null),[pending,setPending]=useState(false),[error,setError]=useState("");
 const[edit,setEdit]=useState(false),[summary,setSummary]=useState(""),[perspective,setPerspective]=useState("");
 const language=storedLanguage(),t=(a:string,b:string)=>language==="vi"?a:(translateUiText(a,language)||b);
 const url=base+"/episode";
 useEffect(()=>{let live=true;setData(null);setEdit(false);setError("");
  void api<State>(url+"?character_id="+encodeURIComponent(actor)).then(r=>{if(live)setData(r);}).catch(e=>{if(live)setError(e.message);});
  return()=>{live=false;};
 },[url,actor]);
 async function work(kind:"generate"|"delete"|"save"){
  setPending(true);setError("");
  try{
   if(kind==="delete"){await api(url+"?character_id="+encodeURIComponent(actor),"DELETE");setData({episode:null,graph:{nodes:[],edges:[]}});}
   else setData(await api<State>(url,kind==="save"?"PUT":"POST",kind==="save"?{character_id:actor,revision:data?.episode?.revision,summary,perspective}:{character_id:actor}));
   setEdit(false);
  }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setPending(false);}
 }
 const note=data?.episode;
 return <section className="rpContinuityCard">
  <h3>{t("Tóm tắt & góc nhìn nhân vật","Recap & character perspective")}</h3>
  <p>{t("Chỉ tạo khi bạn yêu cầu, có thể dùng model tính phí. Tóm tắt tối đa 60 tin nhắn gần đây; góc nhìn là suy luận có thể sai, không phải canon.","Created on request and may incur model charges. Covers up to 60 recent messages; perspective is fallible interpretation, not canon.")}</p>
  <button className="btn sm" disabled={busy||pending||!actor} onClick={()=>void work("generate")}>{pending?"…":note?t("Cập nhật recap AI","Update AI recap"):t("Tạo recap AI","Create AI recap")}</button>
  {error&&<p role="alert">{error}</p>}
  {note&&<>
   <small>{note.created_at} · {note.source_ids.length} {t("tin nhắn nguồn","source messages")}</small>
   {edit?<><label className="field">{t("Tóm tắt","Summary")}<textarea aria-label={t("Tóm tắt","Summary")} maxLength={1800} value={summary} onChange={e=>setSummary(e.target.value)}/></label><label className="field">{t("Góc nhìn","Perspective")}<textarea aria-label={t("Góc nhìn","Perspective")} maxLength={900} value={perspective} onChange={e=>setPerspective(e.target.value)}/></label><button className="btn sm" disabled={pending||busy} onClick={()=>void work("save")}>{t("Lưu","Save")}</button><button className="btn sm" disabled={pending} onClick={()=>setEdit(false)}>{t("Hủy","Cancel")}</button></>:<><p>{note.summary}</p><blockquote>{note.perspective}</blockquote><button className="btn sm" disabled={pending||busy} onClick={()=>{setSummary(note.summary);setPerspective(note.perspective);setEdit(true);}}>{t("Sửa ghi chú","Edit notes")}</button></>}
   <details><summary>{t("Chuỗi sự kiện & nguồn","Event chain & sources")}</summary><p>{t("Các sự kiện theo thứ tự liệt kê; đường nối không khẳng định quan hệ nhân quả.","Events in listed order; links do not establish causation.")}</p><ol className="rpContinuityTimeline">{data?.graph.nodes.map(e=><li key={e.id}><b>{e.kind}</b><p>{e.text}</p><small>{t("Nguồn","Sources")}: {e.source_ids.join(", ")}</small></li>)}</ol></details>
   <button className="btn sm" disabled={pending||busy} onClick={()=>void work("delete")}>{t("Xóa recap và góc nhìn","Delete recap and perspective")}</button>
  </>}
 </section>;
}
