"""Owner-scoped Moonfall persistence helpers shared by HTTP and normal-chat hook."""
import hashlib
import json
import os
from . import moonfall
from .models import AppSetting,Character,Room,RoomMember,Message,Relationship
from .schemas import CharacterSpec

CONFIG_KEY="moonfall_story_config"
def config(db):
    row=db.get(AppSetting,CONFIG_KEY)
    value=json.loads(row.value) if row else moonfall.seed()
    if os.getenv("WORLD_ADVENTURE_ENABLED","true").lower()=="true" and value.get("schema_version")==1:
        from .adventure.loader import seed
        return seed(value)
    if value.get("schema_version")==2:
        from .adventure.guidance import upgrade
        upgrade(value)
        from .adventure.dialogue_timing import upgrade as upgrade_timing
        upgrade_timing(value)
        value["adventure"]["allow_replay"]=True  # Replay is now supported; old snapshots disabled it.
        from .adventure.chapter_one import DEFAULT as CHAPTER_ONE
        value["adventure"].setdefault("chapter_one_flow",CHAPTER_ONE)
        from .adventure.pacing import policy
        value.setdefault("adventure",{}).setdefault("pacing",policy(value))
        from .adventure.story_enrichment import DATA as STORY_BEATS
        value["adventure"].setdefault("story_beats",STORY_BEATS)
        value["adventure"].setdefault("enrichment_enabled",True)
        value["adventure"].setdefault("music_levels",{"master":.85,"music":.45,"ambient":.2,"effects":.22,"narrator":.9,"character":.9,"duck_gain":.35})
    return value

def enabled():
    return os.getenv("WORLD_DEMO_ENABLED","false").lower()=="true"

def owned_selene(db,user,character_id,cfg=None):
    row=db.get(Character,character_id)
    if not row or row.user_id!=user:return None
    spec=CharacterSpec.model_validate_json(row.spec);cfg=cfg or config(db)
    source=cfg["character_source_id"]
    matches=(source==character_id or source=="preset:"+str(spec.preset_type)) if source else " ".join(spec.name.casefold().split())=="selene moonbrook"
    return spec if matches else None

def eligibility(db,user,character_id,cfg=None):
    cfg=cfg or config(db)
    if not enabled() or not cfg["enabled"] or not owned_selene(db,user,character_id,cfg):return None
    own_rooms=[r.id for r in db.query(Room).join(RoomMember,Room.id==RoomMember.room_id).filter(Room.user_id==user,RoomMember.character_id==character_id)]
    rooms=[r for r in own_rooms if db.query(RoomMember).filter_by(room_id=r).count()==1]
    turns=db.query(Message).filter(Message.room_id.in_(rooms),Message.sender_type=="user").order_by(Message.created_at.desc()).limit(100).all() if rooms else []
    from .conversation_reset import reset_cutoff
    cutoff=reset_cutoff(db,user,character_id)
    accepted=[];days=set()
    for message in turns:
        if message.created_at<=cutoff:continue
        # Only turns with an actual completed response, not abandoned user messages.
        reply=db.query(Message.id).filter(Message.room_id==message.room_id,Message.character_id==character_id,Message.sender_type=="character",
            Message.reply_to_message_id==message.id,Message.finish_status.notin_(("partial","generating","error"))).first()
        if reply and moonfall.quality(message.text,accepted):
            accepted.append(" ".join(moonfall.fold(message.text).split()));days.add(message.created_at[:10])
    relation=db.query(Relationship).filter_by(user_id=user,character_id=character_id,other_character_id=None).first()
    trust=relation.trust if relation else 0
    gate=cfg["entry_gate"]
    ready=(trust>=gate["min_trust"] and len(accepted)>=gate["min_meaningful_turns"] and len(days)>=gate["min_days"] and next(c for c in cfg["chapters"] if c["id"]=="selene_01")["enabled"])
    # Numeric gates are internal, never returned to the ordinary user.
    return dict(eligible=ready,trust=trust,meaningful=len(accepted),days=len(days))

def run_key(user,ident):
    return "moonfall_run:"+hashlib.sha256(user.encode()).hexdigest()[:24]+":"+ident

def user_runs(db,user):
    rows=db.query(AppSetting).filter(AppSetting.key.like(run_key(user,"")+"%"),~AppSetting.key.like(run_key(user,"debug_")+"%")).order_by(AppSetting.updated_at.desc()).limit(10).all()
    return [json.loads(r.value) for r in rows if json.loads(r.value).get("owner")==user and not json.loads(r.value).get("debug_only")]

def chat_hook(db,user,character_id):
    if not enabled():return None
    cfg=config(db);status=eligibility(db,user,character_id,cfg)
    if not status or not status["eligible"] or any(s["character_id"]==character_id for s in user_runs(db,user)):return None
    return dict(title=cfg["title"],hook=cfg["hook"],rule="This optional invitation is available. Mention only if naturally relevant; do not repeat an invitation already in the conversation. Do not invent that the user entered or discovered anything.")

def shared_memories(db,user,character_id):
    from .models import Memory
    result=[]
    for run in user_runs(db,user):
        if run["character_id"]!=character_id or (run.get("engine_version")!=2 and (not run["completed"] or not run.get("synced"))):continue
        rewards=list(run["memories"])+[m for attempt in run.get("finished_attempts",[]) for m in attempt.get("memories",[])]
        for reward in rewards:
            if reward["scope"]!="NORMAL_CHAT_SHARED":continue
            key=hashlib.sha256(("moonfall:"+user+":"+run["id"]+":"+reward["id"]+(":"+reward["attempt_id"] if reward.get("attempt_id") else "")).encode()).hexdigest()
            row=db.get(Memory,key)
            if row and row.user_id==user and row.character_id==character_id and row.type=="world_shared" and row.visibility=="CHARACTER_PRIVATE":result.append(row)
    return result[:3]
