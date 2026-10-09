"""Shared action sound library. Detection runs locally on streamed narration."""
import hashlib
import json
import math
import uuid
import io
import wave
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import FileResponse, Response
from .models import AppSetting, ActionSoundAsset

ROOT=Path(__file__).resolve().parent.parent/"sound_effect"
TYPES={".wav":"audio/wav",".mp3":"audio/mpeg",".ogg":"audio/ogg"}
DEFAULT_RULES={
    "pageturn":["lật+trang","giở+trang","turn+page","flip+page","翻页","翻頁","ページ+めく","페이지+넘"],
    "pencil-scratch":["viết+bút","viết+chữ","ghi+chép","scribbl","write+pen","writes+pen","writing+pen","pen+scratch"],
    "blanket-movement":["áo+sột soạt","vải+sột soạt","cloth+rustl"],
    "hard-footstep":["bước+chân","footstep"],
    "tap":["đặt+bút+xuống","gác+bút","put+pen+down","set+pen+down","puts+pen+down","sets+pen+down","lays+pen+down"],
    "crow":["quạ+kêu","crow+caw","raven+caw","乌鸦+叫","烏鴉+叫","カラス+鳴","까마귀+울"],
    "paper_crushed":["vò+giấy","crumpl+paper"],
}
def catalog():
    result={}
    if not ROOT.is_dir():return result
    for path in sorted(ROOT.rglob("*")):
        if path.suffix.lower() not in TYPES or not path.is_file() or ROOT.resolve() not in path.resolve().parents:continue
        relative=path.relative_to(ROOT).as_posix()
        key=hashlib.sha256(relative.encode()).hexdigest()[:24]
        result[key]=path
    return result

def config(db):
    row=db.get(AppSetting,"action_sound_settings")
    return json.loads(row.value) if row else {"volume":0.35,"sounds":{}}

def entries(db):
    stored=config(db);overrides=stored.get("sounds",{})
    rows=[]
    for key,path in catalog().items():
        triggers=next((v for token,v in DEFAULT_RULES.items() if token in path.stem.lower()),[])
        info=path.stat()
        rows.append({"id":key,"title":path.stem,"url":f"/v1/roleplay/action-sounds/{key}?v=short2-{info.st_mtime_ns}","triggers":triggers,"enabled":bool(triggers),"volume":1.0,"uploaded":False})
    for key,title in db.query(ActionSoundAsset.id,ActionSoundAsset.title).all():
        rows.append({"id":key,"title":title,"url":f"/v1/roleplay/action-sounds/{key}?v=short2","triggers":[],"enabled":False,"volume":1.0,"uploaded":True})
    for row in rows:row.update({key:value for key,value in overrides.get(row["id"],{}).items() if key in {"triggers","enabled","volume"}})
    return {"volume":stored.get("volume",0.35),"sounds":rows}

def short_wav(content):
    """Keep PCM WAV downloads bounded to the same three seconds played in chat."""
    try:
        with wave.open(io.BytesIO(content), "rb") as source:
            params = source.getparams()
            frames = source.readframes(min(source.getnframes(), source.getframerate() * 3))
        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            target.setparams(params)
            target.writeframes(frames)
        return output.getvalue()
    except (wave.Error, EOFError):
        return content


@lru_cache(maxsize=64)
def bundled_wav(path, modified, size):
    # Stat fields invalidate clips when an administrator replaces a file.
    with wave.open(path, "rb") as source:
        params = source.getparams()
        frames = source.readframes(min(source.getnframes(), source.getframerate() * 3))
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setparams(params)
        target.writeframes(frames)
    return output.getvalue()


