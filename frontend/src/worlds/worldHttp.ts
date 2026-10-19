/** Proxies can return plaintext/HTML even with HTTP 200. Never parse it blindly. */
export class WorldError extends Error{
 status:number;
 constructor(status:number,message:string){super(message);this.name="WorldError";this.status=status;}
}
function unavailable(){
 const messages:Record<string,string>={
 vi:"Dịch vụ tạm thời chưa phản hồi đúng. Vui lòng thử lại sau ít giây.",
 en:"The service is temporarily unavailable. Please try again in a few seconds.",
 ja:"一時的にサービスに接続できません。少し待ってから、もう一度お試しください。",
 zh:"服务暂时无法正常响应，请稍等几秒后重试。",
 ko:"서비스가 잠시 응답하지 않습니다. 잠시 후 다시 시도해 주세요.",
 my:"ဝန်ဆောင်မှု ခေတ္တမရနိုင်သေးပါ။ ခဏစောင့်ပြီး ပြန်စမ်းကြည့်ပါ။",
 km:"សេវាកម្មមិនទាន់អាចឆ្លើយតបបានទេ។ សូមរង់ចាំបន្តិច រួចព្យាយាមម្តងទៀត។"
 };
 try{return messages[localStorage.getItem("ui_language")||"vi"]||messages.en;}catch{return messages.en;}
}
export async function readWorldJson<T=any>(response:Response):Promise<T>{
 let value:any;
 try{value=JSON.parse(await response.text());}
 catch{throw new WorldError(response.ok?503:response.status,unavailable());}
 if(!response.ok)throw new WorldError(response.status,typeof value?.detail==="string"?value.detail:unavailable());
 // A JSON string/null is not an API document (e.g. a proxy-encoded diagnostic).
 if(value===null||typeof value!=="object")throw new WorldError(503,unavailable());
 return value as T;
}
