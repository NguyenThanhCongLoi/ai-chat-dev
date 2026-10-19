"""Prepare fixed chapter speech in CMS; game downloads only its authorized chapter."""
import hashlib,json,os,logging
from copy import deepcopy
from threading import Lock
from fastapi import BackgroundTasks
from .. import moonfall_store as storage
from ..adventure.authored_audio import script_events
from ..adventure import engine

def bind_chapter_audio(runtime,read,render):
    app=runtime.app;guard=Lock();job={"running":False,"failures":0}
    def snapshot(db,chapter_id):
        cfg=storage.config(db)
        if cfg.get("schema_version")!=2 or chapter_id not in {c["id"] for c in cfg["chapters"]}:raise runtime.HTTPException(422,"Choose a valid chapter")
        spec=next((p for p in runtime.effective_presets(db) if ("preset:"+p.preset_type==cfg["character_source_id"] if cfg["character_source_id"] else p.name.casefold()=="selene moonbrook")),None)
        if not spec:raise runtime.HTTPException(503,"Select the existing Selene system card in CMS")
        s=engine.fresh("cms_audio",spec.id,cfg["character_source_id"],cfg,"vi",0)
        s["admin_preview"]=True
        return engine.select_chapter(s,chapter_id),spec
    def audio_state(s,db):
        if s.get("engine_version")!=2:raise runtime.HTTPException(409,"Audio preparation requires a current chapter")
        value=deepcopy(s)
        value["config"]["adventure"]["speaker_voices"]=storage.config(db)["adventure"].get("speaker_voices",{})
        return value
    async def catalog(s,lang,db,user,spec=None,include_all_endings=False):
        if lang not in ("vi","en"):return dict(enabled=False,clips=[],version="off")
        clips=[]
        try:
            for key,event in script_events(s,lang,include_all_endings=include_all_endings).items():
                info=await render(s,event,lang,db,user,spec,describe=True)
                clips.append(dict(id=key,version=info["version"],ready=info["ready"]))
        except runtime.HTTPException as exc:
            return dict(enabled=False,clips=[],version="unconfigured",status=exc.status_code)
        version=hashlib.sha256(json.dumps([(c["id"],c["version"]) for c in clips],sort_keys=True).encode()).hexdigest()
        return dict(enabled=True,clips=clips,version=version)
    @app.get("/v1/moonfall/{ident}/chapter-audio")
    async def get_catalog(ident:str,user:str=runtime.Depends(runtime.current_user),db=runtime.Depends(runtime.db_session)):
        s=audio_state(read(db,user,ident),db)
        return await catalog(s,s["content_language"],db,user)
    @app.post("/v1/moonfall/{ident}/chapter-audio/{key}")
    async def prepare_clip(ident:str,key:str,user:str=runtime.Depends(runtime.current_user),db=runtime.Depends(runtime.db_session)):
        s=audio_state(read(db,user,ident),db);lang=s["content_language"]
        if lang not in ("vi","en"):raise runtime.HTTPException(422,"This language uses text-only chapters")
        event=script_events(s,lang).get(key)
        if not event:raise runtime.HTTPException(404,"Audio is not part of the current authorized chapter")
        return await render(s,event,lang,db,user,generate=False)
    @app.get("/v1/admin/moonfall/chapter-audio")
    async def admin_status(chapter_id:str="selene_01",_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        s,spec=snapshot(db,chapter_id);rows={}
        for lang in ("vi","en"):
            result=await catalog(s,lang,db,"cms_audio",spec,include_all_endings=True)
            plan=script_events(s,lang,include_all_endings=True)
            missing=[dict(id=c["id"],speaker=plan[c["id"]].get("speaker"),text=plan[c["id"]]["text"].get(lang,"")) for c in result["clips"] if not c["ready"]]
            rows[lang]=dict(enabled=result["enabled"],ready=sum(c["ready"] for c in result["clips"]),total=len(result["clips"]),status=result.get("status"),missing=missing)
        return dict(chapter_id=chapter_id,languages=rows,**job)
    @app.post("/v1/admin/moonfall/chapter-audio/prepare-line")
    async def admin_line(data:dict,_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        if set(data)!={"chapter_id","language","key"} or any(not isinstance(v,str) for v in data.values()) or data["language"] not in ("vi","en"):raise runtime.HTTPException(422,"Choose a valid scripted line")
        s,spec=snapshot(db,data["chapter_id"])
        event=script_events(s,data["language"],include_all_endings=True).get(data["key"])
        if not event:raise runtime.HTTPException(404,"Unknown scripted line")
        return await render(s,event,data["language"],db,"cms_audio",spec)

    async def prepare_all(ids):
        try:
            with runtime.Session() as db:
                for ident in ids:
                    s,spec=snapshot(db,ident)
                    for lang in ("vi","en"):
                        for event in script_events(s,lang,include_all_endings=True).values():
                            try:await render(s,event,lang,db,"cms_audio",spec)
                            except runtime.HTTPException:job["failures"]+=1
        except Exception:
            job["failures"]+=1
            logging.getLogger(__name__).warning("Chapter audio preparation incomplete; retry in CMS")
        finally:
            with guard:job["running"]=False
    def schedule(tasks,ids=None):
        with guard:
            if job["running"]:return False
            job.update(running=True,failures=0)
        tasks.add_task(prepare_all,ids or ["selene_0"+str(n) for n in range(1,9)])
        return True
    @app.post("/v1/admin/moonfall/chapter-audio/prepare")
    def admin_prepare(data:dict,tasks:BackgroundTasks,_:None=runtime.Depends(runtime.docs_auth)):
        ids=data.get("chapters") or ["selene_0"+str(n) for n in range(1,9)]
        if set(data)-{"chapters"} or not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in {"selene_0"+str(n) for n in range(1,9)} for i in ids):raise runtime.HTTPException(422,"Choose valid chapters")
        started=schedule(tasks,list(dict.fromkeys(ids)))
        return dict(started=started,**job)
    def start_preparation():
        # This runs in the server lifecycle after credentials are loaded.
        # It checks content-addressed files and generates only missing authored audio.
        if os.getenv("WORLD_CHAPTER_PREPARE_ON_STARTUP","false").lower()!="true":return None
        import asyncio
        with guard:
            if job["running"]:return None
            job.update(running=True,failures=0)
        return asyncio.create_task(prepare_all(["selene_0"+str(n) for n in range(1,9)]))
    runtime.start_world_chapter_audio=start_preparation
    def after_save(tasks):
        if os.getenv("WORLD_INTRO_PREPARE_ON_SAVE","true").lower()=="true":schedule(tasks)
    return after_save
