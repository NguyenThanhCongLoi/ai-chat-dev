import os
import shutil
import subprocess
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import modal

PROJECT_DIR=Path(__file__).resolve().parent
FRONTEND_DIR=PROJECT_DIR/"frontend"
NODE_DIR=Path(r"D:\Chatbot\.tools\node-v24.21.0-win-x64")

def build_frontend_for_deploy():
    def source_fingerprint():
        digest=hashlib.sha256()
        for base in (FRONTEND_DIR/"src",):
            for path in sorted(item for item in base.rglob("*") if item.is_file()):
                digest.update(path.relative_to(FRONTEND_DIR).as_posix().encode());digest.update(path.read_bytes())
        for path in (FRONTEND_DIR/"index.html",FRONTEND_DIR/"admin.html",FRONTEND_DIR/"package.json",FRONTEND_DIR/"package-lock.json",FRONTEND_DIR/"vite.config.ts"):
            if path.exists():digest.update(path.name.encode());digest.update(path.read_bytes())
        return digest.hexdigest()
    npm=shutil.which("npm.cmd") or shutil.which("npm")
    if not npm and (NODE_DIR/"npm.cmd").exists():npm=str(NODE_DIR/"npm.cmd")
    if not npm:
        # Modal imports this module again when a container starts. The built
        # frontend is already included in api_image there, while Node/npm is
        # intentionally absent from the lightweight runtime image.
        if PROJECT_DIR==Path("/root"):return source_fingerprint()
        marker=FRONTEND_DIR/"dist"/".source-fingerprint"
        if (FRONTEND_DIR/"dist"/"index.html").exists() and marker.exists() and marker.read_text(encoding="utf-8").strip()==source_fingerprint():return source_fingerprint()
        raise RuntimeError("Không tìm thấy npm và frontend/dist chưa được build.")
    env=os.environ.copy()
    if NODE_DIR.exists():env["PATH"]=str(NODE_DIR)+os.pathsep+env.get("PATH","")
    if not (FRONTEND_DIR/"node_modules").exists():
        subprocess.run([npm,"install"],cwd=FRONTEND_DIR,env=env,check=True)
    subprocess.run([npm,"run","build"],cwd=FRONTEND_DIR,env=env,check=True)
    fingerprint=source_fingerprint()
    (FRONTEND_DIR/"dist"/".source-fingerprint").write_text(fingerprint,encoding="utf-8")
    return fingerprint

FRONTEND_FINGERPRINT=build_frontend_for_deploy()
BUILD_VERSION=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")+"-"+FRONTEND_FINGERPRINT[:12]

app=modal.App("character-chat")
volume=modal.Volume.from_name("character-chat-data",create_if_missing=True)
llm_secret=modal.Secret.from_name("character-chat-llm")
moderation_secret=modal.Secret.from_name("character-chat-moderation")
docs_secret=modal.Secret.from_name("character-chat-docs")
api_image=modal.Image.debian_slim(python_version="3.12").pip_install("fastapi>=0.115","uvicorn>=0.30","sqlalchemy>=2","pydantic>=2","python-multipart>=0.0.9","httpx>=0.27","pillow>=10.4","pymupdf>=1.24","python-docx>=1.1","python-pptx>=1.0","openpyxl>=3.1","cryptography>=43","modal>=1.5,<2").add_local_dir("character_chat",remote_path="/root/character_chat").add_local_dir("frontend/dist",remote_path="/root/frontend/dist").add_local_dir("image",remote_path="/root/image")
avatar_image=modal.Image.debian_slim(python_version="3.12").pip_install("pillow>=10.4","rembg[cpu]>=2.0.67","httpx>=0.27","modal>=1.5,<2").add_local_dir("character_chat",remote_path="/root/character_chat")

