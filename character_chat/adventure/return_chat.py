"""Idempotent rewards for a real shared chapter; previews never leave World."""
import hashlib,json,uuid
from ..models import Relationship,RelationshipEvent
from .languages import enrich
from ..moonfall import localized

RETURN_LINE={"vi":"Mình vẫn đang nghĩ về những gì hai ta vừa trải qua ở Moonfall. Có điều gì ở đó khiến bạn muốn nói thêm với mình không?","en":"I've been thinking about what we just experienced at Moonfall. Was there anything there you'd like to talk through with me?"}
def fallback(s):return localized(enrich(RETURN_LINE),s["content_language"])

def award(db,user,s,room,chapter_id=None):
    if s.get("debug_only") or s.get("admin_preview"):return {}
    ch=chapter_id or s["chapter_id"]
    ident=hashlib.sha256(("moonfall_reward:"+user+":"+s["character_id"]+":"+ch).encode()).hexdigest()
    if db.get(RelationshipEvent,ident):return {}
    row=db.query(Relationship).filter_by(user_id=user,character_id=s["character_id"],other_character_id=None).first()
    if not row:
        row=Relationship(id=str(uuid.uuid4()),user_id=user,character_id=s["character_id"],familiarity=0,trust=0,affinity=0,tension=0,respect=0)
        db.add(row)
    delta={}
    cap=max(0,min(.03,float(s["config"].get("relationship_delta_cap",.01))))
    for key,value in {"trust":.02,"affinity":.01,"familiarity":.01,"respect":.005}.items():
        before=getattr(row,key) or 0;after=min(1,before+min(value,cap));setattr(row,key,after);delta[key]=round(after-before,6)
    db.add(RelationshipEvent(id=ident,user_id=user,character_id=s["character_id"],room_id=room["id"],event_type="world_chapter_completed",valence=1,confidence=1,deltas=json.dumps(delta)))
    return delta
