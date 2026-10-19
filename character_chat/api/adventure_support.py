"""World-only CMS diagnostics, LLM reflections/chronicles and contextual return messages."""
from copy import deepcopy
import hashlib,json
from ..models import Message
from .. import moonfall_store as storage
from ..adventure.knowledge import context
from ..adventure.schema import report
from ..adventure.engine import chapter
from ..world_lastlight import persona_snapshot

def bind_adventure_support(runtime,read,view,save,model,safe,actor):
    app=runtime.app
    def v2(s):
        if s.get("engine_version")!=2:raise runtime.HTTPException(409,"This is a legacy chapter save")
    def generate(db,user,s,kind):
        cfg=s["config"];selected=model(db,cfg)
        spec=actor(db,user,s["character_id"],cfg)
        known=context(s,persona_snapshot(spec))
        instruction=cfg["adventure"]["prompts"][kind]["template"]
        prompts=[dict(role="system",content=runtime.character_engine.RESPONSE_SYSTEM_PROMPT+"\n"+instruction+"\nOUTPUT_LANGUAGE="+s["content_language"]),
                 dict(role="user",content="KNOWN_CONTEXT="+json.dumps(known,ensure_ascii=False))]
        try:answer=runtime.direct_completion(prompts,selected.model_id,selected.api_base,runtime.credential_for_model(db,selected),.55,2400 if kind=="memory_chronicle" else 500,"disabled","default",60 if kind=="memory_chronicle" else 25)
        except Exception:raise runtime.HTTPException(503,"Story writing unavailable; saved progress is unchanged") from None
        if not isinstance(answer,str) or not answer.strip():raise runtime.HTTPException(503,"Empty story writing")
        safe(answer,strict=True)
        return answer.strip()[:16000 if kind=="memory_chronicle" else 2400]

    @app.post("/v1/moonfall/{ident}/reflection")
    def reflection(ident:str,user:str=runtime.Depends(runtime.current_user),db=runtime.Depends(runtime.db_session)):
        old=read(db,user,ident);v2(old)
        if old["chapter_id"] not in old["completed_chapters"]:raise runtime.HTTPException(409,"Finish the chapter first")
        if old["chapter_id"] in old["reflections"]:return view(db,user,old)
        answer=generate(db,user,old,"chapter_reflection")
        new=deepcopy(old);new["reflections"][old["chapter_id"]]=dict(text=answer,language=old["content_language"],prompt_version=old["config"]["adventure"]["prompts"]["chapter_reflection"]["version"])
        save(db,old,new);return view(db,user,new)

    @app.post("/v1/moonfall/{ident}/chronicle")
    def chronicle(ident:str,user:str=runtime.Depends(runtime.current_user),db=runtime.Depends(runtime.db_session)):
        old=read(db,user,ident);v2(old)
        if not old["ending"]:raise runtime.HTTPException(409,"Finish the arc first")
        if old["chronicle"]:return view(db,user,old)
        answer=generate(db,user,old,"memory_chronicle")
        new=deepcopy(old);new["chronicle"]=dict(text=answer,language=old["content_language"],prompt_version=old["config"]["adventure"]["prompts"]["memory_chronicle"]["version"])
        save(db,old,new);return view(db,user,new)

    @app.get("/v1/admin/moonfall/validation")
    def validation(_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        cfg=storage.config(db)
        if cfg.get("schema_version")!=2:return dict(valid=True,errors=[],warnings=[dict(type="legacy_configuration")])
        return report(cfg)

    @app.get("/v1/admin/moonfall/debug/{ident}")
    def debug_get(ident:str,user:str=runtime.Depends(runtime.current_user),_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        s=read(db,user,ident);v2(s)
        from ..adventure.conditions import allows
        return dict(state={k:v for k,v in s.items() if k!="config"},ending_eligible=allows(s["config"]["adventure"]["hidden_ending"],s),validation=report(s["config"]))

    @app.post("/v1/admin/moonfall/debug/{ident}")
    def debug_change(ident:str,data:dict,user:str=runtime.Depends(runtime.current_user),_:None=runtime.Depends(runtime.docs_auth),db=runtime.Depends(runtime.db_session)):
        old=read(db,user,ident);v2(old)
        # Debug changes live in a separate owner-scoped preview run, never the real run.
        import uuid,time
        from ..models import AppSetting
        new=deepcopy(old);new["id"]="debug_"+uuid.uuid4().hex;new["debug_only"]=True;new["admin_preview"]=True;new["revision"]=0
        if set(data)-{"chapter_id","stats","flags","inventory","core_memories","echoes","lore_fragments","ending"}:raise runtime.HTTPException(422,"Unexpected debug controls")
        ch=next((c for c in new["config"]["chapters"] if c["id"]==data.get("chapter_id",new["chapter_id"])),None)
        if not ch:raise runtime.HTTPException(422,"Unknown chapter")
        for key in ("stats","flags","inventory","core_memories","echoes","lore_fragments"):
            if key in data:new[key]=deepcopy(data[key])
        if not isinstance(new["stats"],dict) or set(new["stats"])!={"trust","truth","understanding","sacrifice"} or any(type(v) not in (int,float) or not -100<=v<=100 for v in new["stats"].values()):raise runtime.HTTPException(422,"Invalid debug stats")
        if not isinstance(new["flags"],dict) or any(type(v) is not bool for v in new["flags"].values()):raise runtime.HTTPException(422,"Invalid flags")
        items={i["id"] for i in new["config"]["adventure"]["items"]}
        if not isinstance(new["inventory"],list) or not set(new["inventory"])<=items:raise runtime.HTTPException(422,"Unknown inventory item")
        for key in ("core_memories","echoes","lore_fragments"):
            if not isinstance(new[key],list) or any(not isinstance(v,str) or len(v)>100 for v in new[key]):raise runtime.HTTPException(422,"Invalid archive list")
        new["chapter_id"]=ch["id"];new["location"]=ch["scenes"][0]["id"];new["intro_seen"]=True;new["phase"]="explore";new["reviewing"]=False;new["completed"]=False
        new["completed_chapters"]=[c["id"] for c in new["config"]["chapters"] if c["order"]<ch["order"]]
        new["ending"]=data.get("ending")
        if new["ending"] and new["ending"] not in {e["id"] for e in new["config"]["adventure"]["endings"]}:raise runtime.HTTPException(422,"Unknown ending")
        if new["ending"]:new["phase"]="arc_complete";new["completed"]=True
        db.add(AppSetting(key=storage.run_key(user,new["id"]),value=json.dumps(new,ensure_ascii=False)));db.commit()
        return view(db,user,new)

    def post_chat(db,user,old,room,consent=True):
        if old.get("debug_only"):raise runtime.HTTPException(409,"Debug runs cannot publish memories or chat messages")
        db.expire_all();current=read(db,user,old["id"])
        ch=chapter(current)
        if ch["id"] not in current["completed_chapters"]:return
        existing=current["post_chat_messages"].get(ch["id"])
        if existing:return
        if current.get("ending_is_new") is False:return
        if not consent:return # Preserve the user's choice not to carry World content into chat.
        from ..adventure.return_chat import fallback,award
        # Returning is navigation, never a provider round trip. Use the authored,
        # localized opening; optional reflection writing remains a separate action.
        answer=fallback(current)
        # Reflection writing may finish while the provider is answering.
        db.expire_all();current=read(db,user,old["id"])
        if current["post_chat_messages"].get(ch["id"]):return
        ident=hashlib.sha256(("world_return:"+user+":"+old["id"]+":"+ch["id"]).encode()).hexdigest()
        if not db.get(Message,ident):db.add(Message(id=ident,room_id=room["id"],sender_type="character",character_id=old["character_id"],text=answer))
        new=deepcopy(current);new["post_chat_messages"][ch["id"]]=ident
        for completed in current["completed_chapters"]:award(db,user,current,room,completed)
        save(db,current,new)
    return dict(post_chat=post_chat)
