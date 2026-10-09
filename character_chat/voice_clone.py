"""CMS-only voice upload; credentials stay in the backend."""
import httpx
from fastapi import HTTPException
from .voice import vbee_voice_url,normalize_voices

async def upload_voice(api_base,api_key,name,content,filename,mime_type,gender,language,ref_text="",enhance_audio=False):
    form={"name":name,"gender":gender,"language":language,"ref_text":ref_text,
          "enhance_audio":"true" if enhance_audio else "false","infer_ref_text_if_empty":"true"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180,connect=10),follow_redirects=False) as client:
            response=await client.post(vbee_voice_url(api_base),headers={"Authorization":"Bearer "+api_key},
                data=form,files={"audio":(filename,content,mime_type)})
            if response.status_code in (401,403):raise HTTPException(502,"API key clone giọng không được chấp nhận; kiểm tra key của model TTS trong CMS.")
            if response.status_code==409:raise HTTPException(409,"Tên giọng đã tồn tại. Hãy chọn tên khác.")
            if response.status_code>=400:raise HTTPException(502,f"Upload Voice thất bại (HTTP {response.status_code}).")
            try:result=response.json()
            except ValueError:raise HTTPException(502,"API Upload Voice không trả JSON hợp lệ.")
            candidates=[result]
            if isinstance(result,dict):
                candidates.extend(result.get(key) for key in ("voice","data","result"))
            voice_id=""
            for item in candidates:
                if isinstance(item,dict):
                    voice_id=str(item.get("voice_id") or item.get("id") or item.get("voice_code") or "").strip()
                    if voice_id:break
            if not voice_id:
                # The schema does not specify an upload response structure.
                # Resolve a returned name only through the authenticated catalog.
                catalog=await client.get(vbee_voice_url(api_base),headers={"Authorization":"Bearer "+api_key})
                if catalog.status_code==200:
                    matches=[voice for voice in normalize_voices(catalog.json()) if voice["name"]==name]
                    if len(matches)==1:voice_id=matches[0]["id"]
            if not voice_id or len(voice_id)>160:raise HTTPException(502,"API đã nhận mẫu nhưng chưa trả mã giọng hợp lệ. Hãy tải lại danh sách giọng trước khi upload lại.")
            return voice_id
    except httpx.TimeoutException:raise HTTPException(504,"Clone giọng chưa hoàn tất trong thời gian chờ. Kiểm tra danh sách giọng trước khi upload lại.")
    except httpx.RequestError:raise HTTPException(502,"Không kết nối được API clone giọng.")
