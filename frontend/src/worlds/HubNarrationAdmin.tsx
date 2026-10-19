import {readWorldJson} from "./worldHttp";
import {useEffect,useState} from "react";
import {UI_LANGUAGES} from "../i18n";
import type {IntroNarrationConfig} from "./IntroNarration";
import IntroAudioStatus from "./IntroAudioStatus";
export default function HubNarrationAdmin({locale}:{locale:string}){
 const [data,setData]=useState<IntroNarrationConfig|null>(null),[error,setError]=useState(""),[saved,setSaved]=useState(false),[busy,setBusy]=useState(false);
 async function request(method="GET",body?:IntroNarrationConfig){
  const response=await fetch("/v1/admin/moonfall/hub-narration",{method,credentials:"same-origin",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined});
  const value=await readWorldJson(response);if(!response.ok)throw Error(typeof value.detail==="string"?value.detail:"Không lưu được lời dẫn");
  return value as IntroNarrationConfig;
 }
 useEffect(()=>{let live=true;void request().then(c=>{if(live)setData(c);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[]);
 function patch(fn:(c:IntroNarrationConfig)=>void){setData(old=>{if(!old)return old;const next=structuredClone(old);fn(next);return next;});setSaved(false);}
 return <section><h2>Intro trang chủ · lời dẫn & phụ đề</h2>
 <p>Khác lời mở đầu Chương 1. Dùng chung provider và Voice ID người kể VI/EN đã chọn ở trên. Phụ đề có đủ 7 ngôn ngữ; không gọi AI dịch mỗi lượt xem. Thời gian tính từ đầu bản video đã cắt 17 giây. Các khoảng im lời dành riêng cho hình và nhạc.</p>
 {error&&<p role="alert">{error}</p>}{saved&&<p role="status">Đã lưu. Hệ thống đang chuẩn bị giọng VI/EN theo cấu hình đã lưu; quay lại World để nhận phiên bản mới.</p>}
 {data&&<><label><input type="checkbox" checked={data.enabled} onChange={e=>patch(c=>{c.enabled=e.target.checked;})}/>Bật lời dẫn và phụ đề intro</label>
 <div className="mfCmsGrid">{(["music_gain","duck_gain","voice_gain"] as const).map((key,i)=><label key={key}>{["Mức nhạc khi chưa đọc (0–1)","Mức nhạc khi đang đọc (0–1)","Mức giọng đọc (0–1)"][i]}<input type="number" min="0" max="1" step=".01" value={data[key]} onChange={e=>patch(c=>{c[key]=Number(e.target.value);})}/></label>)}</div>
 <p>Thanh âm lượng của user nhân đồng thời với cả ba mức trên. Audio TTS được tạo theo từng câu và cache trong DATA_DIR/world_intro_audio; đổi nội dung hoặc giọng sẽ tạo bản mới.</p>
 <button type="button" disabled={busy} onClick={()=>{setBusy(true);setError("");void fetch("/v1/admin/moonfall/hub-narration/prepare",{method:"POST",credentials:"same-origin"}).then(async r=>{if(!r.ok)throw Error("Không chuẩn bị được giọng đọc.");const value=await readWorldJson(r);if(!value.ready)throw Error("Một số câu chưa tạo được. Kiểm tra provider và giọng VI/EN rồi thử lại.");setSaved(true);}).catch(e=>setError(e.message)).finally(()=>setBusy(false));}}>Tạo sẵn giọng intro VI/EN</button>
 <small>Lưu nội dung và giọng sẽ tự chuẩn bị audio ở nền. Nút này dùng để thử lại khi provider lỗi. Các lần xem sau chỉ lấy audio đã tạo.</small>
 {data.duration_seconds&&<label>Thời lượng clip (giây)<input type="number" min="1" step=".001" value={data.duration_seconds} onChange={e=>patch(c=>{c.duration_seconds=Number(e.target.value);})}/></label>}
 {data.silent_windows?.map((window,i)=><fieldset key={window.id}><legend>Im lời · {window.label}</legend><label>Bắt đầu im lời (giây)<input type="number" min="0" step=".1" value={window.start} onChange={e=>patch(c=>{c.silent_windows![i].start=Number(e.target.value);})}/></label><label>Kết thúc im lời (giây)<input type="number" min="0" step=".1" value={window.end} onChange={e=>patch(c=>{c.silent_windows![i].end=Number(e.target.value);})}/></label></fieldset>)}
 <IntroAudioStatus config={data}/>
 {data.cues.map((cue,i)=><fieldset key={cue.id}><legend>Đoạn {i+1} · {cue.id}</legend><div className="mfCmsGrid"><label>Bắt đầu (giây)<input type="number" min="0" step=".1" value={cue.start} onChange={e=>patch(c=>{c.cues[i].start=Number(e.target.value);})}/></label><label>Kết thúc (giây)<input type="number" min="0" step=".1" value={cue.end} onChange={e=>patch(c=>{c.cues[i].end=Number(e.target.value);})}/></label></div><label>Phụ đề · {UI_LANGUAGES.find(l=>l.code===locale)?.label||locale}<textarea rows={3} value={cue.text[locale]||""} onChange={e=>patch(c=>{c.cues[i].text[locale]=e.target.value;})}/></label></fieldset>)}
 <button type="button" disabled={busy} onClick={()=>{setBusy(true);setError("");void request("PUT",data).then(c=>{setData(c);setSaved(true);}).catch(e=>setError(e.message)).finally(()=>setBusy(false));}}>Lưu lời dẫn intro chung</button></>}
 </section>;
}
