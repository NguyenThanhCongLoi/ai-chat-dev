"""Owner-scoped adaptive chapter gates. No changes to ordinary chat generation."""
from datetime import datetime,timezone
from copy import deepcopy
from ..models import Message,Room,RoomMember,Relationship
from .. import moonfall
DEFAULT={"enabled":True,"minimum_turns":3,"topic_bonus_cap":4,"trust_bonus_cap":2,"chapters":{
 "selene_02":{"points":7,"topics":["pendant","promise","trust","mat day","loi hua","tin tuong"]},
 "selene_03":{"points":10,"topics":["journal","memory","nhat ky","ky uc"]},
 "selene_04":{"points":12,"topics":["choice","ritual","lua chon","nghi le"]},
 "selene_05":{"points":14,"topics":["evidence","truth","bang chung","su that"]},
 "selene_06":{"points":15,"topics":["elarion","letter","thu","remember","nho"]},
 "selene_07":{"points":17,"topics":["missing","time","thoi gian","danh mat"]},
 "selene_08":{"points":19,"topics":["identity","past","future","ban than","qua khu","tuong lai"]}}}
def policy(cfg):return deepcopy(cfg.get("adventure",{}).get("pacing") or DEFAULT)
def validate(value):
    if not isinstance(value,dict) or type(value.get("enabled")) is not bool:raise ValueError("Invalid pacing policy")
    for key,limit in (("minimum_turns",100),("topic_bonus_cap",30),("trust_bonus_cap",20)):
        if type(value.get(key)) is not int or not 0<=value[key]<=limit:raise ValueError("Invalid pacing bound")
    rows=value.get("chapters")
    if not isinstance(rows,dict) or set(rows)!={"selene_0"+str(n) for n in range(2,9)}:raise ValueError("Provide gates for chapters 2 to 8")
    for row in rows.values():
        if not isinstance(row,dict) or type(row.get("points")) is not int or not 1<=row["points"]<=200:raise ValueError("Invalid chapter points")
        topics=row.get("topics")
        if not isinstance(topics,list) or len(topics)>40 or any(not isinstance(t,str) or not 2<=len(t)<=80 for t in topics):raise ValueError("Invalid pacing topics")
def trust(db,user,character):
    row=db.query(Relationship).filter_by(user_id=user,character_id=character,other_character_id=None).first()
    return float(row.trust) if row else 0.
def stamp(db,old,new):
    if new.get("engine_version")!=2:return
    marks=new.setdefault("completion_marks",{})
    for ident in set(new["completed_chapters"])-set(old.get("completed_chapters",[])):
        marks[ident]={"at":datetime.now(timezone.utc).isoformat(),"trust":trust(db,new["owner"],new["character_id"])}
    # Old saves have no completion timestamps. Start a fair new boundary at
    # first migration; never count a user's entire old chat history as new effort.
    for ident in new.get("completed_chapters",[]):
        if ident not in marks:marks[ident]={"at":datetime.now(timezone.utc).isoformat(),"trust":trust(db,new["owner"],new["character_id"])}
def status(db,user,run,target,cfg):
    if run.get("owner")!=user:return {"eligible":False}
    if target=="selene_01":return {"eligible":True}
    chapter=next((c for c in cfg["chapters"] if c["id"]==target),None)
    if not chapter:return {"eligible":False}
    if run.get("admin_preview"):return {"eligible":True}
    if target in run.get("completed_chapters",[]) or target==run["chapter_id"] or target in run.get("chapter_bookmarks",{}):return {"eligible":True}
    previous=cfg["chapters"][chapter["order"]-2]["id"]
    if previous not in run.get("completed_chapters",[]):return {"eligible":False}
    if run.get("attempt_number",1)>1:return {"eligible":True}
    rules=policy(cfg)
    if not rules["enabled"]:return {"eligible":True}
    mark=run.get("completion_marks",{}).get(previous)
    if not mark:return {"eligible":False}
    rooms=db.query(Room.id).join(RoomMember,Room.id==RoomMember.room_id).filter(Room.user_id==user,RoomMember.character_id==run["character_id"]).all()
    owned=[rid for (rid,) in rooms if db.query(RoomMember).filter_by(room_id=rid).count()==1]
    messages=db.query(Message).filter(Message.room_id.in_(owned),Message.sender_type=="user",Message.created_at>mark["at"]).order_by(Message.created_at).limit(500).all() if owned else []
    accepted=[];topics=set();rule=rules["chapters"][target]
    # Topic signals are multilingual; configured custom terms supplement these.
    from .story_enrichment import TOPICS
    keywords=rule["topics"]+TOPICS.get(target,[])
    for message in messages:
        reply=db.query(Message.id).filter(Message.room_id==message.room_id,Message.character_id==run["character_id"],Message.sender_type=="character",Message.reply_to_message_id==message.id,Message.finish_status.notin_(("partial","generating","error"))).first()
        if not reply or not moonfall.quality(message.text,accepted):continue
        folded=" ".join(moonfall.fold(message.text).split());accepted.append(folded)
        for word in keywords:
            if moonfall.phrase_match(word,folded):topics.add(moonfall.fold(word))
    bonus=min(rules["topic_bonus_cap"],len(topics))
    relationship=min(rules["trust_bonus_cap"],max(0,int(round((trust(db,user,run["character_id"])-mark["trust"])*20,6))))
    points=len(accepted)+bonus+relationship
    return {"eligible":len(accepted)>=rules["minimum_turns"] and points>=rule["points"],"turns":len(accepted),"points":points,"required":rule["points"]}
