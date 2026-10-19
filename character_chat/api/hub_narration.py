"""Timed public intro narration, edited independently of saved chapter state."""
import hashlib
import math
import json
import os
from pathlib import Path
from threading import Lock,BoundedSemaphore
from sqlalchemy.exc import IntegrityError
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
from ..models import AppSetting,ModelConfig
from .. import moonfall_store as storage
KEY="world_hub_narration"
LANGUAGES={"vi","en","zh","ja","ko","my","km"}
SLOTS=BoundedSemaphore(3)
GUARD=Lock()
PENDING=set()
def config(db):
    row=db.get(AppSetting,KEY)
    root=Path(__file__).resolve().parents[1]/"story_data"
    default=json.loads((root/"world_hub_narration.json").read_text(encoding="utf-8"))
    if not row:return default
    value=json.loads(row.value)
    legacy=json.loads((root/"world_hub_narration_legacy.json").read_text(encoding="utf-8"))
    if value.get("cues")==legacy["cues"]:
        # Only the unchanged shipped script follows the new video. Keep CMS
        # mixer/enabled choices; custom scripts and player saves remain intact.
        return {**default,**{k:value[k] for k in ("enabled","music_gain","duck_gain","voice_gain")},"revision":value["revision"]+1}
    return value

def presentation_config(db):
    """Version private browser audio URLs whenever authored copy, voice or provider changes."""
    cfg=config(db);world=storage.config(db)
    providers=[(m.id,m.model_id,m.api_base,m.updated_at) for m in db.query(ModelConfig).filter_by(enabled=1).order_by(ModelConfig.id)]
    version=hashlib.sha256(json.dumps([cfg,world.get("tts_model_id"),world.get("narrator_voices"),providers],ensure_ascii=False,default=str).encode()).hexdigest()[:24]
    return {**cfg,"audio_version":version}

def validate(data):
    if set(data)-{"duration_seconds","silent_windows"}!={"revision","enabled","music_gain","duck_gain","voice_gain","cues"}:raise ValueError("Unexpected intro fields")
    if type(data["revision"]) is not int or type(data["enabled"]) is not bool:raise ValueError("Invalid revision or enabled")
    for key in ("music_gain","duck_gain","voice_gain"):
        if type(data[key]) not in (int,float) or not 0<=data[key]<=1:raise ValueError("Audio gains must be between 0 and 1")
    if data["duck_gain"]>data["music_gain"]:raise ValueError("Ducked music must not exceed normal music")
    if not isinstance(data["cues"],list) or not 1<=len(data["cues"])<=12:raise ValueError("Use 1–12 narration cues")
    duration=data.get("duration_seconds",600)
    if type(duration) not in (int,float) or not math.isfinite(duration) or not 0<duration<=600:raise ValueError("Invalid intro duration")
    windows=data.get("silent_windows",[])
    if not isinstance(windows,list) or len(windows)>12:raise ValueError("Invalid silent windows")
    previous=0;window_ids=set()
    for window in windows:
        if not isinstance(window,dict) or set(window)!={"id","start","end","label"}:raise ValueError("Invalid silent window")
        if not isinstance(window["id"],str) or not window["id"] or window["id"] in window_ids:raise ValueError("Unique silence ID required")
        window_ids.add(window["id"])
        if not isinstance(window["label"],str) or not window["label"].strip() or len(window["label"])>200:raise ValueError("Invalid silence label")
        if any(type(window[k]) not in (int,float) or not math.isfinite(window[k]) for k in ("start","end")) or not previous<=window["start"]<window["end"]<=duration:raise ValueError("Invalid silence timing")
        previous=window["end"]
    ids=set();end=0
    for cue in data["cues"]:
        if set(cue)!={"id","start","end","text"}:raise ValueError("Invalid cue fields")
        if not isinstance(cue["id"],str) or not cue["id"].replace("_","").isalnum() or len(cue["id"])>60 or cue["id"] in ids:raise ValueError("Unique cue ID required")
        ids.add(cue["id"])
        if any(type(cue[k]) not in (int,float) or not math.isfinite(cue[k]) for k in ("start","end")) or not end<=cue["start"]<cue["end"]<=duration:raise ValueError("Cue times must be ordered and not overlap")
        if any(cue["start"]<w["end"] and cue["end"]>w["start"] for w in windows):raise ValueError("Narration overlaps a silent window")
        end=cue["end"]
        if not isinstance(cue["text"],dict) or set(cue["text"])!=LANGUAGES or any(not isinstance(t,str) or not t.strip() or len(t)>600 for t in cue["text"].values()):raise ValueError("Provide all seven subtitle languages; max 600 characters")
    return data

