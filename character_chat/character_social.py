"""Owner-scoped social state for normal Roleplay; no new generation engine."""
import hashlib
import itertools
import json
import re
from sqlalchemy.exc import IntegrityError
from .models import (Character, Room, RoomMember, Message, CharacterSocialState as Edge,
    CharacterSocialKnowledge as Fact, CharacterSocialCanon as Canon,
    CharacterSharedInteraction as Event, now)
from .roleplay_recall import fold

SCOPE="roleplay"
DIMENSIONS=("affinity","trust","respect","jealousy","rivalry","fear","romantic_interest")

def ident(*parts):
    return hashlib.sha256(json.dumps(parts,ensure_ascii=False).encode()).hexdigest()

def edge_id(user,a,b,scope=SCOPE):return ident("edge",user,scope,a,b)
def pair_id(user,a,b,scope=SCOPE):return ident("canon",user,scope,*sorted((a,b)))

def owned(db,user,actor):
    row=db.get(Character,actor)
    if not row or row.user_id!=user:raise ValueError("Character unavailable")
    return row

def edge(db,user,a,b,create=False,scope=SCOPE):
    key=edge_id(user,a,b,scope);row=db.get(Edge,key)
    if not row and create:
        try:
            with db.begin_nested():
                row=Edge(id=key,user_id=user,scope=scope,character_a_id=a,character_b_id=b)
                db.add(row);db.flush()
        except IntegrityError:row=db.get(Edge,key)
    return row

def snapshot(row):
    card=json.loads(row.spec)
    return {"id":row.id,"name":row.name,"role":str((card.get("identity") or {}).get("role",""))[:120]}

def remember_identity(db,user,a,b,source,scope=SCOPE):
    subject=owned(db,user,b)
    key=ident("identity",user,scope,a,b)
    value=json.dumps(snapshot(subject),ensure_ascii=False)
    current=db.get(Fact,key)
    if not current:
        current=Fact(id=key,user_id=user,scope=scope,character_id=a,subject_character_id=b,
            fact_key="introduced_identity",fact_value=value,source=source,knowledge_type="WITNESSED" if source=="witnessed_shared_turn" else "TOLD")
        try:
            with db.begin_nested():db.add(current);db.flush()
        except IntegrityError:pass
    # Do not refresh existing knowledge silently from another actor's mutable card.

def introduce(db,user,a,b,mutual=True,scope=SCOPE):
    if a==b:raise ValueError("Choose another character")
    owned(db,user,a);owned(db,user,b)
    for actor,subject in ((a,b),(b,a)) if mutual else ((a,b),):
        row=edge(db,user,actor,subject,True,scope);row.active=1;row.updated_at=now()
        remember_identity(db,user,actor,subject,"user_introduction",scope)
    db.flush()
    return edge(db,user,a,b,scope=scope)

def canon_for(db,user,a,b,scope=SCOPE):
    return db.get(Canon,pair_id(user,a,b,scope))

def state(row,canon=None):
    if canon:return "RELATIONSHIP"
    if row.interaction_count>=3:return "RELATIONSHIP"
    if row.first_met_at:return "MET"
    return "AWARE"

def label(row):
    if row.rivalry>=18 and row.trust<15:return "rival"
    if row.trust<=2 and row.rivalry>=6:return "suspicious"
    if row.affinity>=30 and row.trust>=35:return "friend"
    return "acquaintance" if row.first_met_at else "introduced"

def fingerprint(messages):
    return ident(*[(m.id,m.room_id,m.sender_type,m.character_id,m.text,m.finish_status) for m in messages])

def valid_sources(db,event):
    ids=json.loads(event.source_ids)
    rows=[db.get(Message,i) for i in ids]
    room=db.get(Room,event.conversation_id)
    if not room or room.user_id!=event.user_id or any(m is None or m.room_id!=room.id for m in rows):return []
    return rows if fingerprint(rows)==event.source_fingerprint else []

def evaluate(actor_name,other_name,text):
    """Conservative direct address only. Uncertain intent -> no emotional delta."""
    value=fold(text).strip()
    name=fold(other_name)
    # Do not score third-person discussion, quotations, hypothetical or questions.
    if any(c in text for c in ('"', '“', '”', '?')):return {}, "GROUP_CHAT"
    if not re.match(r"^@?"+re.escape(name)+r"(?:\s*[,!:.-]\s*|\s+)",value):return {}, "GROUP_CHAT"
    rest=value.lstrip("@")[len(name):].lstrip(" ,!:.-@")
    if re.fullmatch(r"(?:toi khong tin (?:ban|cau)|i (?:do not|don't) trust you)[.!…]*",rest):
        return {"trust":-3,"rivalry":2},"CONFLICT"
    if re.fullmatch(r"(?:toi tin (?:ban|cau)|i trust you|cam on (?:ban|cau)|thank you)[.!…]*",rest):
        return {"trust":2,"respect":1,"affinity":1},"COOPERATION"
    return {}, "GROUP_CHAT"

