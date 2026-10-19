import {WorldEntry} from "../../worlds/entry";
import {storedLanguage,translateUiText} from "../../i18n";
import "./experiences.css";

/** Activities change the interaction model; chat intelligence stays in chat. */
export function ExperiencesView({tabs,onChat}:{tabs:React.ReactNode;onChat:()=>void}){
 const language=storedLanguage(),t=(a:string,b:string)=>language==="vi"?a:(translateUiText(a,language)||b);
 return <section className="rpExperiences">
  {tabs}
  <h2>{t("Chọn cách trải nghiệm","Choose your experience")}</h2>
  <div className="rpExperienceGrid">
   <article><span aria-hidden="true">✧</span><h3>{t("Phiêu lưu trong thế giới","World adventures")}</h3><p>{t("Chọn bạn đồng hành từ kho nhân vật, gặp gỡ, chọn thẻ hành động và tìm manh mối. Tiến trình phiêu lưu được lưu riêng.","Choose companions from your character library, meet characters, play action cards and uncover clues. Adventure progress is saved separately.")}</p><WorldEntry/></article>
   <article><span aria-hidden="true">☏</span><h3>{t("Trò chuyện cùng nhân vật","Chat with characters")}</h3><p>{t("Chỉ cần chọn nhân vật rồi nhắn tin. Ký ức, cảm xúc, ngữ cảnh và gợi ý hỗ trợ ngay trong cuộc trò chuyện.","Choose a character and start messaging. Memory, emotions, context and suggestions support the conversation.")}</p><button className="btn" onClick={onChat}>{t("Chọn nhân vật","Choose a character")}</button></article>
  </div>
 </section>;
}