@app.function(image=api_image,cpu=1,memory=1024,timeout=300,scaledown_window=120,max_containers=10,secrets=[llm_secret])
def assistant_worker(messages:list,model:str,api_base:str,api_key:str,temperature:float=.35,max_tokens:int=1000,thinking_mode:str="default",reasoning_effort:str="default",request_timeout:float=12):
    """Independent inference worker for AI Assistant traffic."""
    import httpx
    payload={"model":model,"messages":messages}
    if "gpt-5" in model:payload["max_completion_tokens"]=max_tokens
    else:payload.update({"temperature":temperature,"max_tokens":max_tokens})
    if thinking_mode in ("enabled","disabled"):payload["thinking"]={"type":thinking_mode}
    if thinking_mode!="disabled" and reasoning_effort in ("low","high","max"):payload["reasoning_effort"]=reasoning_effort
    # Do not let an upstream keep the whole fallback chain blocked for minutes.
    # Bound each provider attempt so configured fallbacks remain useful.
    request_timeout=max(4,min(float(request_timeout),45));connect_timeout=min(8,request_timeout)
    timeout=httpx.Timeout(timeout=request_timeout,connect=connect_timeout,read=request_timeout,write=10,pool=5)
    global _assistant_http_client
    try:client=_assistant_http_client
    except NameError:
        client=_assistant_http_client=httpx.Client(timeout=timeout,limits=httpx.Limits(max_connections=20,max_keepalive_connections=10,keepalive_expiry=120))
    try:response=client.post(api_base.rstrip("/")+"/chat/completions",headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},json=payload,timeout=timeout)
    except httpx.HTTPError as exc:raise RuntimeError(f"Gateway network error: {type(exc).__name__}: {exc}") from None
    if response.is_error:
        try:
            body=response.json();detail=body.get("error",{}).get("message") or body.get("message") or response.text
        except Exception:detail=response.text
        # httpx.HTTPStatusError contains request/response objects that Modal
        # cannot deserialize reliably across the function boundary.
        raise RuntimeError(f"Gateway HTTP {response.status_code}: {str(detail)[:1000]}")
    from character_chat.assistant_pipeline import extract_assistant_text
    return extract_assistant_text(response.json())

@app.function(image=api_image,cpu=1,memory=1024,timeout=300,scaledown_window=120,max_containers=10,secrets=[llm_secret])
def assistant_stream_worker(messages:list,model:str,api_base:str,api_key:str,temperature:float=.35,max_tokens:int=1000,thinking_mode:str="default",reasoning_effort:str="default",request_timeout:float=14):
    """Yield visible answer text from an OpenAI-compatible SSE stream."""
    import json,httpx
    payload={"model":model,"messages":messages,"stream":True}
    if "gpt-5" in model:payload["max_completion_tokens"]=max_tokens
    else:payload.update({"temperature":temperature,"max_tokens":max_tokens})
    if thinking_mode in ("enabled","disabled"):payload["thinking"]={"type":thinking_mode}
    if thinking_mode!="disabled" and reasoning_effort in ("low","high","max"):payload["reasoning_effort"]=reasoning_effort
    emitted=False;finish_reason=""
    # ``read`` is also the maximum silence between SSE chunks. If the gateway
    # accepts a request but never starts (or stops) streaming, fail quickly so
    # the web process can immediately advance to the configured fallback.
    request_timeout=max(.1,min(float(request_timeout),45));timeout=httpx.Timeout(timeout=request_timeout,connect=min(8,request_timeout),read=request_timeout,write=min(10,request_timeout),pool=min(5,request_timeout))
    global _assistant_stream_http_client
    try:client=_assistant_stream_http_client
    except NameError:
        client=_assistant_stream_http_client=httpx.Client(timeout=timeout,limits=httpx.Limits(max_connections=20,max_keepalive_connections=10,keepalive_expiry=120))
    try:
        with client.stream("POST",api_base.rstrip("/")+"/chat/completions",headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},json=payload,timeout=timeout) as response:
            if response.is_error:
                raw=response.read().decode("utf-8","replace")
                try:
                    body=json.loads(raw);detail=body.get("error",{}).get("message") or body.get("message") or raw
                except Exception:detail=raw
                raise RuntimeError(f"Gateway HTTP {response.status_code}: {str(detail)[:1000]}")
            for line in response.iter_lines():
                if not line or not line.startswith("data:"):continue
                value=line[5:].strip()
                if value=="[DONE]":break
                try:data=json.loads(value)
                except Exception:continue
                choices=data.get("choices") or []
                if not choices:continue
                choice=choices[0];finish_reason=choice.get("finish_reason") or finish_reason
                content=(choice.get("delta") or {}).get("content")
                if isinstance(content,str) and content:
                    emitted=True;yield content
                elif isinstance(content,list):
                    for part in content:
                        text=part.get("text","") if isinstance(part,dict) else ""
                        if text:emitted=True;yield text
    except RuntimeError:raise
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Gateway network error: {type(exc).__name__}: {exc}") from None
    if not emitted:raise RuntimeError(f"Model returned an empty response (finish_reason={finish_reason or 'unknown'})")
    # The caller must distinguish a complete stream from a token-limited one.
    # Yielding a control record keeps already streamed text visible while the
    # web process requests a seamless continuation.
    if finish_reason in ("stop","tool_calls","content_filter"):
        status="complete"
    elif finish_reason in ("length","max_tokens"):
        status="truncated"
    else:
        status="interrupted"
    yield {"_stream_status":status,"finish_reason":finish_reason or "unknown"}

