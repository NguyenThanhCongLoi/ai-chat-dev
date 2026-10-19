import {useEffect,useRef,useState} from "react";
import {api} from "./api";
import {storedLanguage,translateUiText} from "../i18n";
import "./continuity.css";
import {EpisodeNotes} from "./EpisodeNotes";

type Lore={id:string;title:string;text:string;scope:string;knowers:string[];keywords:string[];priority:number;canon:boolean;always:boolean;unlocked:boolean};
type Config={revision:number;scene:{location:string;time:string;objective:string};lore:Lore[];use_memory:boolean;auto_memory:boolean};
type Memory={id:string;content:string;type:string;pinned:boolean;confidence:number;importance:number;scope:string;source_text:string;created_at:string;selected:boolean;used_last_turn:boolean};
type Inspector={memories:Memory[];budget:number;estimated_characters:number;last_trace_at:string|null;visible_lore_ids:string[]};
type Timeline={id:string;type:string;confidence:number;valence:number;source_text:string;created_at:string;deltas:Record<string,number>};
type Recap={items:{id:string;speaker:string;text:string;created_at:string}[]};
type Tab="memory"|"scene"|"lore"|"timeline"|"recap";
const blankLore=():Lore=>({id:crypto.randomUUID(),title:"",text:"",scope:"public",knowers:[],keywords:[],priority:5,canon:false,always:true,unlocked:false});