def record_turn(db,user,room_id,source_id,scope=SCOPE):
    room=db.get(Room,room_id);source=db.get(Message,source_id)
    if not room or room.user_id!=user or not source or source.room_id!=room_id or source.sender_type!="user":return []
    members={m.character_id for m in db.query(RoomMember).filter_by(room_id=room_id)}
    replies=db.query(Message).filter_by(room_id=room_id,sender_type="character",reply_to_message_id=source_id).order_by(Message.created_at,Message.id).all()
    replies=[m for m in replies if m.character_id in members and m.text.strip() and m.finish_status not in ("partial","generating","error")]
    by_actor={m.character_id:m for m in replies}
    events=[]
    for a,b in itertools.combinations(sorted(by_actor),2):
        # Every actor is an owned, fixed group member; no private room is merged.
        ca=owned(db,user,a);cb=owned(db,user,b)
        key=ident("shared",user,scope,a,b,source_id)
        if db.get(Event,key):continue
        sources=[source,by_actor[a],by_actor[b]]
        deltas={};kind="GROUP_CHAT"
        for actor,subject,row,other in ((a,b,ca,cb),(b,a,cb,ca)):
            delta,detected=evaluate(row.name,other.name,by_actor[actor].text)
            deltas[actor]=delta
            if detected!="GROUP_CHAT":kind=detected
        event=Event(id=key,user_id=user,scope=scope,character_a_id=a,character_b_id=b,
            conversation_id=room_id,source_message_id=source_id,interaction_type=kind,
            summary=json.dumps([{"speaker":a,"text":by_actor[a].text[:220]},
                                {"speaker":b,"text":by_actor[b].text[:220]}],ensure_ascii=False),
            source_ids=json.dumps([m.id for m in sources]),source_fingerprint=fingerprint(sources),
            deltas=json.dumps(deltas))
        try:
            with db.begin_nested():db.add(event);db.flush()
        except IntegrityError:continue
        for actor,subject in ((a,b),(b,a)):
            row=edge(db,user,actor,subject,True,scope)
            remember_identity(db,user,actor,subject,"witnessed_shared_turn",scope)
            db.flush()
            # SQL row lock prevents lost updates on databases supporting it.
            row=db.query(Edge).filter_by(id=row.id).populate_existing().with_for_update().one()
            row.interaction_count+=1;row.first_met_at=row.first_met_at or now()
            row.last_interaction_at=now();row.updated_at=now()
            for dimension,delta in deltas[actor].items():
                if dimension in DIMENSIONS:
                    change=max(-3,min(3,float(delta)))
                    setattr(row,dimension,max(0,min(100,getattr(row,dimension)+change)))
        events.append(event)
    db.flush()
    return events

def projection(db,row):
    canon=canon_for(db,row.user_id,row.character_a_id,row.character_b_id,row.scope)
    facts=db.query(Fact).filter_by(user_id=row.user_id,scope=row.scope,character_id=row.character_a_id,subject_character_id=row.character_b_id).all()
    peer=owned(db,row.user_id,row.character_b_id)
    return {"id":row.id,"character_id":row.character_a_id,"other":snapshot(peer),
        "active":bool(row.active),"state":state(row,canon),"label":label(row),
        "origin":"AUTHORED_CANON" if canon else "dynamic",
        "canon":None if not canon else {"text":canon.text,"revision":canon.revision},
        "interaction_count":row.interaction_count,"first_met_at":row.first_met_at,
        "known_facts":[{"kind":f.knowledge_type,"value":json.loads(f.fact_value),"source":f.source} for f in facts]}

def prompt_context(db,user,actor,scope=SCOPE):
    owned(db,user,actor)
    edges=db.query(Edge).filter_by(user_id=user,scope=scope,character_a_id=actor).order_by(Edge.updated_at.desc(),Edge.id).limit(12).all()
    result={"rule":"Unlisted characters are UNKNOWN unless explicitly established by authorized canon or introduced in the current shared room. Never infer acquaintance from a matching name. Awareness is not a meeting or friendship. No access to private chats, memories, secrets or the user's relationship with peers. Canon and witnessed history are separate. Inactive connections retain historical knowledge. Zero emotional scores mean no established signal, not dislike or distrust. Recognize only learned identities; AWARE alone means never met unless canon explicitly says otherwise. Use a saved quotation only as attributed dialogue, not proof of its claims. Preserve your own personality; never reveal internal scores.","connections":[]}
    used=0
    for row in edges:
        if not db.query(Character.id).filter_by(id=row.character_b_id,user_id=user).first():continue
        value=projection(db,row)
        # Current mutable peer role/card must not leak into known information.
        value.pop("other",None);value["subject_character_id"]=row.character_b_id
        value["dynamic_signals"]={k:round(getattr(row,k),2) for k in DIMENSIONS}
        events=db.query(Event).filter(Event.user_id==user,Event.scope==scope,
            ((Event.character_a_id==actor)&(Event.character_b_id==row.character_b_id))|
            ((Event.character_b_id==actor)&(Event.character_a_id==row.character_b_id))).order_by(Event.created_at.desc(),Event.id.desc()).limit(3).all()
        value["shared_history"]=[{"id":e.id,"kind":e.interaction_type,"quoted_dialogue":json.loads(e.summary)} for e in reversed(events) if valid_sources(db,e)]
        size=len(json.dumps(value,ensure_ascii=False))
        if used+size<=5500:result["connections"].append(value);used+=size
    return result

def purge_actor(db,user,actor):
    for model,field1,field2 in ((Event,Event.character_a_id,Event.character_b_id),
        (Canon,Canon.character_a_id,Canon.character_b_id),(Fact,Fact.character_id,Fact.subject_character_id),
        (Edge,Edge.character_a_id,Edge.character_b_id)):
        db.query(model).filter(model.user_id==user,(field1==actor)|(field2==actor)).delete(synchronize_session=False)
