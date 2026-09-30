import base64
import os
import concurrent.futures
from pathlib import Path
from io import BytesIO

import httpx
from PIL import Image,ImageEnhance,ImageFilter,ImageOps

EMOTIONS=("neutral","happy","sad","angry","surprised","shy")
EXPRESSION_VERSION="2"
DEFAULT_ICON_FILES={"neutral":"neutral.png","happy":"happy.png","sad":"sad.png","angry":"angry.png","surprised":"surprised.png","shy":"shy.png"}

def optimize_card_avatar(content,max_side=720):
    """Create a compact, browser-friendly avatar for catalog/home cards."""
    image=ImageOps.exif_transpose(Image.open(BytesIO(content)))
    image.seek(0)
    image=image.convert("RGBA" if "A" in image.getbands() else "RGB")
    image.thumbnail((max_side,max_side),Image.Resampling.LANCZOS)
    out=BytesIO()
    image.save(out,"WEBP",quality=82,method=6)
    return out.getvalue(),"image/webp"

BASE_PROMPT=(
    "Create a new clean avatar portrait from the supplied character reference. Preserve the exact same "
    "character identity, facial features, hair, colors, clothing design and illustration style. Show one "
    "person only, front facing and looking directly at the viewer, symmetrical head-and-shoulders framing, "
    "centered face, transparent background. No scenery, circle, frame, border, text, logo, watermark, props "
    "or extra body parts. Neutral relaxed facial expression. Output a square transparent PNG."
)
EXPRESSION_PROMPTS={
    "happy":"Edit only the facial expression into a clear natural happy smile. Keep identity, pose, camera, hair, clothing, lighting, style and transparency exactly unchanged.",
    "sad":"Edit only the facial expression into visibly sad eyes and a subtle downturned mouth. Keep identity, pose, camera, hair, clothing, lighting, style and transparency exactly unchanged.",
    "angry":"Edit only the facial expression into clear restrained anger with furrowed brows and a tense mouth. Keep identity, pose, camera, hair, clothing, lighting, style and transparency exactly unchanged.",
    "surprised":"Edit only the facial expression into clear surprise with widened eyes and a slightly open mouth. Keep identity, pose, camera, hair, clothing, lighting, style and transparency exactly unchanged.",
    "shy":"Edit only the facial expression into a shy warm look with softened eyes, a small smile and slight blush. Keep identity, pose, camera, hair, clothing, lighting, style and transparency exactly unchanged.",
}

