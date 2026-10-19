"""Reset one owner's learned state; preserve authored cards and CMS configuration.
Runs inside the room-deletion transaction; no commit or filesystem deletion.
"""
import json
import hashlib
from .models import (AppSetting,Character,Memory,PromptTrace,VoiceEvent,
                     CharacterReaction,CharacterRating,CharacterUsage,Room,now)
from .moonfall_store import run_key
from .character_social import purge_actor
from .roleplay_episode import key as episode_key

def reset_key(user,actor):
    return "character_experience_reset:"+hashlib.sha256(json.dumps([user,actor]).encode()).hexdigest()

def reset_cutoff(db,user,actor):
    row=db.get(AppSetting,reset_key(user,actor))
    return row.value if row else ""

def source_was_reset(db,user,actors,created_at):
    return any(created_at<=reset_cutoff(db,user,actor) for actor in actors)

def reset_character_experience(db,user,character_ids):
    ids=set(character_ids)
    if not ids:return
    cutoff=now()
    for actor in ids:
        row=db.get(AppSetting,reset_key(user,actor))
        if row:row.value=cutoff
        else:db.add(AppSetting(key=reset_key(user,actor),value=cutoff))
    aliases=set(ids)
    for row in db.query(Character).filter(Character.user_id==user,Character.id.in_(ids)):
        card=json.loads(row.spec)
        if card.get("preset_type"):aliases.add("preset:"+card["preset_type"])
    for model in (Memory,PromptTrace,VoiceEvent,CharacterReaction,CharacterRating,CharacterUsage):
        db.query(model).filter(model.user_id==user,model.character_id.in_(aliases)).delete(synchronize_session=False)
    from .relationship_voice import key as address_key
    for actor in ids:
        purge_actor(db,user,actor)
        db.query(AppSetting).filter_by(key=address_key(user,actor)).delete(synchronize_session=False)
    rooms=[r.id for r in db.query(Room).filter_by(user_id=user)]
    for room_id in rooms:
        for actor in ids:
            db.query(AppSetting).filter_by(key=episode_key(room_id,actor)).delete(synchronize_session=False)
    # Scan all owner runs, not the UI's limited list.
    for row in db.query(AppSetting).filter(AppSetting.key.startswith(run_key(user,""),autoescape=True)).all():
        state=json.loads(row.value)
        if state.get("owner")==user and state.get("character_id") in aliases:db.delete(row)
    # Legacy saves embed history and checkpoints; authored CMS templates are separate.
    for prefix in ("ai_world:","world_campaign:"):
        for row in db.query(AppSetting).filter(AppSetting.key.startswith(prefix,autoescape=True)).all():
            value=json.loads(row.value)
            if value.get("owner")!=user:continue
            state=value.get("state",value)
            members=set(state.get("members",[]))
            members.update(c["id"] for c in state.get("cast",[]) if isinstance(c,dict) and "id" in c)
            if members & aliases:db.delete(row)
