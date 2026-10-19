"""User-facing tools for ordinary Roleplay; no routes depend on Worlds."""
import json
import uuid
import hashlib
from types import ModuleType
from sqlalchemy.exc import IntegrityError
from .. import roleplay_continuity as continuity
from ..retrieval import retrieve_memories


def bind_roleplay_continuity(runtime: ModuleType):
    app = runtime.app

    def access(db, room_id, user, character_id=None):
        room = runtime.owned(db, runtime.Room, room_id, user)
        ids = {m.character_id for m in db.query(runtime.RoomMember).filter_by(room_id=room_id).all()}
        if character_id is not None and character_id not in ids:
            raise runtime.HTTPException(404, "Character is not in this room")
        return room, ids

    def text(value, size):
        if not isinstance(value, str) or len(value) > size:
            raise runtime.HTTPException(422, "Invalid text length")
        return value.strip()

    def boolean(value):
        if type(value) is not bool:
            raise runtime.HTTPException(422, "Expected a boolean")
        return value

    def safe(value):
        try:
            runtime.ensure_safe_content(value)
        except ValueError:
            raise runtime.HTTPException(422, "Content requires moderation. Please revise.") from None

    @app.get("/v1/roleplay/rooms/{room_id}/continuity")
    def continuity_get(room_id: str, user: str = runtime.Depends(runtime.current_user),
                       db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        access(db, room_id, user)
        return continuity.read(db, room_id)

    @app.put("/v1/roleplay/rooms/{room_id}/continuity")
    def continuity_save(room_id: str, data: dict, user: str = runtime.Depends(runtime.current_user),
                        db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        _, members = access(db, room_id, user)
        old = continuity.read(db, room_id)
        if type(data.get("revision")) is not int or data["revision"] != old["revision"]:
            raise runtime.HTTPException(409, "The scene changed. Reload before saving.")
        scene = data.get("scene", old["scene"])
        if not isinstance(scene, dict) or set(scene) - {"location", "time", "objective"}:
            raise runtime.HTTPException(422, "Invalid scene")
        scene = {k: text(scene.get(k, ""), 400 if k == "objective" else 120) for k in ("location", "time", "objective")}
        entries = data.get("lore", old["lore"])
        if not isinstance(entries, list) or len(entries) > 40:
            raise runtime.HTTPException(422, "At most 40 lore entries")
        clean, seen = [], set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise runtime.HTTPException(422, "Invalid lore entry")
            ident = text(entry.get("id", uuid.uuid4().hex), 40)
            if not ident or ident in seen:
                raise runtime.HTTPException(422, "Duplicate or empty lore ID")
            seen.add(ident)
            scope = entry.get("scope", "public")
            if scope not in ("public", "private", "witnessed", "rumor", "discovered"):
                raise runtime.HTTPException(422, "Invalid knowledge scope")
            knowers = entry.get("knowers", [])
            if not isinstance(knowers, list) or any(not isinstance(k, str) or k not in members for k in knowers):
                raise runtime.HTTPException(422, "Knowledge recipients must belong to this room")
            knowers = list(dict.fromkeys(knowers))
            if scope in ("private", "witnessed") and not knowers or scope == "private" and len(knowers) != 1:
                raise runtime.HTTPException(422, "Select valid recipients for private/witnessed lore")
            keys = entry.get("keywords", [])
            if not isinstance(keys, list) or len(keys) > 12:
                raise runtime.HTTPException(422, "At most 12 keywords or aliases")
            keys = list(dict.fromkeys(k for k in (text(k, 60) for k in keys) if k))
            priority = entry.get("priority", 5)
            if type(priority) is not int or not 0 <= priority <= 10:
                raise runtime.HTTPException(422, "Priority must be 0-10")
            canon, always = boolean(entry.get("canon", False)), boolean(entry.get("always", False))
            if canon and scope == "rumor":
                raise runtime.HTTPException(422, "A rumour cannot be locked canon")
            if not always and not keys:
                raise runtime.HTTPException(422, "Add keywords or enable always include")
            title, content = text(entry.get("title", ""), 150), text(entry.get("text", ""), 1500)
            if not title or not content:
                raise runtime.HTTPException(422, "Lore title and text are required")
            clean.append({"id": ident, "title": title, "text": content, "scope": scope, "knowers": knowers,
                          "keywords": keys, "canon": canon, "always": always, "priority": priority,
                          "unlocked": boolean(entry.get("unlocked", False))})
        new = {"revision": old["revision"] + 1, "scene": scene, "lore": clean,
               "use_memory": boolean(data.get("use_memory", old["use_memory"])),
               "auto_memory": boolean(data.get("auto_memory", old["auto_memory"]))}
        safe(json.dumps(new, ensure_ascii=False))
        key = continuity.PREFIX + room_id
        raw = db.query(runtime.AppSetting.value).filter_by(key=key).scalar()
        encoded = json.dumps(new, ensure_ascii=False)
        try:
            if raw is None:
                db.add(runtime.AppSetting(key=key, value=encoded))
            else:
                if json.loads(raw)["revision"] != old["revision"] or db.query(runtime.AppSetting).filter_by(key=key, value=raw).update({"value": encoded}, synchronize_session=False) != 1:
                    db.rollback()
                    raise runtime.HTTPException(409, "The scene changed. Reload before saving.")
            db.commit()
        except IntegrityError:
            db.rollback()
            raise runtime.HTTPException(409, "The scene changed. Reload before saving.") from None
        return new

    def source(db, ident, user):
        message = db.get(runtime.Message, ident) if ident else None
        room = db.get(runtime.Room, message.room_id) if message else None
        return message if room and room.user_id == user else None

    @app.get("/v1/roleplay/rooms/{room_id}/pins")
    def pinned_messages(room_id: str, user: str = runtime.Depends(runtime.current_user),
                        db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        access(db, room_id, user)
        rows=db.query(runtime.Memory.source_message_id).join(runtime.Message,runtime.Memory.source_message_id==runtime.Message.id).filter(
            runtime.Memory.user_id==user,runtime.Memory.pinned==1,runtime.Memory.type=="pinned_message",runtime.Message.room_id==room_id).all()
        return {"message_ids":list(dict.fromkeys(row[0] for row in rows if row[0]))}

    @app.post("/v1/roleplay/rooms/{room_id}/remember")
    def remember_message(room_id: str, data: dict, user: str = runtime.Depends(runtime.current_user),
                         db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        _,members=access(db,room_id,user)
        message_id=text(data.get("message_id",""),100)
        message=db.get(runtime.Message,message_id)
        if not message or message.room_id!=room_id or message.sender_type not in ("user","character") or not message.text.strip():
            raise runtime.HTTPException(404,"Message not found")
        character_id=data.get("character_id")
        if character_id is not None and character_id not in members:raise runtime.HTTPException(422,"Choose a room participant")
        if character_id is None and len(members)==1:character_id=next(iter(members))
        visibility="CHARACTER_PRIVATE" if character_id else "ROOM_SHARED"
        if "pinned" in data and type(data["pinned"]) is not bool:raise runtime.HTTPException(422,"Expected a boolean")
        if data.get("pinned",True) is False:
            rows=db.query(runtime.Memory).filter_by(user_id=user,source_message_id=message_id,type="pinned_message")
            if data.get("character_id") is not None:rows=rows.filter_by(character_id=character_id)
            rows.update({"pinned":0},synchronize_session=False);db.commit()
            return {"pinned":False,"message_id":message_id}
        previous=db.query(runtime.Memory).filter_by(user_id=user,source_message_id=message_id,visibility=visibility,character_id=character_id,type="pinned_message").first()
        if previous:
            previous.pinned=1;db.commit()
            return {"id":previous.id,"pinned":True,"message_id":message_id}
        author=db.get(runtime.Character,message.character_id) if message.character_id else None
        content=((author.name if author else "User")+": "+message.text)[:1000]
        safe(content)
        pin_id="pin_"+hashlib.sha256((user+"|"+message_id+"|"+str(character_id)).encode()).hexdigest()
        item=runtime.Memory(id=pin_id,user_id=user,character_id=character_id,
            room_id=None if character_id else room_id,type="pinned_message",content=content,
            importance=.95,confidence=1.0 if message.sender_type=="user" else .6,visibility=visibility,
            pinned=1,source_message_id=message_id)
        try:
            db.add(item);db.commit()
        except IntegrityError:
            db.rollback()
            item=db.get(runtime.Memory,pin_id)
            if item is None:raise runtime.HTTPException(409,"Retry pinning this message") from None
            item.pinned=1;db.commit()
        return {"id":item.id,"pinned":True,"message_id":message_id}

    @app.get("/v1/roleplay/rooms/{room_id}/inspect")
    def continuity_inspect(room_id: str, character_id: str, user: str = runtime.Depends(runtime.current_user),
                           db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        access(db, room_id, user, character_id)
        config = continuity.read(db, room_id)
        latest = db.query(runtime.Message).filter_by(room_id=room_id, sender_type="user").order_by(runtime.Message.created_at.desc(), runtime.Message.id.desc()).first()
        query = latest.text if latest else ""
        predicted = retrieve_memories(db, user, character_id, room_id, query, limit=12) if config["use_memory"] else []
        selected, _, used = continuity.memory_pack(predicted)
        selected_ids = {m.id for m in selected}
        visible = [m for m in db.query(runtime.Memory).filter_by(user_id=user).all()
                   if m.visibility == "USER_GLOBAL" or m.visibility == "CHARACTER_PRIVATE" and m.character_id == character_id
                   or m.visibility == "ROOM_SHARED" and m.room_id == room_id]
        trace = db.query(runtime.PromptTrace).filter_by(user_id=user, room_id=room_id, character_id=character_id).order_by(runtime.PromptTrace.created_at.desc(), runtime.PromptTrace.id.desc()).first()
        last_ids = set(json.loads(trace.memory_ids)) if trace else set()
        memories = []
        for m in sorted(visible, key=lambda m: (not bool(m.pinned), m.created_at), reverse=False)[:100]:
            msg = source(db, m.source_message_id, user)
            memories.append({"id": m.id, "content": m.content, "type": m.type, "pinned": bool(m.pinned),
                             "confidence": m.confidence, "importance": m.importance, "scope": m.visibility,
                             "source_message_id": msg.id if msg else None, "source_text": msg.text[:300] if msg else "",
                             "created_at": m.created_at, "selected": m.id in selected_ids, "used_last_turn": m.id in last_ids})
        return {"memories": memories, "budget": 3200, "estimated_characters": used,
                "use_memory": config["use_memory"], "auto_memory": config["auto_memory"],
                "last_trace_at": trace.created_at if trace else None,
                "visible_lore_ids": [e["id"] for e in continuity.visible_entries(config, character_id)]}

    @app.get("/v1/roleplay/rooms/{room_id}/timeline")
    def continuity_timeline(room_id: str, character_id: str, user: str = runtime.Depends(runtime.current_user),
                            db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        access(db, room_id, user, character_id)
        rows = db.query(runtime.RelationshipEvent).filter_by(user_id=user, character_id=character_id, room_id=room_id).order_by(runtime.RelationshipEvent.created_at.desc(), runtime.RelationshipEvent.id.desc()).limit(50).all()
        result = []
        for e in rows:
            msg = source(db, e.source_message_id, user)
            try:
                deltas = json.loads(e.deltas)
            except (ValueError, TypeError):
                deltas = {}
            result.append({"id": e.id, "type": e.event_type, "valence": e.valence, "confidence": e.confidence,
                           "deltas": {k: v for k, v in deltas.items() if k in ("trust", "affinity", "tension", "respect", "familiarity") and type(v) in (int, float)} if isinstance(deltas, dict) else {},
                           "source_text": msg.text[:300] if msg else "", "created_at": e.created_at})
        return result

    @app.get("/v1/roleplay/rooms/{room_id}/recap")
    def continuity_recap(room_id: str, user: str = runtime.Depends(runtime.current_user),
                         db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        _, ids = access(db, room_id, user)
        names = {c.id: c.name for c in db.query(runtime.Character).filter(runtime.Character.id.in_(ids)).all()}
        rows = db.query(runtime.Message).filter_by(room_id=room_id).order_by(runtime.Message.created_at.desc(), runtime.Message.id.desc()).limit(20).all()[::-1]
        # Quoted excerpts, not a model-generated summary or new canonical facts.
        return {"kind": "excerpts", "items": [{"id": m.id, "speaker": names.get(m.character_id, "User") if m.sender_type == "character" else "User",
                                             "text": m.text[:350], "created_at": m.created_at} for m in rows if m.text.strip()][-10:]}

    # These tools reuse existing room ownership and membership checks.
    @app.get("/v1/roleplay/rooms/{room_id}/episode")
    def episode_get(room_id: str, character_id: str,
                    user: str = runtime.Depends(runtime.current_user),
                    db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        from .. import roleplay_episode as episodes
        access(db, room_id, user, character_id)
        value=episodes.snapshot(db, room_id, character_id)
        return {"episode":value,"graph":episodes.graph(value)}

    @app.post("/v1/roleplay/rooms/{room_id}/episode")
    def episode_generate(room_id: str, data: dict,
                         user: str = runtime.Depends(runtime.current_user),
                         db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        from .. import roleplay_episode as episodes
        actor=text(data.get("character_id",""),120)
        access(db,room_id,user,actor)
        config=continuity.read(db,room_id)
        if not config["auto_memory"] or not config["use_memory"]:
            raise runtime.HTTPException(409,"Enable memory use and automatic memory before generating a recap.")
        character=runtime.owned(db,runtime.Character,actor,user)
        profile=db.get(runtime.UserProfile,user)
        rows=episodes.window(db,room_id)
        picked,payload=episodes.payload(rows,runtime.spec(character),profile.language if profile else "vi")
        if not picked:raise runtime.HTTPException(409,"No dialogue to summarize.")
        current=episodes.snapshot(db,room_id,actor)
        original=db.query(runtime.AppSetting.value).filter_by(key=episodes.key(room_id,actor)).scalar()
        signature=episodes.fingerprint(picked)
        if current and current["source_fingerprint"]==signature:
            return {"episode":current,"graph":episodes.graph(current),"cached":True}
        model=runtime.llm.purpose_models.get("recap") or runtime.llm.fallback_model or runtime.llm.model
        if not model:raise runtime.HTTPException(503,"Assign a chat model in CMS first.")
        # Commit the read transaction before external I/O, then recheck consent,
        # ownership, roster and sources before writing the result.
        db.commit()
        try:
            generated=runtime.llm.json(
                [{"role":"system","content":episodes.PROMPT},
                 {"role":"user","content":json.dumps(payload,ensure_ascii=False)}],
                episodes.Episode,model=model,max_tokens=1800)
            value=episodes.validate(generated.model_dump(),picked)
            safe(json.dumps(value,ensure_ascii=False))
        except runtime.HTTPException:raise
        except Exception:
            raise runtime.HTTPException(503,"Could not create a reliable recap. Existing notes are unchanged.") from None
        db.expire_all()
        access(db,room_id,user,actor)
        config=continuity.read(db,room_id)
        sources=db.query(runtime.Message).filter(runtime.Message.room_id==room_id,
            runtime.Message.id.in_([r.id for r in picked])).all()
        order={r.id:i for i,r in enumerate(picked)}
        sources.sort(key=lambda r:order[r.id])
        if not config["auto_memory"] or not config["use_memory"] or episodes.fingerprint(sources)!=signature:
            raise runtime.HTTPException(409,"Sources or memory settings changed. Retry.")
        value.update(source_ids=[r.id for r in picked],source_fingerprint=signature,
            character_id=actor,created_at=runtime.now(),revision=(current or {}).get("revision",0)+1)
        setting_key=episodes.key(room_id,actor)
        encoded=json.dumps(value,ensure_ascii=False)
        try:
            if original is None:
                db.add(runtime.AppSetting(key=setting_key,value=encoded))
            elif db.query(runtime.AppSetting).filter_by(key=setting_key,value=original).update(
                    {"value":encoded},synchronize_session=False)!=1:
                db.rollback();raise runtime.HTTPException(409,"Notes changed while generating. Reload.")
            db.commit()
        except IntegrityError:
            db.rollback();raise runtime.HTTPException(409,"Another recap was saved. Reload.") from None
        return {"episode":value,"graph":episodes.graph(value),"cached":False}

    @app.delete("/v1/roleplay/rooms/{room_id}/episode")
    def episode_delete(room_id: str, character_id: str,
                       user: str = runtime.Depends(runtime.current_user),
                       db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        from .. import roleplay_episode as episodes
        access(db,room_id,user,character_id)
        row=db.get(runtime.AppSetting,episodes.key(room_id,character_id))
        if row:db.delete(row);db.commit()
        return {"deleted":True}

    @app.put("/v1/roleplay/rooms/{room_id}/episode")
    def episode_edit(room_id: str, data: dict,
                     user: str = runtime.Depends(runtime.current_user),
                     db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        from .. import roleplay_episode as episodes
        actor=text(data.get("character_id",""),120)
        access(db,room_id,user,actor)
        value=episodes.snapshot(db,room_id,actor)
        if not value:raise runtime.HTTPException(409,"Sources changed; generate a new recap.")
        if type(data.get("revision")) is not int or data["revision"]!=value["revision"]:
            raise runtime.HTTPException(409,"Notes changed. Reload before editing.")
        summary=text(data.get("summary"),1800)
        perspective=text(data.get("perspective"),900)
        safe(summary+"\n"+perspective)
        row=db.get(runtime.AppSetting,episodes.key(room_id,actor))
        original=row.value
        value.update(summary=summary,perspective=perspective,edited_by_user=True,revision=value["revision"]+1)
        if db.query(runtime.AppSetting).filter_by(key=row.key,value=original).update(
            {"value":json.dumps(value,ensure_ascii=False)},synchronize_session=False)!=1:
            db.rollback();raise runtime.HTTPException(409,"Notes changed. Reload.")
        db.commit()
        return {"episode":value,"graph":episodes.graph(value)}
