import {useEffect,useState} from "react";
import {readWorldJson} from "./worldHttp";
import {introAudioDuration,introVoiceRate} from "./introTiming";
import type {IntroNarrationConfig} from "./IntroNarration";
type Row={language:string;cue:string;ready:boolean;status?:number};
export default function IntroAudioStatus({config}:{config:IntroNarrationConfig}){
 const [rows,setRows]=useState<string[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState("");
 async function check(){
  setBusy(true);setError("");setRows([]);
  try{
   const response=await fetch("/v1/admin/moonfall/hub-narration/status",{credentials:"same-origin",cache:"no-store"});
   if(!response.ok)throw Error("Không lấy được trạng thái audio intro.");
   const state=await readWorldJson(response) as {results:Row[]};
   const result:string[]=[];
   for(const row of state.results){
    const name=row.language.toUpperCase()+" · "+row.cue;
    if(!row.ready){result.push(name+" · "+(row.status===503?"Thiếu cấu hình model/giọng TTS":"Chưa tạo audio"));continue;}
    const cue=config.cues.find(c=>c.id===row.cue);
    if(!cue){result.push(name+" · Nội dung đã đổi, hãy kiểm tra lại");continue;}
    const audio=await fetch("/v1/admin/moonfall/hub-narration/audio/"+encodeURIComponent(row.cue)+"?language="+row.language,{credentials:"same-origin",cache:"no-store"});
    if(!audio.ok){result.push(name+" · Không tải được audio");continue;}
    try{const duration=await introAudioDuration(await audio.blob());introVoiceRate(duration,cue);result.push(name+" · Sẵn sàng, "+duration.toFixed(1)+" giây / khung "+(cue.end-cue.start).toFixed(1)+" giây");}
    catch{result.push(name+" · Audio không khớp thời lượng hoặc chưa giải mã được; cần sửa trước khi phát");}
   }
   setRows(result);
  }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
 }
 useEffect(()=>{setRows([]);},[config.revision]);
 return <section><h3>Kiểm tra giọng đọc và thời lượng</h3><p>Chỉ kiểm tra file đã tạo, không gọi TTS. Giới hạn tăng tốc 1,25 lần để giữ các khoảng im lời.</p><button disabled={busy} onClick={()=>void check()}>{busy?"Đang kiểm tra…":"Kiểm tra audio intro đã tạo"}</button>{error&&<p role="alert">{error}</p>}{rows.map(row=><p key={row}>{row}</p>)}</section>;
}
