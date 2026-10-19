import {readWorldJson} from "./worldHttp";
import {useEffect,useState} from "react";
async function request(path:string,value?:unknown){
 const response=await fetch(path,{method:value===undefined?"GET":"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:value===undefined?undefined:JSON.stringify(value)});
 const result=await readWorldJson(response);if(!response.ok)throw Error(typeof result.detail==="string"?result.detail:"Không kiểm tra được audio");return result;
}
export default function ChapterAudioAdmin({chapterId,dirty}:{chapterId:string;dirty:boolean}){
 const [status,setStatus]=useState<any>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 const load=()=>request("/v1/admin/moonfall/chapter-audio?chapter_id="+encodeURIComponent(chapterId)).then(setStatus).catch(e=>setError(String(e.message)));
 useEffect(()=>{setStatus(null);setError("");void load();},[chapterId]);
 useEffect(()=>{if(!status?.running)return;const timer=setInterval(()=>void load(),2500);return()=>clearInterval(timer);},[status?.running,chapterId]);
 async function prepare(all=false){
  setBusy(true);setError("");
  try{await request("/v1/admin/moonfall/chapter-audio/prepare",all?{}:{chapters:[chapterId]});await load();}
  catch(e){setError(e instanceof Error?e.message:String(e));}
  finally{setBusy(false);}
 }
 return <section className="mfChapterAudioAdmin"><h3>Giọng đọc cố định · {chapterId}</h3>
 <p>Giọng dẫn dùng provider và lựa chọn VI/EN ở trên. Giọng Selene dùng cấu hình nhân vật trong <a href="/admin">CMS chat thường</a>, không tạo giọng riêng cho World.</p>
 <p>Lưu World sẽ tự chuẩn bị audio VI/EN. Sau khi đổi giọng Selene ở CMS chat, bấm tạo lại ở đây. Chỉ câu thay đổi lời/giọng/provider mới gọi TTS lại; audio đã có được giữ trên volume.</p>
 {status?.languages&&Object.entries(status.languages).map(([language,row]:[string,any])=><div key={language}><p><strong>{language.toUpperCase()}</strong> · {row.enabled?row.ready+" / "+row.total+" đoạn đã sẵn sàng":"Chưa đủ cấu hình TTS/giọng; kiểm tra provider và giọng kể khác giọng Selene."}</p>{!!row.missing?.length&&<details><summary>Các câu chưa có audio</summary>{row.missing.map((line:{id:string;speaker:string;text:string})=><p key={line.id}><strong>{line.speaker}</strong> · {line.text}</p>)}</details>}</div>)}
 {status?.running&&<p role="status">Đang chuẩn bị giọng đọc ở nền…</p>}
 {!!status?.failures&&<p role="alert">{status.failures} đoạn chưa chuẩn bị được. Kiểm tra provider/giọng rồi bấm thử lại.</p>}
 {error&&<p role="alert">{error}</p>}
 <button disabled={busy||dirty||status?.running} onClick={()=>void prepare()}>Chuẩn bị VI/EN chương này</button>
 <button disabled={busy||dirty||status?.running} onClick={()=>void prepare(true)}>Chuẩn bị VI/EN cả 8 chương</button>
 <button disabled={busy} onClick={()=>void load()}>Cập nhật trạng thái audio</button>
 {dirty&&<p>Lưu cấu hình World trước khi chuẩn bị audio.</p>}
 </section>;
}