@app.function(image=avatar_image,cpu=2,memory=4096,timeout=1800,scaledown_window=300,max_containers=4,secrets=[llm_secret],env={"LLM_API_BASE":"https://gateway.avibi.ai/v1","AVATAR_IMAGE_MODEL":"openai/gpt-image-1-mini"})
def process_avatar(content:bytes,model:str="",api_base:str="",api_key:str=""):
    """Generate and cache the expression set once when a source image changes."""
    from character_chat.avatar_pipeline import build_ai_expression_variants,build_expression_variants
    try:return {"images":build_ai_expression_variants(content,model,api_base,api_key),"generated":True,"error":""}
    except Exception as exc:return {"images":build_expression_variants(content),"generated":False,"error":str(exc)[:500]}

@app.function(image=api_image,cpu=1,memory=2048,timeout=21600,volumes={"/data":volume},secrets=[llm_secret,moderation_secret,docs_secret],env={"DATA_DIR":"/data","LLM_API_BASE":"https://gateway.avibi.ai/v1","CHARACTER_IMAGE_DIR":"/root/image","AVATAR_MODAL_FUNCTION":"process_avatar"})
def backfill_avatars(target_name:str="",max_groups:int=0):
    """Durable migration job for existing characters; run outside the web lifecycle."""
    from character_chat.main import backfill_character_expressions,ensure_model_registry
    from character_chat.db import Session,CharacterExpressionAsset
    with Session() as db:ensure_model_registry(db)
    volume.commit()
    backfill_character_expressions(target_name,max_groups or None)
    volume.commit()
    with Session() as db:return {"assets":db.query(CharacterExpressionAsset).count(),"target_name":target_name}

@app.function(image=api_image,cpu=1,memory=2048,timeout=21600,volumes={"/data":volume},secrets=[llm_secret,moderation_secret,docs_secret],env={"DATA_DIR":"/data","LLM_API_BASE":"https://gateway.avibi.ai/v1","CHARACTER_IMAGE_DIR":"/root/image","AVATAR_MODAL_FUNCTION":"process_avatar"})
def regenerate_avatar(character_id:str):
    """Regenerate one exact character instead of selecting by display name."""
    from character_chat.main import regenerate_character_expression_set,ensure_model_registry
    from character_chat.db import Session
    with Session() as db:ensure_model_registry(db)
    result=regenerate_character_expression_set(character_id)
    volume.commit()
    return result

@app.function(image=api_image,cpu=1,memory=1024,timeout=120,volumes={"/data":volume},env={"DATA_DIR":"/data"})
def optimize_preset_avatar(preset_type:str):
    """One-time optimizer for an existing CMS preset avatar."""
    import base64,hashlib,json
    from character_chat.avatar_pipeline import optimize_card_avatar
    from character_chat.db import Session,AppSetting,now
    from character_chat.schemas import CharacterSpec
    with Session() as db:
        asset=db.get(AppSetting,"preset_asset:"+preset_type)
        if not asset:raise RuntimeError("Preset avatar not found")
        data=json.loads(asset.value);before=len(base64.b64decode(data["content"]))
        content,mime=optimize_card_avatar(base64.b64decode(data["content"]))
        version=hashlib.sha256(content).hexdigest()[:12]
        asset.value=json.dumps({"mime_type":mime,"content":base64.b64encode(content).decode("ascii")});asset.updated_at=now()
        for key in ("admin_preset:"+preset_type,"preset_override:"+preset_type):
            row=db.get(AppSetting,key)
            if not row:continue
            spec=CharacterSpec.model_validate_json(row.value);spec.avatar_url=f"/v1/system-characters/{preset_type}/avatar?v={version}"
            row.value=spec.model_dump_json();row.updated_at=now()
        db.commit();volume.commit()
        result={"preset_type":preset_type,"before_bytes":before,"after_bytes":len(content),"mime_type":mime,"version":version}
        print(json.dumps(result,ensure_ascii=False));return result

