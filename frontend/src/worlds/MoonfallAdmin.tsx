import {readWorldJson} from "./worldHttp";
/** Separate story CMS; reuses existing admin authentication and model credentials. */
import {useEffect,useState} from "react";
import {UI_LANGUAGES} from "../i18n";
import type {LocalText} from "./moonfallTypes";
import "./moonfall.css";
import NarratorVoicePicker from "./NarratorVoicePicker";
import AdventureAdmin from "./AdventureAdmin";
import HubNarrationAdmin from "./HubNarrationAdmin";
import {WORLD_EFFECTS} from "./worldEffectRegistry";
type RecordData=Record<string,any>;
type Config=RecordData&{revision:number;enabled:boolean;character_source_id:string;title:LocalText;arc_title:LocalText;pitch:LocalText;hook:LocalText;intro_narration:LocalText;instruction:string;model_id:string;tts_model_id:string;narrator_voices:{en:string;vi:string};entry_gate:RecordData;hints:RecordData;emotional_access:RecordData;relationship_delta_cap:number;bgm:string;intro_asset:string;chapters:RecordData[];assets:RecordData[];visual_events:Record<string,RecordData>};
type Data={config:Config;models:{id:string;name:string;tts:boolean}[];characters:{id:string;name:string}[];music:{id:string;title:string}[]};
async function admin<T>(method="GET",value?:unknown):Promise<T>{
 const response=await fetch("/v1/admin/moonfall",{method,credentials:"same-origin",headers:value?{"Content-Type":"application/json"}:{},body:value?JSON.stringify(value):undefined});
 const result=await readWorldJson(response);if(!response.ok)throw new Error(typeof result.detail==="string"?result.detail:"Không lưu được: "+response.status);return result;
}
function JsonEditor({label,value,onChange,invalid}:{label:string;value:unknown;onChange:(value:any)=>void;invalid:(bad:boolean)=>void}){
 const serialized=JSON.stringify(value,null,2),[text,setText]=useState(serialized),[error,setError]=useState("");
 useEffect(()=>{setText(serialized);setError("");invalid(false);},[serialized]);
 return <label className="mfCmsJson">{label}<textarea value={text} spellCheck={false} rows={10} onChange={e=>{setText(e.target.value);try{JSON.parse(e.target.value);setError("");invalid(true);}catch{setError("JSON chưa hợp lệ; không thể lưu bản nháp này.");invalid(true);}}} onBlur={()=>{try{const parsed=JSON.parse(text);if(label==="Story configuration"&&(!Array.isArray(parsed.chapters)||!Array.isArray(parsed.assets)||!parsed.entry_gate||!parsed.hints||!parsed.narrator_voices))throw new Error();onChange(parsed);setError("");invalid(false);}catch{setError("JSON chưa hợp lệ hoặc thiếu trường bắt buộc.");invalid(true);}}}/>{error&&<span role="alert">{error}</span>}</label>;
}
export default function MoonfallAdmin(){
 const [data,setData]=useState<Data|null>(null),[cfg,setCfg]=useState<Config|null>(null),[tab,setTab]=useState("world"),[chapterId,setChapterId]=useState("selene_01"),[locale,setLocale]=useState("vi");
 const [error,setError]=useState(""),[saved,setSaved]=useState(false),[busy,setBusy]=useState(false),[dirty,setDirty]=useState(false),[badJson,setBadJson]=useState<Record<string,boolean>>({});
 async function load(){try{const d=await admin<Data>();setData(d);setCfg(d.config);setError("");setDirty(false);setBadJson({});}catch(e){setError(e instanceof Error?e.message:String(e));}}
 useEffect(()=>{void load();},[]);
 useEffect(()=>{const warn=(e:BeforeUnloadEvent)=>{if(dirty){e.preventDefault();e.returnValue="";}};window.addEventListener("beforeunload",warn);return()=>window.removeEventListener("beforeunload",warn);},[dirty]);
 function patch(fn:(next:Config)=>void){setCfg(old=>{if(!old)return old;const next=structuredClone(old);fn(next);return next;});setSaved(false);setDirty(true);}
 function bad(key:string,flag:boolean){setBadJson(old=>old[key]===flag?old:{...old,[key]:flag});}
 function text(label:string,value:LocalText,onChange:(v:LocalText)=>void,rows=3){
  return <label>{label} <small>{locale.toUpperCase()}</small><textarea rows={rows} value={value?.[locale]||""} onChange={e=>{const next={...value};if(!e.target.value&&locale!=="vi"&&locale!=="en")delete next[locale];else next[locale]=e.target.value;onChange(next);}}/></label>;
 }
 async function save(){if(!cfg)return;setBusy(true);setError("");try{const next=await admin<Config>("PUT",cfg);setCfg(next);setDirty(false);setSaved(true);}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 const ch=cfg?.chapters.find(c=>c.id===chapterId),idx=cfg?.chapters.findIndex(c=>c.id===chapterId)??0;
 const chapterPatch=(key:string,value:unknown)=>patch(c=>{c.chapters[idx][key]=value;});
 if(cfg?.schema_version===2&&data)return <AdventureAdmin initial={data}/>;
 return <main className="mfCms" data-no-translate="true"><header><div><small>WORLD STUDIO · ECHOES OF MOONFALL</small><h1>Biên tập câu chuyện Selene</h1></div><nav><a href="/admin">CMS chính</a><a href="/worlds">Xem World</a></nav></header>
 <p>World mới thay giao diện Academy. Nội dung chat thường và tính cách gốc không bị ghi đè. Bản lưu áp dụng cho lượt chơi mới; tiến trình đang chơi giữ phiên bản cũ.</p>
 {error&&<p className="mfCmsError" role="alert">{error} <button onClick={()=>void load()}>Tải lại</button></p>}
 {saved&&<p className="mfCmsSuccess" role="status">Đã lưu phiên bản {cfg?.revision}. Chương 1 sẵn sàng cho lượt chơi mới.</p>}
 {!cfg||!data?<p>Đang tải cấu hình…</p>:<>
 <div className="mfCmsToolbar"><nav>{[["world","Thế giới & giọng nói"],["chapters","Chương truyện"],["assets","Ảnh / video / âm thanh"],["events","Hoạt ảnh"],["advanced","JSON nâng cao"]].map(([id,label])=><button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}>{label}</button>)}</nav><label>Ngôn ngữ đang biên tập<select value={locale} onChange={e=>setLocale(e.target.value)}>{UI_LANGUAGES.map(l=><option key={l.code} value={l.code}>{l.label}</option>)}</select></label></div>
 <div className="mfCmsBody">
 {tab==="world"?<><div className="mfCmsGrid"><section><h2>World & nhân vật</h2><label><input type="checkbox" checked={cfg.enabled} onChange={e=>patch(c=>{c.enabled=e.target.checked;})}/>Bật Echoes of Moonfall</label>
 {text("Tên thế giới",cfg.title,v=>patch(c=>{c.title=v;}))}{text("Tên hồi truyện",cfg.arc_title,v=>patch(c=>{c.arc_title=v;}))}{text("Giới thiệu",cfg.pitch,v=>patch(c=>{c.pitch=v;}))}
 <label>Nhân vật Selene từ kho hệ thống<select value={cfg.character_source_id} onChange={e=>patch(c=>{c.character_source_id=e.target.value;})}><option value="">Tự nhận đúng Selene Moonbrook</option>{data.characters.map(a=><option key={a.id} value={a.id}>{a.name} · {a.id}</option>)}</select></label><small>Chọn card Selene đã có; không nhập lại prompt/cá tính tại đây. Nếu chưa có, khôi phục nhân vật từ backup/CMS nhân vật.</small>
 {text("Lời hẹn gợi mở trong chat thường",cfg.hook,v=>patch(c=>{c.hook=v;}))}
 <label>Chỉ dẫn hội thoại World<textarea rows={5} value={cfg.instruction} onChange={e=>patch(c=>{c.instruction=e.target.value;})}/></label></section>
 <section><h2>Model & giọng nói</h2><label>Model hội thoại<select value={cfg.model_id} onChange={e=>patch(c=>{c.model_id=e.target.value;})}><option value="">Dùng model Roleplay đã gán</option>{data.models.map(m=><option value={m.id} key={m.id}>{m.name}</option>)}</select></label>
 <label>Provider TTS người kể<select value={cfg.tts_model_id} onChange={e=>patch(c=>{c.tts_model_id=e.target.value;})}><option value="">Dùng provider TTS hiện có</option>{data.models.filter(m=>m.tts).map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
 <NarratorVoicePicker modelId={cfg.tts_model_id} value={cfg.narrator_voices} onChange={(language,id)=>patch(c=>{c.narrator_voices[language]=id;})}/>
 <p>Giọng Selene và model TTS lấy đúng cấu hình chat thường; lựa chọn provider ở đây chỉ dành cho người kể. Người kể phải dùng Voice ID khác. Suy nghĩ và thông báo không có TTS. API key tiếp tục quản lý trong Kết nối/model hoặc env.</p>
 <label>Nhạc nền — dùng chung playlist chat thường<select value={cfg.bgm.startsWith("shared:")?cfg.bgm:"shared:"} onChange={e=>patch(c=>{c.bgm=e.target.value;})}><option value="shared:">Bài đầu trong playlist đang được duyệt</option>{data.music.map(m=><option key={m.id} value={"shared:"+m.id}>{m.title}</option>)}</select></label>
 <h3>Điều kiện mở lời hẹn</h3>{[["min_trust","Trust tối thiểu",.01,1],["min_meaningful_turns","Lượt có ý nghĩa",1,100],["min_days","Ngày trò chuyện khác nhau",1,365]].map(([key,label,step,max])=><label key={key}>{label}<input type="number" min="0" max={max} step={step} value={cfg.entry_gate[key]} onChange={e=>patch(c=>{c.entry_gate[key]=Number(e.target.value);})}/></label>)}<small>Không tính tin spam, câu lặp hay tin chưa có phản hồi. Để test nhanh, có thể đặt các ngưỡng bằng 0.</small></section></div>
 <HubNarrationAdmin locale={locale}/><section><h2>Mở đầu điện ảnh</h2>{text("Lời người kể — không gắn cứng vào video",cfg.intro_narration,v=>patch(c=>{c.intro_narration=v;}),4)}
 <label>Asset intro<select value={cfg.intro_asset} onChange={e=>patch(c=>{c.intro_asset=e.target.value;})}>{cfg.assets.filter(a=>a.type==="VIDEO").map(a=><option value={a.id} key={a.id}>{a.id}</option>)}</select></label></section>
 <section><h2>Gợi ý và độ mở cảm xúc</h2><label><input type="checkbox" checked={cfg.hints.enabled} onChange={e=>patch(c=>{c.hints.enabled=e.target.checked;})}/>Bật gợi ý bằng suy nghĩ</label><div className="mfCmsGrid">{[["cooldown_seconds","Khoảng cách giữa gợi ý (giây)",3,300],["idle_seconds","Thời gian không tiến triển (giây)",15,3600],["stalled_turns","Lượt không tiến triển",1,20]].map(([key,label,min,max])=><label key={key}>{label}<input type="number" min={min} max={max} value={cfg.hints[key]} onChange={e=>patch(c=>{c.hints[key]=Number(e.target.value);})}/></label>)}</div>
 <div className="mfCmsGrid">{Object.entries(cfg.emotional_access).map(([k,v])=><label key={k}>Ngưỡng {k}<input type="number" min="0" max="1" step=".01" value={v as number} onChange={e=>patch(c=>{c.emotional_access[k]=Number(e.target.value);})}/></label>)}<label>Delta trust tối đa khi tìm manh mối mới<input type="number" min="0" max=".03" step=".001" value={cfg.relationship_delta_cap} onChange={e=>patch(c=>{c.relationship_delta_cap=Number(e.target.value);})}/></label></div><small>Độ mở khác với biểu cảm tức thời. Điểm chỉ áp dụng World; không ghi đè điểm quan hệ chat thường.</small></section>
 </>:tab==="chapters"&&ch?<><nav className="mfCmsChapters">{cfg.chapters.map(c=><button key={c.id} aria-pressed={chapterId===c.id} onClick={()=>setChapterId(c.id)}>{c.order}. {c.title.vi} {!c.implemented?"· Dự kiến":""}</button>)}</nav>
 {!ch.implemented&&<p className="mfCmsNotice">Đây là khung chuẩn bị nội dung. Runtime chương 2–8 chưa triển khai, không thể bật cho người chơi.</p>}
 <section><h2>{ch.id}</h2><label><input type="checkbox" disabled={!ch.implemented} checked={ch.enabled} onChange={e=>chapterPatch("enabled",e.target.checked)}/>Cho phép chơi chương</label>
 {text("Tên chương",ch.title,v=>chapterPatch("title",v))}{text("Mục tiêu",ch.objective,v=>chapterPatch("objective",v))}
 {text("Lời mở đầu Selene nói",ch.opening_speech,v=>chapterPatch("opening_speech",v))}{text("Suy nghĩ mở đầu — không đọc thành tiếng",ch.opening_thought,v=>chapterPatch("opening_thought",v))}
 {text("Lời kết chương",ch.completion,v=>chapterPatch("completion",v),4)}
 <div className="mfCmsGrid"><label>Manh mối cần tìm<input type="number" min="1" max="20" value={ch.required_clues} onChange={e=>chapterPatch("required_clues",Number(e.target.value))}/></label><label>Độ khó (thông tin biên tập)<input type="number" min="1" max="5" value={ch.difficulty} onChange={e=>chapterPatch("difficulty",Number(e.target.value))}/><small>Chưa tự đổi câu đố hay mức gợi ý. Mức gợi ý do 3 nội dung bên dưới quyết định.</small></label>
 <label>Độ mở tối đa<select value={ch.max_access} onChange={e=>chapterPatch("max_access",e.target.value)}>{["GUARDED","OPEN","VULNERABLE","DEEPLY_CONNECTED"].map(x=><option key={x}>{x}</option>)}</select></label></div></section>
 <section><h2>Manh mối và 3 mức gợi ý</h2>{ch.clues.map((clue:RecordData,i:number)=><details key={clue.id}><summary>{clue.id} · {clue.title.vi}</summary>
 {text("Tên manh mối",clue.title,v=>patch(c=>{c.chapters[idx].clues[i].title=v;}))}
 {text("Dữ kiện khi phát hiện",clue.fact,v=>patch(c=>{c.chapters[idx].clues[i].fact=v;}),4)}
 {text("Suy nghĩ khi phát hiện",clue.thought,v=>patch(c=>{c.chapters[idx].clues[i].thought=v;}))}
 {text("Lời nói phản ứng của Selene",clue.reaction||{en:"",vi:""},v=>patch(c=>{c.chapters[idx].clues[i].reaction=v;}))}
 <label>Ảnh vật thể<select value={clue.asset||""} onChange={e=>patch(c=>{c.chapters[idx].clues[i].asset=e.target.value;})}><option value="">Không dùng ảnh</option>{cfg.assets.filter(a=>a.type==="IMAGE").map(a=><option key={a.id} value={a.id}>{a.id}</option>)}</select></label>
 <label>Từ khóa hội thoại (phân cách bằng dấu ;)<input value={clue.keywords.join("; ")} onChange={e=>patch(c=>{c.chapters[idx].clues[i].keywords=e.target.value.split(";").map(x=>x.trim()).filter(Boolean);})}/></label>
 {clue.hints.map((h:LocalText,n:number)=>text(["Gợi ý nhẹ","Chỉ hướng","Chỉ dẫn rõ"][n],h,v=>patch(c=>{c.chapters[idx].clues[i].hints[n]=v;})))}
 <label>Biểu cảm<select value={clue.expression} onChange={e=>patch(c=>{c.chapters[idx].clues[i].expression=e.target.value;})}>{["neutral","happy","sad","angry","surprised","shy","thinking"].map(e=><option key={e}>{e}</option>)}</select></label>
 </details>)}</section>
 <section><h2>Ký ức và phạm vi chia sẻ</h2>{text("Tên ký ức",ch.reward.title,v=>patch(c=>{c.chapters[idx].reward.title=v;}))}
 {text("Dữ kiện ký ức — không chứa transcript",ch.reward.fact,v=>patch(c=>{c.chapters[idx].reward.fact=v;}),4)}
 <label>Phạm vi<select value={ch.reward.scope} onChange={e=>patch(c=>{c.chapters[idx].reward.scope=e.target.value;})}>{["WORLD_ONLY","CHARACTER_ONLY","USER_AND_CHARACTER","NORMAL_CHAT_SHARED","SECRET","CANON"].map(x=><option key={x}>{x}</option>)}</select></label>
 <small>Chỉ NORMAL_CHAT_SHARED đủ điều kiện chuyển sang chat thường khi user đồng ý. SECRET/CANON không xuất ra nhật ký người chơi.</small></section>
 <section><h2>Địa điểm, lựa chọn, canon và điều kiện</h2>{(["locations","choices","canon"] as const).map(key=><JsonEditor key={chapterId+key} label={key==="canon"?"Lore / bí mật / HARD_CANON (requires_clue để khóa)":key==="choices"?"Lựa chọn và story flags":"Địa điểm / asset / vị trí / manh mối cần có"} value={ch[key]} onChange={v=>chapterPatch(key,v)} invalid={flag=>bad(key,flag)}/>)}<small>Engine kiểm tra điều kiện; LLM không tự cấp vật phẩm/flags. Nội dung chương sau không được gửi vào prompt chương hiện tại.</small></section>
 </>:tab==="assets"?<><h2>Manifest tài nguyên</h2><p>Thư mục gốc: image/worlds/selene/moonfall/. Điền đường dẫn tương đối; file chưa có vẫn lưu được và UI dùng cảnh CSS/SVG dự phòng. Không đặt dữ liệu riêng tư trong thư mục public này.</p><p>Nhạc nền lấy từ kho chat thường; không cần chuẩn bị bản sao BGM tại đây.</p>
 {cfg.assets.filter(a=>a.audio_category!=="BGM").map(a=><details key={a.id}><summary>{a.type} · {a.id} · {a.path}</summary><label>Đường dẫn file<input value={a.path} onChange={e=>patch(c=>{c.assets.find(x=>x.id===a.id)!.path=e.target.value;})}/></label>
 <div className="mfCmsGrid"><label>Thời lượng (giây)<input type="number" min="0" max="120" step=".1" value={a.duration} onChange={e=>patch(c=>{c.assets.find(x=>x.id===a.id)!.duration=Number(e.target.value);})}/></label>
 <label>Fallback<select value={a.fallback} onChange={e=>patch(c=>{c.assets.find(x=>x.id===a.id)!.fallback=e.target.value;})}><option value="">CSS / tắt âm thanh nếu thiếu</option>{cfg.assets.filter(x=>x.id!==a.id).map(x=><option key={x.id} value={x.id}>{x.id}</option>)}</select></label></div>
 <label><input type="checkbox" checked={a.loop} onChange={e=>patch(c=>{c.assets.find(x=>x.id===a.id)!.loop=e.target.checked;})}/>Loop</label>
 <JsonEditor label="Thông tin nguồn và giấy phép" value={a.license_metadata} onChange={v=>patch(c=>{c.assets.find(x=>x.id===a.id)!.license_metadata=v;})} invalid={flag=>bad(a.id,flag)}/></details>)}</>:tab==="events"?<section><h2>Visual event registry</h2><p>Không dùng video cho mỗi lượt chat. Duration intro 5–8 giây; reduced motion dùng cảnh tĩnh.</p>{Object.entries(cfg.visual_events).map(([name,event])=><details key={name}><summary>{name}</summary><label>Cinematic video<select value={event.cinematic||""} onChange={e=>patch(c=>{c.visual_events[name].cinematic=e.target.value;})}><option value="">Không dùng video</option>{cfg.assets.filter(a=>a.type==="VIDEO").map(a=><option key={a.id} value={a.id}>{a.id}</option>)}</select></label><label>Hiệu ứng realtime<select value={event.vfx} onChange={e=>patch(c=>{c.visual_events[name].vfx=e.target.value;})}><option value="">Tự chọn theo sự kiện</option><option value="none">Tắt VFX</option>{[...WORLD_EFFECTS,"rune","pulse","fade","reconstruct"].map(v=><option key={v} value={v}>{v}</option>)}</select></label><JsonEditor label={name} value={event} onChange={v=>patch(c=>{c.visual_events[name]=v;})} invalid={flag=>bad(name,flag)}/></details>)}</section>:<section><h2>Cấu hình đầy đủ có kiểm tra schema</h2><JsonEditor label="Story configuration" value={cfg} onChange={v=>{setCfg(v);setDirty(true);setSaved(false);}} invalid={flag=>bad("full",flag)}/></section>}
 </div><footer className="mfCmsSave"><span>Phiên bản {cfg.revision} {dirty?"· Có thay đổi chưa lưu":""}</span><button disabled={busy||Object.values(badJson).some(Boolean)} onClick={()=>void save()}>{busy?"Đang lưu…":"Lưu cấu hình World"}</button></footer>
 </>}
 </main>;
}
