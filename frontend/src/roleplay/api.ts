import { localizedError, storedLanguage, translateUiText } from "../i18n";

export const API = import.meta.env.VITE_API_URL || "";
const userId = localStorage.getItem("demo_user_id") || crypto.randomUUID();
localStorage.setItem("demo_user_id", userId);
export const authHeaders = (): Record<string, string> => {
  const token = localStorage.getItem("auth_token");
  return token
    ? { Authorization: `Bearer ${token}` }
    : { "X-Demo-User-Id": userId };
};
export async function responseError(response: Response): Promise<string> {
  const text = await response.text();
  // Only expose known configuration errors; provider failures remain sanitized.
  try {
    const detail = JSON.parse(text).detail;
    if(detail&&typeof detail==="object"&&typeof detail.code==="string"&&detail.code.startsWith("character_policy_")) {
      const labels:Record<string,string>={
        politics:"Không thể tạo nhân vật liên quan đến chính trị.",
        religion:"Không thể tạo nhân vật liên quan đến tôn giáo.",
        sexual:"Không thể tạo nhân vật có nội dung tình dục hoặc khiêu dâm.",
        minor_sexual:"Không cho phép nội dung tình dục liên quan người dưới 18 tuổi.",
        harmful:"Nội dung nhân vật không được phép.",
      };
      if(detail.code==="character_policy_blocked") {
        const categories=Array.isArray(detail.categories)?detail.categories:[];
        return (categories.length?categories:["harmful"]).map((code:string)=>translateUiText(labels[code]||labels.harmful,storedLanguage())).join(" ");
      }
      return translateUiText(detail.code==="character_policy_too_large"?"Thông tin nhân vật quá dài để kiểm duyệt.":"Không thể kiểm duyệt nhân vật lúc này. Vui lòng thử lại.",storedLanguage());
    }
    if (typeof detail === "string") {
      const missingVoice = /^No suitable voice configured for (vi|en)$/.exec(detail);
      if (missingVoice) return storedLanguage() === "vi"
        ? "Chưa có giọng phù hợp cho " + (missingVoice[1] === "vi" ? "tiếng Việt" : "tiếng Anh") + ". Hãy cấu hình giọng trong CMS."
        : "No matching " + (missingVoice[1] === "vi" ? "Vietnamese" : "English") + " voice is configured. Configure the voice in CMS.";
      if (detail === "TTS model is not assigned" || /^Hãy phân công model TTS trong CMS trước\.?$/.test(detail) || detail === "Chưa phân công model TTS trong CMS")
        return storedLanguage() === "vi" ? "Chưa phân công model TTS trong CMS." : "No TTS model is assigned. Configure it in CMS.";
      if (detail === "TTS model has no API key")
        return storedLanguage() === "vi" ? "Model TTS chưa có khóa API trong CMS." : "The TTS model has no API key configured in CMS.";
    }
  } catch { /* Preserve generic handling for unrecognized response bodies. */ }
  if (storedLanguage() !== "vi") return localizedError(response.status);
  try {
    const payload = JSON.parse(text);
    const detail = payload.detail || payload.error?.message;
    if (Array.isArray(detail))
      return detail
        .map((item: unknown) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object") {
            const value = item as { loc?: unknown[]; msg?: string };
            return `${value.loc?.slice(1).join(" → ") || "Dữ liệu"}: ${value.msg || "không hợp lệ"}`;
          }
          return String(item);
        })
        .join("; ");
    if (detail && typeof detail === "object") return JSON.stringify(detail);
    return String(detail || response.statusText || "Yêu cầu không hợp lệ");
  } catch {
    if (/modal-http|internal server error|runner terminated/i.test(text)) {
      return "Dịch vụ vừa được khởi động lại. Vui lòng gửi lại tin nhắn.";
    }
    return (
      text.trim().slice(0, 500) ||
      response.statusText ||
      "Không thể kết nối tới máy chủ."
    );
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch(API + path, {
    method,
    headers: {
      ...authHeaders(),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: path === "/v1/auth/me" && method === "GET" ? AbortSignal.timeout(15000) : undefined,
  });
  if (!r.ok) throw Object.assign(new Error(await responseError(r)), { status: r.status });
  const contentType = r.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error("Máy chủ trả về dữ liệu không hợp lệ. Vui lòng thử lại.");
  }
  if(method!=="GET" && path.startsWith("/v1/memories/"))window.dispatchEvent(new Event("roleplay-memories-changed"));
  return r.json();
}