@app.function(image=api_image,cpu=1,memory=1024,timeout=600,volumes={"/data":volume},env={"DATA_DIR":"/data"})
def optimize_character_avatars():
    """One-time optimizer for all existing user/admin character card images."""
    import hashlib,json
    from character_chat.avatar_pipeline import optimize_card_avatar
    from character_chat.db import Session,Character,CharacterAsset,now
    from character_chat.schemas import CharacterSpec
    result={"assets":0,"before_bytes":0,"after_bytes":0,"failed":[]}
    with Session() as db:
        for asset in db.query(CharacterAsset).all():
            try:
                before=len(asset.content);content,mime=optimize_card_avatar(asset.content)
                asset.content=content;asset.mime_type=mime;asset.updated_at=now()
                row=db.get(Character,asset.character_id)
                if row:
                    spec=CharacterSpec.model_validate_json(row.spec)
                    spec.avatar_url=f"/v1/public/characters/{row.id}/avatar?v={hashlib.sha256(content).hexdigest()[:12]}"
                    row.spec=spec.model_dump_json();row.updated_at=now()
                result["assets"]+=1;result["before_bytes"]+=before;result["after_bytes"]+=len(content)
            except Exception as exc:result["failed"].append({"character_id":asset.character_id,"error":str(exc)[:200]})
        db.commit();volume.commit()
    print(json.dumps(result,ensure_ascii=False));return result

@app.function(image=api_image,cpu=1,memory=1024,timeout=600,volumes={"/data":volume},env={"DATA_DIR":"/data"})
def optimize_assistant_images():
    """Shrink existing Assistant image attachments before future model calls."""
    import json
    from character_chat.avatar_pipeline import optimize_card_avatar
    from character_chat.db import Session,AssistantFile
    result={"images":0,"before_bytes":0,"after_bytes":0,"failed":[]}
    with Session() as db:
        for item in db.query(AssistantFile).all():
            try:
                before=len(item.content);content,mime=optimize_card_avatar(item.content,max_side=1600)
                item.content=content;item.mime_type=mime;result["images"]+=1;result["before_bytes"]+=before;result["after_bytes"]+=len(content)
            except Exception as exc:result["failed"].append({"document_id":item.document_id,"error":str(exc)[:200]})
        db.commit();volume.commit()
    print(json.dumps(result,ensure_ascii=False));return result


# SQLite on a Modal Volume must have a single writer/view. Request concurrency
# remains high inside this container through @modal.concurrent below.
@app.function(image=api_image,cpu=.5,volumes={"/data":volume},secrets=[llm_secret,moderation_secret,docs_secret],timeout=600,scaledown_window=120,max_containers=1,env={"DATA_DIR":"/data","DEMO_AUTH_ENABLED":"false","LLM_PROVIDER":"api","LLM_API_BASE":"https://gateway.avibi.ai/v1","LLM_MODEL":"openai/gpt-4.1-mini","LLM_FALLBACK_MODEL":"","MODERATION_MODEL":"","OPENAI_MODERATION_API_BASE":"https://api.openai.com/v1","FRONTEND_DIST":"/root/frontend/dist","CHARACTER_IMAGE_DIR":"/root/image","AVATAR_MODAL_FUNCTION":"process_avatar","BUILD_VERSION":BUILD_VERSION})
@modal.concurrent(max_inputs=20,target_inputs=12)
@modal.asgi_app()
def web():
    from character_chat.main import app as fastapi_app
    return fastapi_app
