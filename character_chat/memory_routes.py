"""Role Play memory, relationship and prompt trace endpoints."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from .db import Character, CharacterState, Memory, PromptTrace, RelationshipEvent, Room


def build_memory_router(db_session, current_user, owned, memory_out,
                        relationship, ensure_safe_content, uid):
    router = APIRouter()

    def save_manual_roleplay_memory(db,user,content,character_id=None,room_id=None):
        content=str(content or "").strip()
        if not content or len(content)>1000:raise HTTPException(400,"Ký ức phải có từ 1 đến 1000 ký tự")
        try:ensure_safe_content(content)
        except ValueError as exc:raise HTTPException(400,str(exc))
        visibility="ROOM_SHARED" if room_id else "CHARACTER_PRIVATE"
        existing=next((item for item in db.query(Memory).filter_by(user_id=user,character_id=character_id,room_id=room_id,visibility=visibility).all() if item.content.casefold().strip()==content.casefold()),None)
        if existing:
            existing.pinned=1;existing.importance=max(existing.importance,.95)
            db.commit();return memory_out(existing)
        item=Memory(id=uid(),user_id=user,character_id=character_id,room_id=room_id,type="manual",content=content,importance=.95,confidence=1.0,visibility=visibility,pinned=1)
        db.add(item);db.commit();return memory_out(item)

    @router.post("/v1/characters/{character_id}/memories")
    def add_character_memory(character_id:str,data:dict,db:DBSession=Depends(db_session),user:str=Depends(current_user)):
        owned(db,Character,character_id,user)
        return save_manual_roleplay_memory(db,user,data.get("content"),character_id=character_id)

    @router.get("/v1/rooms/{room_id}/memories")
    def room_memories(room_id:str,db:DBSession=Depends(db_session),user:str=Depends(current_user)):
        owned(db,Room,room_id,user)
        return [memory_out(x) for x in db.query(Memory).filter_by(user_id=user,room_id=room_id,visibility="ROOM_SHARED").all()]

    @router.post("/v1/rooms/{room_id}/memories")
    def add_room_memory(room_id:str,data:dict,db:DBSession=Depends(db_session),user:str=Depends(current_user)):
        owned(db,Room,room_id,user)
        return save_manual_roleplay_memory(db,user,data.get("content"),room_id=room_id)

    @router.patch("/v1/memories/{memory_id}")
    def patch_memory(memory_id:str,changes:dict,db:DBSession=Depends(db_session),user:str=Depends(current_user)):
        m=owned(db,Memory,memory_id,user)
        if "content" in changes:m.content=str(changes["content"])[:1000]
        if "pinned" in changes:m.pinned=bool(changes["pinned"])
        db.commit();return memory_out(m)

    @router.delete("/v1/memories/{memory_id}")
    def delete_memory(memory_id:str,db:DBSession=Depends(db_session),user:str=Depends(current_user)):
        db.delete(owned(db,Memory,memory_id,user));db.commit();return {"deleted":True}

    @router.get("/v1/characters/{character_id}/relationship")
    def get_relationship(character_id:str,db:DBSession=Depends(db_session),user:str=Depends(current_user)):
        owned(db,Character,character_id,user)
        row=relationship(db,user,character_id)
        label="Mới gặp" if row.familiarity<.06 else "Đã làm quen" if row.familiarity<.16 else "Quen thuộc" if row.familiarity<.32 else "Tin tưởng" if row.familiarity<.52 else "Thân thiết" if row.familiarity<.75 else "Gắn bó sâu sắc"
        state=db.query(CharacterState).filter_by(user_id=user,character_id=character_id).first()
        events=db.query(RelationshipEvent).filter_by(user_id=user,character_id=character_id).order_by(RelationshipEvent.created_at.desc()).limit(5).all()
        return {"summary":label,"familiarity":row.familiarity,"trust":row.trust,"affection":row.affinity,"conflict":row.tension,"respect":row.respect,"emotion":state.emotion if state else "neutral","emotion_intensity":state.intensity if state else 0,"energy":state.energy if state else .6,"mood":state.mood if state else .5,"recent_events":[{"type":item.event_type,"valence":item.valence,"confidence":item.confidence,"created_at":item.created_at} for item in events]}

    @router.get("/v1/debug/rooms/{room_id}/prompt-traces")
    def prompt_traces(room_id:str,limit:int=10,db:DBSession=Depends(db_session),user:str=Depends(current_user)):
        """Prompt inspector metadata. It never exposes API keys or full system prompts."""
        owned(db,Room,room_id,user)
        rows=db.query(PromptTrace).filter_by(user_id=user,room_id=room_id).order_by(PromptTrace.created_at.desc()).limit(max(1,min(limit,50))).all()
        return [{"id":item.id,"character_id":item.character_id,"query":item.query,"layers":json.loads(item.layers),"memory_ids":json.loads(item.memory_ids),"document_ids":json.loads(item.document_ids),"state":json.loads(item.state),"created_at":item.created_at} for item in rows]

    return router, (save_manual_roleplay_memory, add_character_memory, room_memories, add_room_memory, patch_memory, delete_memory, get_relationship, prompt_traces)
