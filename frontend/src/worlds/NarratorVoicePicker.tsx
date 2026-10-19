import {readWorldJson} from "./worldHttp";
import {useEffect,useState} from "react";
type Voice={id:string;name:string;language:string;gender:string};
type Catalog={model:string;voices:Voice[]};
export default function NarratorVoicePicker({modelId,value,onChange}:{modelId:string;value:{vi:string;en:string};onChange:(language:"vi"|"en",id:string)=>void}){
 const [voices,setVoices]=useState<Voice[]>([]),[loading,setLoading]=useState(false),[error,setError]=useState(""),[attempt,setAttempt]=useState(0);
 useEffect(()=>{
  const abort=new AbortController();setLoading(true);setError("");setVoices([]);
  void fetch("/v1/admin/moonfall/voices?model_id="+encodeURIComponent(modelId),{credentials:"same-origin",signal:abort.signal})
   .then(async response=>{const data=await readWorldJson(response);if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"Không tải được danh sách giọng.");return data as Catalog;})
   .then(data=>{if(!abort.signal.aborted)setVoices(data.voices);})
   .catch(e=>{if(!abort.signal.aborted)setError(e instanceof Error?e.message:String(e));})
   .finally(()=>{if(!abort.signal.aborted)setLoading(false);});
  return()=>abort.abort();
 },[modelId,attempt]);
 return <fieldset className="mfNarratorVoices"><legend>Giọng người dẫn chuyện từ API</legend>
 {(["vi","en"] as const).map(language=>{
  const options=voices;
  const current=voices.find(v=>v.id===value[language]);
  return <label key={language}>Giọng người kể · {language.toUpperCase()}<select aria-label={"Giọng người kể "+language.toUpperCase()} value={value[language]} disabled={loading} onChange={e=>onChange(language,e.target.value)}>
   <option value="">Chưa chọn — chỉ hiển thị lời kể</option>
   {value[language]&&!options.some(v=>v.id===value[language])&&<option value={value[language]}>Đang gán: {current?.name||value[language]} · kiểm tra lại với provider</option>}
   {options.map(v=><option key={v.id} value={v.id}>{v.name} · {v.language||"Không ghi ngôn ngữ"} · {v.gender==="male"?"Nam":v.gender==="female"?"Nữ":v.gender||"Khác"} · {v.id}</option>)}
  </select><small>{loading?"Đang lấy giọng từ API…":options.length?options.length+" giọng từ API — hiển thị toàn bộ, không lọc ngôn ngữ.": "API chưa trả danh sách giọng; không tự đổi giọng đang lưu."}</small></label>;
 })}
 <button type="button" disabled={loading} onClick={()=>setAttempt(v=>v+1)}>Tải lại danh sách giọng</button>
 {error&&<p role="alert">{error}</p>}
 <small>Danh sách lấy từ provider TTS người kể đã chọn ở trên. API key chỉ dùng ở backend. Giọng Selene vẫn quản lý tại CMS nhân vật.</small>
 </fieldset>;
}
