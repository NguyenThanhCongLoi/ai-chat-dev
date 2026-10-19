import {useEffect,useRef,useState} from "react";
import {api} from "./api";
import {storedLanguage,translateUiText} from "../i18n";
import {CharacterAvatar} from "./CharacterCards";
import {loadExpressionPortrait} from "./EmotionPortrait";
import type {Character,Message} from "./types";
import "./character-social.css";

type Identity={id:string;name:string;role:string};
type Connection={id:string;character_id:string;other:Identity;active:boolean;state:string;label:string;
 interaction_count:number;first_met_at:string|null;canon:{text:string;revision:number}|null;
 known_facts:{kind:string;value:Identity;source:string}[];reverse?:Connection|null};
type Props={actor:Character;candidates:Character[];roomId:string;messages:Message[];busy:boolean;
 resolveCharacter:(c:Character)=>Promise<Character>};

export function CharacterSocial({actor,candidates,roomId,messages,busy,resolveCharacter}:Props){
 const[open,setOpen]=useState(false),[links,setLinks]=useState<Connection[]>([]),[chosen,setChosen]=useState<Character|null>(null);
 const[current,setCurrent]=useState<Connection|null>(null),[phase,setPhase]=useState("idle"),[error,setError]=useState("");
 const[surprises,setSurprises]=useState<Record<string,string>>({});
 const[suggestion,setSuggestion]=useState<Identity|null>(null),[pending,setPending]=useState(false),[loadingLinks,setLoadingLinks]=useState(true);
 const dialog=useRef<HTMLDialogElement>(null),alive=useRef(true),timer=useRef<number|undefined>(undefined),operation=useRef(false);
 const t=(vi:string,en:string)=>{const lang=storedLanguage();const translated=translateUiText(vi,lang);return lang==="vi"?vi:translated===vi?en:translated;};
 const base="/v1/roleplay/characters/"+encodeURIComponent(actor.id);
 const path=(id:string)=>"/v1/roleplay/character-connections/"+id;
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;window.clearTimeout(timer.current);};},[]);
 useEffect(()=>{if(open){dialog.current?.showModal();}else dialog.current?.close();},[open]);
 async function refresh(){
  setLoadingLinks(true);
  try{const rows=await api<Connection[]>(base+"/connections");if(alive.current){setLinks(rows);setCurrent(previous=>previous?rows.find(row=>row.id===previous.id)||previous:null);}}
  finally{if(alive.current)setLoadingLinks(false);}
 }
 useEffect(()=>{if(open)void refresh().catch(e=>setError(e.message));},[open,base]);
 const lastUser=[...messages].reverse().find(m=>m.sender_type==="user");
 useEffect(()=>{
  setSuggestion(null);if(!lastUser||busy)return;let live=true;
  void api<{candidate:Identity|null}>(base+"/connection-suggestion?room_id="+encodeURIComponent(roomId)+"&message_id="+encodeURIComponent(lastUser.id))
   .then(r=>{if(live&&r.candidate&&!sessionStorage.getItem("social-dismiss:"+actor.id+":"+r.candidate.id))setSuggestion(r.candidate);})
   .catch(()=>{});return()=>{live=false;};
 },[lastUser?.id,busy,base,roomId,actor.id]);
 const pool=candidates.filter((c,i,list)=>c.id!==actor.id&&(!actor.preset_type||c.preset_type!==actor.preset_type)
  &&list.findIndex(x=>(x.preset_type||x.id)===(c.preset_type||c.id))===i);
 function choose(c:Character){
  window.clearTimeout(timer.current);setChosen(c);const found=links.find(l=>l.other.id===c.id);
  setCurrent(found||null);setPhase(found?.active?"rest":"idle");setSurprises({});setError("");
 }
 async function connect(){
  if(!chosen||operation.current)return;operation.current=true;setPending(true);setPhase("saving");setError("");
  try{
   const target=await resolveCharacter(chosen);
   const result=await api<Connection>(base+"/connections","POST",{other_character_id:target.id,mutual:true});
   if(!alive.current)return;setChosen(target);setCurrent(result);setPhase("connected");setSuggestion(null);
   for(const c of [actor,target])void loadExpressionPortrait(c.id,"surprised").then(url=>{if(alive.current)setSurprises(s=>({...s,[c.id]:url}));}).catch(()=>{});
   timer.current=window.setTimeout(()=>{if(alive.current){setPhase("rest");setSurprises({});}},1200);
   void refresh().catch(()=>{});
  }catch(e){if(alive.current){setPhase("error");setError(e instanceof Error?e.message:String(e));}}
  finally{operation.current=false;if(alive.current)setPending(false);}
 }
 async function disconnect(){
  if(!current||operation.current)return;operation.current=true;setPending(true);setError("");
  try{
   const result=await api<Connection>(path(current.id),"DELETE");
   if(!alive.current)return;setCurrent(result);setPhase("idle");void refresh().catch(()=>{});
  }catch(e){if(alive.current)setError(e instanceof Error?e.message:String(e));}
  finally{operation.current=false;if(alive.current)setPending(false);}
 }
 const labels:Record<string,string>={introduced:t("Đã được giới thiệu","Introduced"),acquaintance:t("Đã quen mặt","Acquaintances"),friend:t("Bạn bè","Friends"),suspicious:t("Còn nghi ngại","Wary"),rival:t("Có cạnh tranh","Rivals")};
 const status=current?.state==="RELATIONSHIP"?t("Đã có câu chuyện chung","A shared history"):current?.state==="MET"?t("Đã gặp nhau","Have met"):current?t("Biết đến nhau, chưa có cuộc gặp được ghi nhận","Introduced; no recorded meeting"):t("Chưa được giới thiệu","Not introduced");
 function portrait(c:Character){return <div className="csPortrait"><CharacterAvatar character={c} className="csAvatar"/>{phase==="connected"&&surprises[c.id]&&<img className="csSurprise" src={surprises[c.id]} alt="" onError={()=>setSurprises(s=>{const next={...s};delete next[c.id];return next;})}/>}<b className="csBang" aria-hidden="true">!</b><strong translate="no">{c.name}</strong></div>;}
 return <section className="csEntry">
  <button type="button" className="btn" disabled={busy} onClick={()=>{setError("");setLoadingLinks(true);setOpen(true);}}>{t("Mối liên kết","Connections")} ✧</button>
  {suggestion&&<div className="csSuggestion"><span>{t("Bạn đang nhắc đến","Do you mean")} <b translate="no">{suggestion.name}</b>?</span>
   <button type="button" disabled={busy} onClick={()=>{const found=candidates.find(c=>c.id===suggestion.id);if(found){choose(found);setOpen(true);}}}>{t("Giới thiệu họ","Introduce them")}</button>
   <button type="button" onClick={()=>{sessionStorage.setItem("social-dismiss:"+actor.id+":"+suggestion.id,"1");setSuggestion(null);}}>{t("Không phải / bỏ qua","No / dismiss")}</button></div>}
  <dialog className="csDialog" ref={dialog} aria-labelledby={"cs-title-"+actor.id} onCancel={e=>{if(pending)e.preventDefault();else setOpen(false);}}>
   <header><div><small>{t("NHỮNG CUỘC GẶP BẠN TẠO NÊN","THE CONNECTIONS YOU MAKE")}</small><h2 id={"cs-title-"+actor.id}>{t("Cho các nhân vật làm quen","Let them know each other")}</h2></div>
    <button type="button" disabled={pending} aria-label={t("Đóng","Close")} onClick={()=>setOpen(false)}>×</button></header>
   <p>{t("Chỉ giới thiệu tên và vai trò. Chat riêng, ký ức và bí mật không được chia sẻ.","Only names and roles are introduced. Private chats, memories and secrets stay separate.")}</p>
   <label>{t("Chọn một nhân vật","Choose a character")}<select aria-label={t("Chọn một nhân vật","Choose a character")} value={chosen?.id||""} disabled={pending||loadingLinks} onChange={e=>{const c=pool.find(c=>c.id===e.target.value);if(c)choose(c);}}>
    <option value="">{t("Chọn người để giới thiệu…","Choose someone to introduce…")}</option>{pool.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
   {chosen&&<><div className={"csMoment cs-"+phase+" cs-kind-"+(current?.label||"introduced")} data-state={current?.state||"UNKNOWN"} aria-busy={pending}>
    {portrait(actor)}<button type="button" className="csThread" disabled={pending||!!current?.active} onClick={()=>void connect()} aria-label={t("Kết nối hai nhân vật","Introduce these characters")}><svg viewBox="0 0 220 50" aria-hidden="true"><path d="M5 25 Q110 5 215 25"/><circle cx="110" cy="16" r="5"/></svg><span className="csFlash" aria-hidden="true">✦</span><span>{phase==="saving"?t("Đang gửi lời giới thiệu…","Introducing…"):current?.active?"✧":t("Chạm để giới thiệu","Tap to introduce")}</span></button>{portrait(chosen)}
   </div><p className="csStatus" role="status">{phase==="error"?t("Chưa kết nối được. Bạn có thể thử lại.","Not connected. You can try again."):phase==="saving"?t("Đang chờ xác nhận…","Waiting for confirmation…"):status}</p>
   <div className="csRolePreview"><span>{actor.name}: {actor.identity?.role||t("Nhân vật","Character")}</span><span>{chosen.name}: {chosen.identity?.role||t("Nhân vật","Character")}</span></div>
   {current&&<div className="csDetails"><h3>{actor.name} → {current.other.name}</h3><p>{labels[current.label]||current.label} · {current.interaction_count} {t("lượt chung","shared turns")}</p>
    {current.first_met_at&&<p>{t("Gặp lần đầu được ghi nhận","First recorded meeting")}: {new Date(current.first_met_at).toLocaleDateString(storedLanguage())}</p>}
    {!current.active&&<p>{t("Đã ngắt liên kết hiển thị; lịch sử và điều đã biết vẫn còn.","Active connection removed; history and learned knowledge remain.")}</p>}
    <h4>{t("Điều đã biết","Known information")}</h4>{current.known_facts.map((f,i)=><p key={i}>{f.value.name} · {f.value.role}</p>)}
    {current.reverse&&<p>{current.other.name} → {current.reverse.other.name}: {labels[current.reverse.label]||current.reverse.label}</p>}
    <p>{t("Họ chỉ gặp nhau khi bạn tạo phòng nhóm có cả hai và họ cùng trò chuyện.","They meet only when you create a group with both and they actually participate.")}</p>
    <footer>{current.active?<button className="btn" type="button" disabled={pending} onClick={()=>void disconnect()}>{t("Ngắt liên kết","Disconnect")}</button>:<button className="btn" type="button" disabled={pending} onClick={()=>void connect()}>{t("Giới thiệu lại","Reconnect")}</button>}</footer>
   </div>}</>}
   {!chosen&&links.length>0&&<nav className="csExisting">{links.map(l=><button key={l.id} type="button" onClick={()=>{const c=candidates.find(c=>c.id===l.other.id);if(c)choose(c);}}>{l.other.name} · {labels[l.label]||l.label}{!l.active?" · "+t("Đã ngắt","Inactive"):""}</button>)}</nav>}
   {error&&<p role="alert" className="csError">{error}</p>}
  </dialog>
 </section>;
}