export function RoleplayContinuity({roomId,characters,revision,busy}:{roomId:string;characters:{id:string;name:string}[];revision:string;busy:boolean}){
 const[open,setOpen]=useState(false),[tab,setTab]=useState<Tab>("memory"),[actor,setActor]=useState(characters[0]?.id||"");
 const[config,setConfig]=useState<Config|null>(null),[inspect,setInspect]=useState<Inspector|null>(null),[timeline,setTimeline]=useState<Timeline[]>([]),[recap,setRecap]=useState<Recap|null>(null);
 const[entry,setEntry]=useState<Lore>(blankLore),[error,setError]=useState(""),[notice,setNotice]=useState(""),[pending,setPending]=useState(false),[load,setLoad]=useState(0);
 const dialog=useRef<HTMLElement>(null),bodyRef=useRef<HTMLDivElement>(null);
 const [editing,setEditing]=useState<string|null>(null);
 useEffect(()=>{bodyRef.current?.scrollTo({top:0});},[tab,actor,open]);
 useEffect(()=>{const refresh=()=>setLoad(n=>n+1);window.addEventListener("roleplay-memories-changed",refresh);return()=>window.removeEventListener("roleplay-memories-changed",refresh);},[]);
 const language=storedLanguage(),t=(a:string,_b:string)=>language==="vi"?a:translateUiText(a,language);
 const base="/v1/roleplay/rooms/"+encodeURIComponent(roomId);
 const percent=(value:number)=>Math.round(Math.max(0,Math.min(1,value))*100);
 useEffect(()=>{if(!open)return;let live=true;setConfig(null);setError("");void api<Config>(base+"/continuity").then(c=>{if(live)setConfig(c);}).catch(e=>{if(live)setError(String(e.message));});return()=>{live=false;};},[open,base]);
 useEffect(()=>{if(!open||busy||!actor)return;let live=true;setError("");
  if(tab==="memory"){setInspect(null);void api<Inspector>(base+"/inspect?character_id="+encodeURIComponent(actor)).then(c=>{if(live)setInspect(c);}).catch(e=>{if(live)setError(String(e.message));});}
  if(tab==="timeline"){setTimeline([]);void api<Timeline[]>(base+"/timeline?character_id="+encodeURIComponent(actor)).then(c=>{if(live)setTimeline(c);}).catch(e=>{if(live)setError(String(e.message));});}
  if(tab==="recap"){setRecap(null);void api<Recap>(base+"/recap").then(c=>{if(live)setRecap(c);}).catch(e=>{if(live)setError(String(e.message));});}
  return()=>{live=false;};
 },[open,base,actor,tab,revision,busy,load]);
 useEffect(()=>{if(!open)return;const previous=document.activeElement as HTMLElement|null;dialog.current?.querySelector<HTMLElement>("button")?.focus();
  const key=(e:KeyboardEvent)=>{if(e.key==="Escape"&&!pending)setOpen(false);if(e.key==="Tab"){const nodes=Array.from(dialog.current?.querySelectorAll<HTMLElement>("button:not(:disabled),input:not(:disabled),textarea,select")||[]).filter(n=>n.getClientRects().length);const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}};
  window.addEventListener("keydown",key);return()=>{window.removeEventListener("keydown",key);previous?.focus();};
 },[open,pending]);
 async function work(fn:()=>Promise<void>){if(pending||busy)return;setPending(true);setError("");setNotice("");try{await fn();setLoad(n=>n+1);}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setPending(false);}}
 async function save(next:Config){const updated=await api<Config>(base+"/continuity","PUT",next);setConfig(updated);setNotice(t("Đã lưu. Áp dụng từ câu trả lời tiếp theo.","Saved. Applies to the next reply."));}
 async function savePreferences(next:Config){const previous=config;setConfig(next);try{await save(next);}catch(e){setConfig(previous);throw e;}}
 const blocked=pending||busy;
 const scope=(value:string)=>({public:t("Cả phòng biết","Known to the room"),private:t("Một nhân vật biết","One character knows"),witnessed:t("Người chứng kiến","Witnesses only"),rumor:t("Tin đồn","Rumour"),discovered:t("Chờ khám phá","Awaiting discovery"),CHARACTER_PRIVATE:t("Riêng nhân vật","Character private"),ROOM_SHARED:t("Chung phòng","Room shared"),USER_GLOBAL:t("Toàn tài khoản","Account-wide")}[value]||value);
 const eventName=(value:string)=>({interaction:t("Tương tác","Interaction"),appreciation:t("Được trân trọng","Appreciation"),sharing:t("Chia sẻ","Sharing"),repair:t("Làm lành","Repair"),conflict:t("Bất đồng","Conflict"),dismissal:t("Bị gạt đi","Dismissal"),boundary:t("Đặt giới hạn","Boundary"),boundary_setting:t("Đặt giới hạn","Boundary"),meaningful_sharing:t("Chia sẻ ý nghĩa","Meaningful sharing")}[value]||value);
 return <div className="rpContinuityEntry"><button className="btn sm" onClick={()=>setOpen(true)}>✧ {t("Ký ức & cốt truyện","Memory & story")}</button>
  {open&&<div className="scrim rpContinuityScrim" onMouseDown={e=>{if(e.target===e.currentTarget&&!pending)setOpen(false);}}>
   <section className="dialog rpContinuityDialog" ref={dialog} role="dialog" aria-modal="true" data-no-translate="true" aria-label={t("Ký ức và cốt truyện Roleplay","Roleplay memory and story")}>
    <header><div><small>{t("CHAT BOT AI · PHÒNG HIỆN TẠI","CHAT BOT AI · CURRENT ROOM")}</small><h2>{t("Điều câu chuyện đang giữ lại","What this story remembers")}</h2></div><button className="btn sm" disabled={pending} aria-label={t("Đóng bảng cốt truyện","Close story panel")} onClick={()=>setOpen(false)}>×</button></header>
    <nav className="rpContinuityTabs" aria-label={t("Công cụ cốt truyện","Story tools")}>{([["memory","Ký ức","Memory"],["scene","Bối cảnh","Scene"],["timeline","Nhật ký phiên","Session journal"]] as const).map(([id,a,b])=><button className={"btn sm "+(tab===id||id==="scene"&&tab==="lore"||id==="timeline"&&tab==="recap"?"active":"")} aria-pressed={tab===id||id==="scene"&&tab==="lore"||id==="timeline"&&tab==="recap"} key={id} onClick={()=>{setTab(id);setNotice("");}}>{t(a,b)}</button>)}</nav>
    <div className="body rpContinuityBody" ref={bodyRef}>
     {(tab==="timeline"||tab==="recap")&&<div className="rpContinuityJournalTabs"><button className="btn sm" onClick={()=>setTab("timeline")}>{t("Mốc quan hệ","Relationship timeline")}</button><button className="btn sm" onClick={()=>setTab("recap")}>{t("Nhật ký phiên","Session journal")}</button></div>}
     {error&&<p role="alert" className="error">{error}<button onClick={()=>void work(async()=>{setConfig(await api<Config>(base+"/continuity"));})}>{t("Tải lại cấu hình","Reload settings")}</button></p>}
     {notice&&<p role="status" className="rpContinuityNotice">{notice}</p>}
     {(tab==="memory"||tab==="timeline"||tab==="lore"||tab==="recap")&&<label className="field"><span>{t("Góc nhìn nhân vật","Character perspective")}</span><select aria-label={t("Góc nhìn nhân vật","Character perspective")} className="input" value={actor} onChange={e=>setActor(e.target.value)}>{characters.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}</select></label>}
     {tab==="memory"&&<>
      {!inspect?<p aria-busy="true">…</p>:<>
       <details className="rpContinuityAdvanced"><summary>{t("Tùy chọn ghi nhớ","Memory settings")}</summary>
        {config&&<div className="rpContinuitySwitches"><label><input type="checkbox" checked={config.use_memory} disabled={blocked} onChange={e=>{const next={...config,use_memory:e.target.checked};void work(()=>savePreferences(next));}}/>{t("Dùng ký ức đã lưu trong phòng này","Use saved memories in this room")}</label><label><input type="checkbox" checked={config.auto_memory} disabled={blocked} onChange={e=>{const next={...config,auto_memory:e.target.checked};void work(()=>savePreferences(next));}}/>{t("Tự lưu ký ức và reflection mới từ phòng này","Automatically save new memories and reflections from this room")}</label></div>}
        <p className="rpContinuityMuted">{t("Tắt ký ức không xóa lịch sử chat, quan hệ hoặc ký ức đã lưu.","Disabling memory does not erase chat history, relationships or stored memories.")}</p>
        <div className="rpContinuityUsage"><b>{inspect.estimated_characters}/{inspect.budget}</b><span>{t("ký tự dự kiến cho ký ức","predicted memory characters")}</span><progress max={inspect.budget} value={inspect.estimated_characters}/></div>
        <p className="rpContinuityMuted">{t("Dự kiến được chọn là kết quả truy hồi theo tin user gần nhất; Đã dùng ở lượt trước dựa trên prompt trace. Đây là ngân sách ký tự, không phải token.","Predicted selection uses the latest user message; Last turn comes from the prompt trace. The budget counts characters, not tokens.")}</p>
       </details>
       {!inspect.memories.length&&<p>{t("Chưa có ký ức phù hợp. Bạn vẫn có thể thêm qua nút Ký ức của nhân vật/phòng.","No memories are available. Add one with the existing character/room memory control.")}</p>}
       {inspect.memories.map(m=><article className="rpContinuityCard" key={m.id}>
        <div className="rpContinuityBadges">{m.pinned&&<span>⌖ {t("Đã ghim","Pinned")}</span>}{m.used_last_turn&&<span>{t("Đã dùng ở lượt trước","Used last turn")}</span>}<span>{scope(m.scope)}</span></div>
        {editing===m.id?<textarea aria-label={t("Ký ức","Memory")} className="input" maxLength={1000} value={m.content} onChange={e=>setInspect({...inspect,memories:inspect.memories.map(x=>x.id===m.id?{...x,content:e.target.value}:x)})}/>:<p>{m.content}</p>}
        <details><summary>{t("Nguồn hình thành","Source")}</summary><small>{t("Tin cậy","Confidence")} {percent(m.confidence)}% · {m.selected?t("Dự kiến được chọn","Predicted selection"):""}</small>{m.source_text?<blockquote>{m.source_text}</blockquote>:<small>{t("Thêm thủ công hoặc nguồn không còn khả dụng","Manually added or source no longer available")}</small>}</details>
        <div className="rpContinuityActions">
         <button className="btn sm" disabled={blocked} onClick={()=>void work(async()=>{await api("/v1/memories/"+m.id,"PATCH",{pinned:!m.pinned});})}>{m.pinned?t("Bỏ ghim","Unpin"):t("Ghim","Pin")}</button>
         {editing!==m.id?<button className="btn sm" onClick={()=>setEditing(m.id)}>{t("Sửa","Edit")}</button>:<><button className="btn sm" disabled={blocked||!m.content.trim()} onClick={()=>void work(async()=>{await api("/v1/memories/"+m.id,"PATCH",{content:m.content});setEditing(null);})}>{t("Lưu","Save")}</button><button className="btn sm danger" disabled={blocked} onClick={()=>{if(confirm(t("Xóa ký ức này?","Delete this memory?")))void work(async()=>{await api("/v1/memories/"+m.id,"DELETE");});}}>{t("Xóa","Delete")}</button></>}
        </div>
       </article>)}
      </>}
     </>}
     {tab==="scene"&&config&&<form onSubmit={e=>{e.preventDefault();void work(()=>save(config));}}>
      <p>{t("Bối cảnh áp dụng ngay trong chat thường. Bot nhận các trường này ở lượt tiếp theo; không sửa persona nhân vật.","This scene applies to ordinary chat on the next reply, without replacing the character persona.")}</p>
      {([["location","Địa điểm","Location",120],["time","Thời điểm","Time",120],["objective","Mục tiêu đang dang dở","Open objective",400]] as const).map(([key,a,b,max])=><label className="field" key={key}><span>{t(a,b)}</span><input className="input" maxLength={max} value={config.scene[key]} onChange={e=>setConfig({...config,scene:{...config.scene,[key]:e.target.value}})}/></label>)}
      <button className="btn primary" disabled={blocked}>{t("Lưu bối cảnh","Save scene")}</button>
      <details className="rpContinuityAdvanced"><summary>{t("Nâng cao","Advanced")}</summary><button className="btn" type="button" onClick={()=>setTab("lore")}>{t("Lore & bí mật","Lore & secrets")}</button></details>
     </form>}
     {tab==="lore"&&config&&<>
      <p className="rpContinuityMuted">{t("Lore của phòng riêng này. Lọc người biết trước khi so khớp từ khóa; không đưa lore này vào kho công khai. Canon khóa tính nhất quán trong prompt, không thay thế kiểm duyệt. Không thể giữ bí mật nội dung đã nói ra trong lịch sử chung.","Lore belongs to this private room. Knowledge scope is checked before keyword matching. Canon guides consistency without overriding moderation. Content already spoken in shared chat cannot be made secret retroactively.")}</p>
      <div className="rpContinuityList">{config.lore.map(e=><article className="rpContinuityCard" key={e.id}><div className="rpContinuityBadges"><span>{scope(e.scope)}</span>{e.canon&&<span>CANON</span>}<span>{e.always?t("Luôn xét","Always considered"):e.keywords.join(", ")}</span></div><b>{e.title}</b><p>{e.text}</p><small>{e.scope==="private"||e.scope==="witnessed"?e.knowers.map(id=>characters.find(c=>c.id===id)?.name||id).join(", "):""}</small><div className="rpContinuityActions"><button className="btn sm" onClick={()=>setEntry({...e})}>{t("Sửa","Edit")}</button><button className="btn sm danger" disabled={blocked} onClick={()=>void work(()=>save({...config,lore:config.lore.filter(x=>x.id!==e.id)}))}>{t("Xóa","Delete")}</button></div></article>)}</div>
      <form className="rpContinuityLoreForm" onSubmit={e=>{e.preventDefault();void work(async()=>{await save({...config,lore:[...config.lore.filter(x=>x.id!==entry.id),entry]});setEntry(blankLore());});}}>
       <h3>{config.lore.some(e=>e.id===entry.id)?t("Sửa lore","Edit lore"):t("Thêm lore hoặc bí mật","Add lore or a secret")}</h3>
       <label className="field"><span>{t("Tiêu đề","Title")}</span><input className="input" required maxLength={150} value={entry.title} onChange={e=>setEntry({...entry,title:e.target.value})}/></label>
       <label className="field"><span>{t("Nội dung","Text")}</span><textarea className="input" required maxLength={1500} value={entry.text} onChange={e=>setEntry({...entry,text:e.target.value})}/></label>
       <label className="field"><span>{t("Ai được biết?","Who knows?")}</span><select aria-label={t("Ai được biết?","Who knows?")} className="input" value={entry.scope} onChange={e=>setEntry({...entry,scope:e.target.value,canon:e.target.value==="rumor"?false:entry.canon,knowers:[]})}>{["public","private","witnessed","rumor","discovered"].map(s=><option key={s} value={s}>{scope(s)}</option>)}</select></label>
       {(entry.scope==="private"||entry.scope==="witnessed")&&<div className="rpContinuitySwitches">{characters.map(c=><label key={c.id}><input type={entry.scope==="private"?"radio":"checkbox"} name="lore-knower" checked={entry.knowers.includes(c.id)} onChange={e=>setEntry({...entry,knowers:entry.scope==="private"?[c.id]:e.target.checked?[...entry.knowers,c.id]:entry.knowers.filter(id=>id!==c.id)})}/>{c.name}</label>)}</div>}
       <details className="rpContinuityAdvanced"><summary>{t("Nâng cao","Advanced")}</summary>
       <label className="field"><span>{t("Từ khóa / alias, phân cách dấu phẩy","Keywords / aliases, comma separated")}</span><input className="input" value={entry.keywords.join(",")} onChange={e=>setEntry({...entry,keywords:e.target.value.split(",")})}/></label>
       <div className="rpContinuitySwitches"><label><input type="checkbox" checked={entry.always} onChange={e=>setEntry({...entry,always:e.target.checked})}/>{t("Luôn xét đưa vào context","Always consider for context")}</label><label><input type="checkbox" disabled={entry.scope==="rumor"} checked={entry.canon} onChange={e=>setEntry({...entry,canon:e.target.checked})}/>{t("Canon cố định","Locked canon")}</label>{entry.scope==="discovered"&&<label><input type="checkbox" checked={entry.unlocked} onChange={e=>setEntry({...entry,unlocked:e.target.checked})}/>{t("Đã khám phá","Discovered")}</label>}</div>
       </details>
       <button className="btn primary" disabled={blocked||config.lore.length>=40&&!config.lore.some(e=>e.id===entry.id)}>{t("Lưu lore","Save lore")}</button> <button type="button" className="btn" onClick={()=>setEntry(blankLore())}>{t("Soạn mục mới","New entry")}</button>
      </form>
     </>}
     {tab==="timeline"&&<>
      <p>{t("Các tín hiệu quan hệ đã ghi cho nhân vật trong phòng này; confidence là ước lượng, không phải cảm xúc thật của AI.","Recorded relationship signals for this character in this room; confidence is an estimate, not an AI's real feelings.")}</p>
      {!timeline.length&&<p className="rpContinuityMuted">{t("Chưa có mốc được ghi. Không tạo mốc giả để lấp danh sách.","No milestones recorded yet.")}</p>}
      <ol className="rpContinuityTimeline">{timeline.map(e=><li key={e.id}><b>{eventName(e.type)}</b><small>{e.created_at} · {t("Tin cậy","Confidence")} {percent(e.confidence)}%</small>{e.source_text&&<blockquote>{e.source_text}</blockquote>}{Object.keys(e.deltas).length>0&&<small>{Object.entries(e.deltas).map(([k,v])=>k+": "+(v>0?"+":"")+v).join(" · ")}</small>}</li>)}</ol>
     </>}
     {tab==="recap"&&<>
      <EpisodeNotes key={roomId+actor} base={base} actor={actor} busy={blocked}/>
      <p>{t("Trích tối đa 10 đoạn gần đây, có người nói. Đây là nhật ký trích dẫn, chưa phải bản tóm tắt AI.","Up to 10 recent attributed excerpts. This is an extractive journal, not an AI summary.")}</p>
      {recap?.items.map(e=><article className="rpContinuityCard" key={e.id}><small>{e.speaker} · {e.created_at}</small><p>{e.text}</p></article>)}
      {!!recap?.items.length&&<button className="btn" onClick={()=>{const blob=new Blob([recap.items.map(e=>e.speaker+": "+e.text).join("\n\n")],{type:"text/plain;charset=utf-8"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="roleplay-journal.txt";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}>{t("Tải nhật ký riêng","Download private journal")}</button>}
     </>}
    </div>
   </section>
  </div>}
 </div>;
}
