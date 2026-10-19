import {readWorldJson} from "./worldHttp";
import ChapterAudioAdmin from "./ChapterAudioAdmin";
import {useEffect,useState} from "react";
import {UI_LANGUAGES} from "../i18n";
import NarratorVoicePicker from "./NarratorVoicePicker";
import HubNarrationAdmin from "./HubNarrationAdmin";
type Data=Record<string,any>;
function Editor({label,value,onApply}:{label:string;value:any;onApply:(v:any)=>void}){
 const source=JSON.stringify(value,null,2),[draft,setDraft]=useState(source),[bad,setBad]=useState("");
 useEffect(()=>{setDraft(source);setBad("");},[source]);
 return <label className="mfCmsJson">{label}<textarea rows={14} value={draft} spellCheck={false} onChange={e=>{setDraft(e.target.value);setBad("Chưa áp dụng bản nháp này.");}}/><button type="button" onClick={()=>{try{onApply(JSON.parse(draft));setBad("");}catch{setBad("JSON không hợp lệ.");}}}>Áp dụng bản nháp JSON</button>{bad&&<small role="status">{bad}</small>}</label>;
}
async function request(path:string,method="GET",value?:unknown){
 const token=localStorage.getItem("auth_token");
 const r=await fetch(path,{method,credentials:"same-origin",headers:{"Content-Type":"application/json",...(token&&path.includes("/debug/")?{Authorization:"Bearer "+token}:{})},body:value===undefined?undefined:JSON.stringify(value)});
 const result=await readWorldJson(r);if(!r.ok)throw Error(typeof result.detail==="string"?result.detail:JSON.stringify(result.detail));return result;
}
export default function AdventureAdmin({initial}:{initial:Data}){
 const [data,setData]=useState(initial),[cfg,setCfg]=useState<Data>(structuredClone(initial.config)),[tab,setTab]=useState("world"),[locale,setLocale]=useState("vi"),[index,setIndex]=useState(0);
 const [error,setError]=useState(""),[status,setStatus]=useState(""),[busy,setBusy]=useState(false),[dirty,setDirty]=useState(false),[diagnostic,setDiagnostic]=useState<any>(null),[runId,setRunId]=useState("");
 const patch=(fn:(v:Data)=>void)=>{setCfg(old=>{const next=structuredClone(old);fn(next);return next;});setDirty(true);setStatus("");};
 useEffect(()=>{const warn=(e:BeforeUnloadEvent)=>{if(dirty){e.preventDefault();e.returnValue="";}};window.addEventListener("beforeunload",warn);return()=>window.removeEventListener("beforeunload",warn);},[dirty]);
 async function work(fn:()=>Promise<void>){setBusy(true);setError("");try{await fn();}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 function text(label:string,value:Data,apply:(v:Data)=>void){return <label>{label} · {locale.toUpperCase()}<textarea rows={3} value={value?.[locale]||""} onChange={e=>{const next={...value};if(!e.target.value&&!["vi","en"].includes(locale))delete next[locale];else next[locale]=e.target.value;apply(next);}}/></label>;}
 const ch=cfg.chapters[index];
 return <main className="mfCms" data-no-translate="true"><header><div><small>WORLD STUDIO · MEMORY ADVENTURE V2</small><h1>Echoes of Moonfall · 8 chương</h1></div><nav><a href="/admin">CMS chính</a><a href="/worlds">Mở bản đồ</a></nav></header>
 <p>Chỉnh nội dung World riêng. Giọng Selene vẫn lấy từ card nhân vật trong CMS chat thường. Lưu cấu hình áp dụng cho lượt chơi mới; save đang chơi giữ phiên bản của nó.</p>
 {error&&<p role="alert" className="mfCmsError">{error}</p>}{status&&<p role="status">{status}</p>}
 <div className="mfCmsToolbar"><nav>{[["world","World & giọng đọc"],["chapters","8 chương"],["assets","Manifest asset"],["prompts","Prompt & kết truyện"],["debug","Kiểm tra & debugger"]].map(([id,label])=><button key={id} aria-pressed={tab===id} onClick={()=>setTab(id)}>{label}</button>)}</nav><label>Ngôn ngữ<select value={locale} onChange={e=>setLocale(e.target.value)}>{UI_LANGUAGES.map(l=><option key={l.code} value={l.code}>{l.label}</option>)}</select></label></div>
 <div className="mfCmsBody">
 {tab==="world"&&<><section><h2>World</h2><label><input type="checkbox" checked={cfg.enabled} onChange={e=>patch(v=>{v.enabled=e.target.checked;})}/>Bật World</label>{text("Tên",cfg.title,v=>patch(c=>{c.title=v;}))}{text("Giới thiệu",cfg.pitch,v=>patch(c=>{c.pitch=v;}))}
 <label>Nhân vật nguồn<select value={cfg.character_source_id} onChange={e=>patch(c=>{c.character_source_id=e.target.value;})}><option value="">Tự nhận diện Selene Moonbrook</option>{data.characters.map((a:Data)=><option key={a.id} value={a.id}>{a.name}</option>)}</select></label>
 <label>Model hội thoại<select value={cfg.model_id} onChange={e=>patch(c=>{c.model_id=e.target.value;})}><option value="">Model Roleplay đã gán</option>{data.models.map((m:Data)=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
 <label>Chỉ dẫn World<textarea rows={5} value={cfg.instruction} onChange={e=>patch(c=>{c.instruction=e.target.value;})}/></label>
 <Editor label="Điều kiện mở World" value={cfg.entry_gate} onApply={v=>patch(c=>{c.entry_gate=v;})}/>
<Editor label="Nhịp mở chương linh hoạt" value={cfg.adventure.pacing} onApply={v=>patch(c=>{c.adventure.pacing=v;})}/><p>Mỗi chương có ngưỡng khác nhau. Chỉ tính lượt chat riêng với Selene đã có câu trả lời sau khi kết thúc chương trước. Chủ đề liên quan và tăng tin tưởng giúp ký ức xuất hiện sớm hơn.</p>
<Editor label="Cảnh nối, tiếng vọng và lời kết chương" value={cfg.adventure.story_beats} onApply={v=>patch(c=>{c.adventure.story_beats=v;})}/><label><input type="checkbox" checked={cfg.adventure.enrichment_enabled!==false} onChange={e=>patch(c=>{c.adventure.enrichment_enabled=e.target.checked;})}/>Bật các cảnh tiếng vọng bổ sung</label>
 <Editor label="Chương 1 · mở cổng và cuộn giấy" value={cfg.adventure.chapter_one_flow} onApply={v=>patch(c=>{c.adventure.chapter_one_flow=v;})}/>
 <Editor label="Gợi ý" value={cfg.hints} onApply={v=>patch(c=>{c.hints=v;})}/></section>
 <section><h2>Giọng kể & nhạc dùng chung</h2><label>Provider TTS<select value={cfg.tts_model_id} onChange={e=>patch(c=>{c.tts_model_id=e.target.value;})}><option value="">Provider đang có</option>{data.models.filter((m:Data)=>m.tts).map((m:Data)=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
 <NarratorVoicePicker modelId={cfg.tts_model_id} value={cfg.narrator_voices} onChange={(language,id)=>patch(c=>{c.narrator_voices[language]=id;})}/><ChapterAudioAdmin chapterId={ch.id} dirty={dirty}/>{[["young_selene","Selene trong ký ức"],["elarion","Elarion"],["unknown_girl","Cô gái trong ký ức"]].map(([id,name])=><div key={id}><h4>Giọng nhân vật phụ · {name}</h4><NarratorVoicePicker modelId={cfg.tts_model_id} value={cfg.adventure.speaker_voices?.[id]||{vi:"",en:""}} onChange={(language,voice)=>patch(c=>{c.adventure.speaker_voices??={};c.adventure.speaker_voices[id]??={vi:"",en:""};c.adventure.speaker_voices[id][language]=voice;})}/></div>)}
<h3>Âm lượng World mặc định</h3>{[["master","Âm lượng chung"],["music","Nhạc nền"],["ambient","Âm thanh môi trường"],["effects","Hiệu ứng"],["narrator","Giọng dẫn"],["character","Giọng nhân vật"],["duck_gain","Nhạc còn lại khi có giọng đọc"]].map(([key,label])=><label key={key}>{label} · {Math.round((cfg.adventure.music_levels?.[key]??0)*100)}%<input type="range" min="0" max="100" value={Math.round((cfg.adventure.music_levels?.[key]??0)*100)} onChange={e=>patch(c=>{c.adventure.music_levels[key]=Number(e.target.value)/100;})}/></label>)}<p>Áp dụng cho người chưa chỉnh âm lượng riêng. Trong World, chọn “Dùng âm lượng từ CMS” để bỏ mức đã lưu trên trình duyệt. Intro có bộ trộn riêng.</p>
 <label>Nhạc nền<select value={cfg.bgm} onChange={e=>patch(c=>{c.bgm=e.target.value;})}><option value="">Nhạc theo chat thường</option>{data.music.map((m:Data)=><option key={m.id} value={m.id}>{m.title}</option>)}</select></label><p>Narration dùng giọng kể; dialogue dùng giọng nhân vật; thought không đọc. Hai giọng được phát lần lượt.</p></section><HubNarrationAdmin locale={locale}/></>}
 {tab==="chapters"&&<><nav className="mfCmsChapters">{cfg.chapters.map((c:Data,i:number)=><button key={c.id} aria-pressed={i===index} onClick={()=>setIndex(i)}>{c.order}. {c.title[locale]||c.title.en}</button>)}</nav><section><h2>{ch.id}</h2><ChapterAudioAdmin chapterId={ch.id} dirty={dirty}/>
 {text("Tên chương",ch.title,v=>patch(c=>{c.chapters[index].title=v;}))}{text("Mục tiêu",ch.objective,v=>patch(c=>{c.chapters[index].objective=v;}))}
 <label><input type="checkbox" checked={ch.enabled} onChange={e=>patch(c=>{c.chapters[index].enabled=e.target.checked;})}/>Cho phép chương</label>
 <p>Scenes: background là ID manifest; hotspot x/y/width/height trong khoảng 0–1; scene_asset là ảnh đặt trên BG (khác item là vật phẩm nhận được), presentation_mode: floor/floor_flat/table/wall/light/detail; effect_profile 1–8 chọn công thức hiệu ứng. Puzzle giữ solution ở backend, không gửi xuống người chơi.</p>
 <Editor label="Scenes & hotspot" value={ch.scenes} onApply={v=>patch(c=>{c.chapters[index].scenes=v;})}/>
 <Editor label="Puzzle & 3 mức gợi ý" value={ch.puzzles} onApply={v=>patch(c=>{c.chapters[index].puzzles=v;})}/>
 <Editor label="Lựa chọn & hệ quả" value={ch.choice} onApply={v=>patch(c=>{c.chapters[index].choice=v;})}/>
 <Editor label="Memory" value={ch.memory} onApply={v=>patch(c=>{c.chapters[index].memory=v;})}/>
 <details><summary>Toàn bộ cấu hình chương</summary><Editor label="Chapter JSON" value={ch} onApply={v=>patch(c=>{c.chapters[index]=v;})}/></details></section>
 <section><h2>Lời dẫn, thoại, suy nghĩ và bản dịch</h2>{Object.entries(ch.localization).map(([key,value])=><div key={key}>{text(key,value as Data,v=>patch(c=>{c.chapters[index].localization[key]=v;}))}</div>)}</section></>}
 {tab==="assets"&&<section><h2>Manifest</h2><p>Đường dẫn tính từ image/worlds/selene/moonfall. Giữ ID để không đứt liên kết. Video không quyết định tiến trình truyện.</p><Editor label="Asset manifest" value={cfg.assets} onApply={v=>patch(c=>{c.assets=v;})}/><Editor label="Story event → VFX" value={cfg.visual_events} onApply={v=>patch(c=>{c.visual_events=v;})}/></section>}
 {tab==="prompts"&&<section><h2>Prompt có phiên bản & kết truyện</h2><p>Reflection, lời trở về chat và chronicle chỉ nhận dữ kiện đã mở. Điều kiện kết ẩn chỉ admin thấy.</p><Editor label="Prompt templates" value={cfg.adventure.prompts} onApply={v=>patch(c=>{c.adventure.prompts=v;})}/><Editor label="Bốn kết truyện" value={cfg.adventure.endings} onApply={v=>patch(c=>{c.adventure.endings=v;})}/><Editor label="Điều kiện kết ẩn" value={cfg.adventure.hidden_ending} onApply={v=>patch(c=>{c.adventure.hidden_ending=v;})}/></section>}
 {tab==="debug"&&<section><h2>Kiểm tra & preview riêng</h2><button disabled={busy} onClick={()=>void work(async()=>{setDiagnostic(await request("/v1/admin/moonfall/validation"));})}>Kiểm tra cấu hình đã lưu</button><label>Run ID của tài khoản đang đăng nhập<input value={runId} onChange={e=>setRunId(e.target.value)}/></label>
 <button disabled={busy||!runId} onClick={()=>void work(async()=>{setDiagnostic(await request("/v1/admin/moonfall/debug/"+encodeURIComponent(runId)));})}>Đọc trạng thái</button>
 <label>Nhảy chương trong preview<select value={index} onChange={e=>setIndex(Number(e.target.value))}>{cfg.chapters.map((c:Data,i:number)=><option key={c.id} value={i}>{c.order}. {c.title.vi}</option>)}</select></label>
 <button disabled={busy||!runId} onClick={()=>void work(async()=>{const preview=await request("/v1/admin/moonfall/debug/"+encodeURIComponent(runId),"POST",{chapter_id:cfg.chapters[index].id});setDiagnostic(preview);})}>Tạo preview riêng tại chương này</button>
 {diagnostic?.admin_preview&&diagnostic?.id&&<a href={"/worlds?character="+encodeURIComponent(diagnostic.character.id)+"&run="+encodeURIComponent(diagnostic.id)} target="_blank" rel="noopener noreferrer">Mở preview riêng</a>}<p>Preview không ghi vào lượt chơi thật và không được đồng bộ ký ức sang chat thường. Cần đăng nhập cùng tài khoản chủ save.</p><pre style={{maxHeight:600,overflow:"auto",whiteSpace:"pre-wrap"}}>{diagnostic?JSON.stringify(diagnostic,null,2):""}</pre></section>}
 </div><footer><button disabled={busy||!dirty} onClick={()=>void work(async()=>{const next=await request("/v1/admin/moonfall","PUT",cfg);setCfg(next);setDirty(false);setStatus("Đã lưu phiên bản "+next.revision);})}>{busy?"Đang xử lý…":"Lưu cấu hình World"}</button><button disabled={busy} onClick={()=>void work(async()=>{const next=await request("/v1/admin/moonfall");setData(next);setCfg(next.config);setDirty(false);})}>Tải lại bản đã lưu</button></footer></main>;
}
