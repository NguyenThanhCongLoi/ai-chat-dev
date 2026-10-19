/** Ordinary-chat CMS. Uses admin Basic session, never the user's Bearer token. */
import {useEffect,useState} from "react";
import "./roleplay-lorebook.css";
type Character={id:string;name:string;source:string;owner?:string};
type Entry={id?:string;revision?:number;title:string;text:string;scope:string;targets:string[];knowers:string[];keywords:string[];enabled:boolean;canon:boolean;always:boolean;priority:number};
type Data={entries:Entry[];characters:Character[]};
const fresh=(target?:string):Entry=>({title:"",text:"",scope:"public",targets:target?[target]:[],knowers:[],keywords:[],enabled:true,canon:false,always:false,priority:5});
async function admin<T>(path="",method="GET",body?:unknown):Promise<T>{
 const r=await fetch("/v1/admin/roleplay-lorebook"+path,{method,credentials:"same-origin",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined});
 const result=await r.json().catch(()=>null);
 if(!r.ok)throw new Error(typeof result?.detail==="string"?result.detail:"Lỗi "+r.status);return result;
}
export default function RoleplayLorebook(){
 const[data,setData]=useState<Data|null>(null),[editing,setEditing]=useState<Entry|null>(null),[error,setError]=useState(""),[status,setStatus]=useState("");
 const[query,setQuery]=useState(""),[characterQuery,setCharacterQuery]=useState(""),[stateFilter,setStateFilter]=useState("all"),[busy,setBusy]=useState(false),[dirty,setDirty]=useState(false),[keywords,setKeywords]=useState("");
 const preferred=new URLSearchParams(location.search).get("character")||"";
 const name=(id:string)=>data?.characters.find(c=>c.id===id)?.name||id;
 async function load(){try{setData(await admin<Data>());}catch(e){setError(e instanceof Error?e.message:String(e));}}
 useEffect(()=>{void load();},[]);
 useEffect(()=>{if(!dirty)return;const warn=(e:BeforeUnloadEvent)=>{e.preventDefault();e.returnValue="";};window.addEventListener("beforeunload",warn);return()=>window.removeEventListener("beforeunload",warn);},[dirty]);
 function choose(entry:Entry){if(dirty&&!confirm("Bỏ các thay đổi chưa lưu?"))return;setEditing(structuredClone(entry));setKeywords(entry.keywords.join(", "));setDirty(false);setStatus("");setError("");}
 function patch(value:Partial<Entry>){if(editing){setEditing({...editing,...value});setDirty(true);setStatus("");}}
 async function save(){
  if(!editing||busy)return;setBusy(true);setError("");setStatus("");
  try{const payload={...editing,keywords:keywords.split(/[,;\n]/).map(s=>s.trim()).filter(Boolean)};
   const entry=await admin<Entry>(editing.id?"/"+editing.id:"",editing.id?"PUT":"POST",payload);
   setEditing(entry);setKeywords(entry.keywords.join(", "));setDirty(false);await load();setStatus("Đã lưu. Lore áp dụng cho lượt chat thường tiếp theo; lore riêng trong phòng và World được giữ nguyên.");
  }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 async function remove(){
  if(!editing?.id||busy||!confirm("Xóa lore gốc này? Các lượt trả lời cũ không bị xóa."))return;
  setBusy(true);setError("");try{await admin("/"+editing.id+"?revision="+editing.revision,"DELETE");setEditing(null);setDirty(false);await load();setStatus("Đã xóa lore gốc.");}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 const entries=(data?.entries||[]).filter(e=>(!preferred||e.targets.includes(preferred))&&(stateFilter==="all"||e.enabled===(stateFilter==="enabled"))&&(e.title+" "+e.targets.map(name).join(" ")).toLocaleLowerCase().includes(query.toLocaleLowerCase()));
 const candidates=(data?.characters||[]).filter(c=>editing?.targets.includes(c.id)||c.name.toLocaleLowerCase().includes(characterQuery.toLocaleLowerCase())||c.id.includes(characterQuery)).sort((a,b)=>Number(editing?.targets.includes(b.id))-Number(editing?.targets.includes(a.id))).slice(0,100);
 return <div className="rpLoreCms" data-no-translate="true">
  <header><div><small>CMS · CHAT ROLEPLAY THƯỜNG</small><h1>Lorebook nhân vật</h1><p>Quản lý kiến thức gốc của nhân vật. Không sửa prompt tính cách, ký ức riêng của user hoặc World.</p></div><a href="/admin">← CMS chính</a></header>
  {error&&<div className="rpLoreError" role="alert">{error}<button onClick={()=>void load()}>Tải lại danh sách</button><small>Nếu có xung đột phiên bản, chọn lại mục trong danh sách trước khi sửa.</small></div>}
  {status&&<p className="rpLoreSuccess" role="status">{status}</p>}
  <main><aside><div className="rpLoreListHead"><h2>Kiến thức gốc <span>{entries.length}</span></h2><button disabled={busy||!data} onClick={()=>choose(fresh(preferred&&data?.characters.some(c=>c.id===preferred)?preferred:undefined))}>＋ Thêm lore</button></div>
   <input aria-label="Tìm lore" placeholder="Tìm theo tiêu đề hoặc nhân vật…" value={query} onChange={e=>setQuery(e.target.value)}/>
   <select aria-label="Trạng thái lore" value={stateFilter} onChange={e=>setStateFilter(e.target.value)}><option value="all">Tất cả trạng thái</option><option value="enabled">Đang bật</option><option value="disabled">Đang tắt</option></select>
   {preferred&&<p>Đang lọc: {name(preferred)} · <a href="/roleplay/lorebook/admin">Xem tất cả</a></p>}
   {!data?<p>Đang tải…</p>:!entries.length?<div className="rpLoreEmpty">Chưa có lore phù hợp. Thêm một mục và gán cho nhân vật để bắt đầu.</div>:<nav>{entries.map(e=><button disabled={busy} aria-current={editing?.id===e.id?"true":undefined} key={e.id} onClick={()=>choose(e)}><b>{e.title}</b><small>{e.targets.map(name).join(" · ")}</small><span>{e.enabled?"● Đang bật":"○ Đang tắt"} · {e.scope==="private"?"Riêng nhân vật":e.scope==="witnessed"?"Chỉ người biết":e.scope==="rumor"?"Tin đồn":"Kiến thức chung"}{e.canon?" · Canon":""}</span></button>)}</nav>}
  </aside><section className="rpLoreEditor">{editing?<form onSubmit={e=>{e.preventDefault();void save();}}><div className="rpLoreEditorHead"><h2>{editing.id?"Sửa lore":"Tạo lore mới"}{dirty&&<small> · Chưa lưu</small>}</h2><label className="rpLoreCheck"><input type="checkbox" checked={editing.enabled} onChange={e=>patch({enabled:e.target.checked})}/> Bật mục này</label></div>
   <label>Tiêu đề<input required maxLength={150} value={editing.title} onChange={e=>patch({title:e.target.value})}/></label>
   <label>Nội dung kiến thức<textarea required rows={8} maxLength={1500} value={editing.text} onChange={e=>patch({text:e.target.value})}/><small>Viết dữ kiện hoặc bối cảnh, không dùng ô này để thay thế tính cách hay yêu cầu vượt quy tắc an toàn.</small></label>
   <fieldset><legend>Gán cho nhân vật</legend><small>Chỉ những nhân vật được gán mới có thể nhận mục lore này.</small><input aria-label="Tìm nhân vật" placeholder="Tìm nhân vật theo tên hoặc ID…" value={characterQuery} onChange={e=>setCharacterQuery(e.target.value)}/>
    <div className="rpLoreCharacterPicker">{candidates.map(c=><label key={c.id} className="rpLoreCheck"><input type="checkbox" disabled={!editing.targets.includes(c.id)&&editing.targets.length>=50} checked={editing.targets.includes(c.id)} onChange={e=>{const targets=e.target.checked?[...editing.targets,c.id]:editing.targets.filter(i=>i!==c.id);patch({targets,knowers:editing.knowers.filter(i=>targets.includes(i))});}}/><span>{c.name}<small>{c.source==="system"?"Nhân vật hệ thống":c.owner?"User: "+c.owner:"Nhân vật"} · {c.id}</small></span></label>)}</div>
    {editing.targets.filter(id=>!data?.characters.some(c=>c.id===id)).map(id=><p key={id}>{id} — không còn tồn tại <button type="button" onClick={()=>patch({targets:editing.targets.filter(i=>i!==id),knowers:editing.knowers.filter(i=>i!==id)})}>Bỏ gán</button></p>)}
   </fieldset>
   <div className="rpLoreColumns"><label>Phạm vi kiến thức<select aria-label="Phạm vi kiến thức" value={editing.scope} onChange={e=>patch({scope:e.target.value,knowers:[],canon:e.target.value==="rumor"?false:editing.canon})}><option value="public">Chung cho các nhân vật được gán</option><option value="private">Chỉ một nhân vật biết</option><option value="witnessed">Chỉ các nhân vật được đánh dấu biết</option><option value="rumor">Tin đồn, chưa xác minh</option></select></label>
    <label>Ưu tiên (0–10)<input type="number" min={0} max={10} value={editing.priority} onChange={e=>patch({priority:Number(e.target.value)})}/></label></div>
   {["private","witnessed"].includes(editing.scope)&&<fieldset><legend>Ai được biết nội dung này?</legend>{editing.targets.length?editing.targets.map(id=><label className="rpLoreCheck" key={id}><input type={editing.scope==="private"?"radio":"checkbox"} name="lore-knowers" checked={editing.knowers.includes(id)} onChange={e=>patch({knowers:editing.scope==="private"?[id]:e.target.checked?[...editing.knowers,id]:editing.knowers.filter(k=>k!==id)})}/>{name(id)}</label>):<p>Gán nhân vật trước.</p>}</fieldset>}
   <label>Từ khóa hoặc tên gọi khác<input value={keywords} onChange={e=>{setKeywords(e.target.value);setDirty(true);}} placeholder="Nguyệt thạch, moonstone, tháp phía bắc"/><small>Tối đa 12 từ khóa, cách nhau bằng dấu phẩy. Được đối chiếu với tin hiện tại và hội thoại gần đây.</small></label>
   <label className="rpLoreCheck"><input type="checkbox" checked={editing.always} onChange={e=>patch({always:e.target.checked})}/> Luôn đưa vào khi còn ngân sách context</label>
   <label className="rpLoreCheck"><input type="checkbox" disabled={editing.scope==="rumor"} checked={editing.canon} onChange={e=>patch({canon:e.target.checked})}/> Canon: dữ kiện gốc cần được tôn trọng</label>
   <p className="rpLoreNote">Quyền được biết được lọc trước khi chọn theo từ khóa. Canon được ưu tiên trong giới hạn context; khi mâu thuẫn với lore trong phòng, nhân vật được hướng dẫn hỏi lại.</p>
   <footer><button className="rpLorePrimary" disabled={busy||!editing.targets.length}>{busy?"Đang lưu…":"Lưu lorebook"}</button>{editing.id&&<button type="button" className="rpLoreDanger" disabled={busy} onClick={()=>void remove()}>Xóa mục này</button>}</footer>
  </form>:<div className="rpLoreEmpty"><h2>Kiến thức giúp nhân vật nhất quán</h2><p>Chọn một mục hoặc bấm “Thêm lore”. User vẫn có thể viết lore riêng trong phòng; họ không sửa bản gốc ở đây.</p><p>Cập nhật ở đây áp dụng từ lượt chat tiếp theo, không viết lại lịch sử cũ.</p></div>}</section></main>
 </div>;
}