def _portrait(content):
    try:
        from rembg import remove,new_session
        content=remove(content,session=new_session("u2net_human_seg"),force_return_bytes=True)
    except Exception:pass
    image=Image.open(BytesIO(content)).convert("RGBA");bbox=image.getbbox()
    if bbox:image=image.crop(bbox)
    w,h=image.size;side=max(w,h);canvas=Image.new("RGBA",(side,side),(0,0,0,0))
    canvas.alpha_composite(image,((side-w)//2,max(0,int((side-h)*.35))))
    return canvas.resize((512,512),Image.Resampling.LANCZOS)

def _png(content):
    image=_portrait(content);out=BytesIO();image.save(out,"PNG",optimize=True);return out.getvalue()

def _icon_png(content):
    """Keep the circular icon itself and remove JPEG/checkerboard corners."""
    image=Image.open(BytesIO(content)).convert("RGBA")
    side=min(image.size);left=(image.width-side)//2;top=(image.height-side)//2
    image=image.crop((left,top,left+side,top+side)).resize((512,512),Image.Resampling.LANCZOS)
    mask=Image.new("L",image.size,0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).ellipse((5,5,507,507),fill=255)
    image.putalpha(mask);out=BytesIO();image.save(out,"PNG",optimize=True);return out.getvalue()

def default_expression_variants(directory=""):
    root=Path(directory or os.getenv("DEFAULT_EXPRESSION_ICON_DIR",Path(os.getenv("CHARACTER_IMAGE_DIR","image"))/"default_icons"))
    variants={}
    for emotion,filename in DEFAULT_ICON_FILES.items():
        path=root/filename
        if path.is_file():variants[emotion]=_icon_png(path.read_bytes())
    if len(variants)!=len(DEFAULT_ICON_FILES):
        missing=sorted(set(DEFAULT_ICON_FILES)-set(variants))
        raise FileNotFoundError("Missing default expression icons: "+", ".join(missing))
    return variants

def _result_bytes(response,http):
    response.raise_for_status();payload=response.json();item=(payload.get("data") or [payload])[0]
    encoded=item.get("b64_json") or item.get("b64")
    if encoded:return base64.b64decode(encoded)
    url=item.get("url") or item.get("image_url")
    if url:
        downloaded=http.get(url);downloaded.raise_for_status();return downloaded.content
    raise ValueError("Image API did not return image data")

def _edit(http,content,prompt,model,api_base,api_key):
    base=api_base.rstrip("/")
    headers={"Authorization":"Bearer "+api_key}
    if base.lower().startswith("https://openrouter.ai/api/v1"):
        reference="data:image/png;base64,"+base64.b64encode(_png(content)).decode("ascii")
        url=base+"/images"
        payload={"model":model,"prompt":prompt,"size":"1024x1024","quality":"low","background":"transparent","output_format":"png","input_references":[{"type":"image_url","image_url":{"url":reference}}]}
        request=lambda:http.post(url,headers=headers,json=payload)
    else:
        url=base+"/images/edits"
        request=lambda:http.post(url,headers=headers,data={"model":model,"prompt":prompt,"size":"1024x1024","quality":"low","background":"transparent","output_format":"png"},files={"image":("reference.png",_png(content),"image/png")})
    try:response=request()
    except httpx.RequestError as exc:raise RuntimeError(f"Không kết nối được API ảnh {url}: {exc}") from exc
    return _result_bytes(response,http)

def build_ai_expression_variants(content,model="",api_base="",api_key=""):
    """Generate once, then persist a consistent front-facing transparent expression set."""
    model=model or os.getenv("AVATAR_IMAGE_MODEL","openai/gpt-image-1-mini")
    api_base=api_base or os.getenv("AVATAR_IMAGE_API_BASE",os.getenv("LLM_API_BASE","https://gateway.avibi.ai/v1"))
    api_key=api_key or os.getenv("AIMP_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if not api_key:raise ValueError("Missing image generation API key")
    with httpx.Client(timeout=httpx.Timeout(180,connect=15,write=30,pool=10),follow_redirects=True) as http:
        neutral=_png(_edit(http,content,BASE_PROMPT,model,api_base,api_key));variants={"neutral":neutral}
        def render(item):
            emotion,prompt=item
            # Reuse the original reference for every variant. Editing an
            # already transparent generated portrait can make image APIs erase
            # the whole character and retain only eyes/mouth alpha fragments.
            full_prompt=BASE_PROMPT.replace("Neutral relaxed facial expression.","")+" "+prompt
            return emotion,_png(_edit(http,content,full_prompt,model,api_base,api_key))
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            for emotion,image in pool.map(render,EXPRESSION_PROMPTS.items()):variants[emotion]=image
        return variants

def build_expression_variants(content):
    """Local fallback used only when the configured image editor is unavailable."""
    base=_portrait(content);variants={}
    settings={"neutral":(1.,1.,0),"happy":(1.08,1.08,-2),"sad":(.82,.92,2),"angry":(1.12,.9,0),"surprised":(1.05,1.02,-4),"shy":(.96,1.05,2)}
    for emotion,(color,brightness,shift) in settings.items():
        image=ImageEnhance.Color(base).enhance(color);image=ImageEnhance.Brightness(image).enhance(brightness)
        if shift:image=image.transform(image.size,Image.Transform.AFFINE,(1,0,0,0,1,shift),resample=Image.Resampling.BICUBIC)
        if emotion=="sad":image=image.filter(ImageFilter.GaussianBlur(.35))
        out=BytesIO();image.save(out,"PNG",optimize=True);variants[emotion]=out.getvalue()
    return variants