def build_action_sound_router(current_user,db_session,admin_auth):
    router=APIRouter()
    @router.get("/v1/roleplay/action-sounds")
    def library(user=Depends(current_user),db=Depends(db_session)):
        data=entries(db);data["sounds"]=[row for row in data["sounds"] if row["enabled"] and row["triggers"]]
        return data

    @router.get("/v1/roleplay/action-sounds/{identifier}")
    def audio(identifier:str,db=Depends(db_session)):
        path=catalog().get(identifier)
        headers={"Cache-Control":"public, max-age=86400","X-Content-Type-Options":"nosniff"}
        if path:
            if path.suffix.lower() == ".wav":
                info = path.stat()
                try:
                    return Response(bundled_wav(str(path), info.st_mtime_ns, info.st_size), media_type="audio/wav", headers=headers)
                except (wave.Error, EOFError):
                    pass
            return FileResponse(path,media_type=TYPES[path.suffix.lower()],headers=headers)
        row=db.get(ActionSoundAsset,identifier)
        if not row:raise HTTPException(404,"Sound not found")
        return Response(short_wav(row.content) if row.mime_type == "audio/wav" else row.content,media_type=row.mime_type,headers=headers)

    @router.get("/v1/admin/action-sounds")
    def admin_library(_=Depends(admin_auth),db=Depends(db_session)):
        return entries(db)

    @router.put("/v1/admin/action-sounds")
    def save(data:dict,_=Depends(admin_auth),db=Depends(db_session)):
        def volume(value):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:raise HTTPException(400,"Volume must be between 0 and 1")
            return value
        overall=volume(data.get("volume"))
        items=data.get("sounds")
        if not isinstance(items,list) or len(items)>300:raise HTTPException(400,"Invalid sound list")
        available={row["id"] for row in entries(db)["sounds"]}
        rules={}
        for item in items:
            if not isinstance(item,dict) or item.get("id") not in available:raise HTTPException(400,"Unknown sound")
            triggers=item.get("triggers")
            if not isinstance(triggers,list) or len(triggers)>30 or any(not isinstance(t,str) or not t.strip() or len(t)>160 for t in triggers):raise HTTPException(400,"Invalid action triggers")
            if not isinstance(item.get("enabled"),bool):raise HTTPException(400,"Invalid enabled state")
            rules[item["id"]]={"enabled":item["enabled"],"volume":volume(item.get("volume")),"triggers":list(dict.fromkeys(t.strip() for t in triggers))}
        row=db.get(AppSetting,"action_sound_settings")
        value=json.dumps({"volume":overall,"sounds":rules},ensure_ascii=False)
        if row:row.value=value
        else:db.add(AppSetting(key="action_sound_settings",value=value))
        db.commit()
        return entries(db)

    @router.post("/v1/admin/action-sounds/upload")
    async def upload(file:UploadFile=File(...),_=Depends(admin_auth),db=Depends(db_session)):
        name=Path((file.filename or "").replace(chr(92),"/")).name
        ext=Path(name).suffix.lower();content=await file.read(20*1024*1024+1)
        valid=(ext==".wav" and content.startswith(b"RIFF") and content[8:12]==b"WAVE") or (ext==".ogg" and content.startswith(b"OggS")) or (ext==".mp3" and (content.startswith(b"ID3") or len(content)>1 and content[0]==255 and content[1]&224==224))
        if not valid:raise HTTPException(400,"Upload WAV, MP3 or OGG audio")
        if len(content)>20*1024*1024:raise HTTPException(413,"Sound must not exceed 20 MB")
        row=ActionSoundAsset(id=uuid.uuid4().hex,title=Path(name).stem[:160],mime_type=TYPES[ext],content=content)
        db.add(row);db.commit()
        return {"id":row.id}

    @router.delete("/v1/admin/action-sounds/{identifier}")
    def remove(identifier:str,_=Depends(admin_auth),db=Depends(db_session)):
        row=db.get(ActionSoundAsset,identifier)
        if not row:raise HTTPException(404,"Uploaded sound not found; disable bundled sounds instead")
        db.delete(row)
        stored=config(db);stored.get("sounds",{}).pop(identifier,None)
        setting=db.get(AppSetting,"action_sound_settings")
        if setting:setting.value=json.dumps(stored,ensure_ascii=False)
        db.commit();return {"deleted":True}
    return router