def bind_hub_narration(runtime,model,safe):
    app=runtime.app
    @app.get("/v1/admin/moonfall/hub-narration")
    def get_admin(_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        return config(db)
    @app.put("/v1/admin/moonfall/hub-narration")
    def put_admin(data:dict,background_tasks:BackgroundTasks,_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        try:validate(data)
        except (ValueError,TypeError,KeyError):raise runtime.HTTPException(422,"Invalid narration: check fields, languages and non-overlapping times") from None
        old=config(db)
        if data["revision"]!=old["revision"]:raise runtime.HTTPException(409,"Intro changed; reload")
        # CMS-authored narration follows the same trusted editorial path as chapters.
        # Authentication, timing/language schema and revision checks still apply.

        next_config={**data,"revision":old["revision"]+1}
        row=db.get(AppSetting,KEY)
        if row:
            changed=db.query(AppSetting).filter_by(key=KEY,value=row.value).update({"value":json.dumps(next_config,ensure_ascii=False)},synchronize_session=False)
            if changed!=1:db.rollback();raise runtime.HTTPException(409,"Intro changed; reload")
        else:db.add(AppSetting(key=KEY,value=json.dumps(next_config,ensure_ascii=False)))
        try:db.commit()
        except IntegrityError:db.rollback();raise runtime.HTTPException(409,"Intro changed; reload") from None
        schedule(background_tasks)
        return next_config

    async def render(cue_id,language,db,generate=False,describe=False):
        cfg=config(db)
        cue=next((c for c in cfg["cues"] if c["id"]==cue_id),None)
        if not cfg["enabled"] or not cue:raise runtime.HTTPException(404,"Narration unavailable")
        if language not in {"vi","en"}:raise runtime.HTTPException(422,"Choose VI or EN narration; subtitles support all seven languages")
        world=storage.config(db);selected=model(db,world,True)
        chosen=world["narrator_voices"].get(language)
        key=runtime.credential_for_model(db,selected)
        if not key or not chosen:raise runtime.HTTPException(503,"Select the intro narrator VI/EN voice and TTS credentials in World CMS")
        text=cue["text"][language]
        digest=hashlib.sha256(json.dumps([selected.model_id,selected.api_base,chosen,text,hashlib.sha256(key.encode()).hexdigest()],ensure_ascii=False).encode()).hexdigest()
        root=Path(os.getenv("DATA_DIR","data"))/"world_intro_audio"
        path=root/(digest+".mp3")
        if describe:return dict(ready=path.is_file())
        if path.is_file():return runtime.FileResponse(str(path),media_type="audio/mpeg",headers={"Cache-Control":"private, no-cache"})
        if not generate:raise runtime.HTTPException(409,"Narration is not prepared; awaiting CMS audio preparation",headers={"Cache-Control":"no-store"})
        with GUARD:
            if digest in PENDING:raise runtime.HTTPException(429,"Narration preparing; retry",headers={"Retry-After":"2"})
            PENDING.add(digest)
        acquired=SLOTS.acquire(blocking=False)
        if not acquired:
            with GUARD:PENDING.discard(digest)
            raise runtime.HTTPException(429,"Narration busy",headers={"Retry-After":"2"})
        try:
            base=runtime.speech_api_base(runtime.normalized_api_base(selected.api_base))
            async with runtime.httpx.AsyncClient(timeout=25,follow_redirects=False) as client:
                async with client.stream("POST",base+"/audio/speech",headers={"Authorization":"Bearer "+key},json={"model":selected.model_id,"voice":chosen,"input":text,"response_format":"mp3"}) as response:
                    if response.status_code>=400:raise runtime.HTTPException(502,"Narration provider unavailable")
                    if not response.headers.get("content-type","").startswith("audio/"):raise runtime.HTTPException(502,"Invalid narration audio")
                    output=bytearray()
                    async for chunk in response.aiter_bytes():
                        output.extend(chunk)
                        if len(output)>4*1024*1024:raise runtime.HTTPException(502,"Narration too large")
                    if not output:raise runtime.HTTPException(502,"Empty narration")
            root.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix(".tmp")
            temp.write_bytes(output);temp.replace(path)
            return runtime.FileResponse(str(path),media_type="audio/mpeg",headers={"Cache-Control":"private, no-cache"})
        except runtime.httpx.HTTPError:raise runtime.HTTPException(502,"Narration unavailable") from None
        finally:
            SLOTS.release()
            with GUARD:PENDING.discard(digest)

    @app.get("/v1/admin/moonfall/hub-narration/audio/{cue_id}")
    async def admin_audio(cue_id:str,language:str="vi",_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        return await render(cue_id,language,db)

    @app.get("/v1/admin/moonfall/hub-narration/status")
    async def narration_status(_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        rows=[]
        for language in ("vi","en"):
            for cue in config(db)["cues"]:
                try:
                    info=await render(cue["id"],language,db,describe=True)
                    rows.append(dict(language=language,cue=cue["id"],**info))
                except runtime.HTTPException as exc:
                    rows.append(dict(language=language,cue=cue["id"],ready=False,status=exc.status_code))
        return dict(ready=bool(rows) and all(r["ready"] for r in rows),results=rows)

    @app.post("/v1/admin/moonfall/hub-narration/prepare")
    async def prepare_narration(_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        # Fixed narration is materialized ahead of viewing using the configured CMS voices.
        result=[]
        for language in ("vi","en"):
            for cue in config(db)["cues"]:
                try:
                    await render(cue["id"],language,db,generate=True)
                    result.append(dict(language=language,cue=cue["id"],ready=True))
                except runtime.HTTPException as exc:
                    result.append(dict(language=language,cue=cue["id"],ready=False,status=exc.status_code))
        return dict(ready=all(row["ready"] for row in result),results=result)


    @app.get("/v1/moonfall/hub/narration-config")
    def public_narration(user:str=runtime.Depends(runtime.current_user),db=runtime.Depends(runtime.db_session)):
        return JSONResponse(presentation_config(db),headers={"Cache-Control":"private, no-store"})

    @app.get("/v1/moonfall/hub/narration/{cue_id}")
    async def speech(cue_id:str,language:str="vi",v:str="",user:str=runtime.Depends(runtime.current_user),db=runtime.Depends(runtime.db_session)):
        if v and v!=presentation_config(db)["audio_version"]:
            raise runtime.HTTPException(409,"Narration configuration changed; refresh",headers={"Cache-Control":"no-store"})
        return await render(cue_id,language,db)

    async def prepare_after_save():
        # Fresh session: background execution must not reuse the completed request's session.
        try:
            with runtime.Session() as db:
                if not config(db)["enabled"]:return
                await prepare_narration(None,db)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Intro audio preparation incomplete; retry from CMS")

    def schedule(tasks):
        if os.getenv("WORLD_INTRO_PREPARE_ON_SAVE","true").lower()=="true":
            tasks.add_task(prepare_after_save)

    return schedule
