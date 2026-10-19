import math, re, json
from datetime import datetime, timezone
from collections import Counter
from .db import Document, DocumentChunk, Memory, CharacterKnowledge, RoomDocument
from .roleplay_recall import rank_scores, same_statement

def tokens(text): return re.findall(r"\w+",text.lower(),re.UNICODE)
def vector(text):
    counts=Counter(tokens(text)); norm=math.sqrt(sum(v*v for v in counts.values())) or 1
    return {k:v/norm for k,v in counts.items()}
def similarity(a,b):
    va=vector(a); vb=vector(b)
    return sum(v*vb.get(k,0) for k,v in va.items())
def chunks(text,metadata=None,size=750,overlap=80):
    words=text.split(); out=[]; step=max(1,size-overlap)
    for i in range(0,len(words),step):
        segment=" ".join(words[i:i+size])
        if segment: out.append((segment,{**(metadata or {}),"word_start":i}))
        if i+size>=len(words): break
    return out
def allowed(meta,knowledge):
    if knowledge.cutoff_page is not None and meta.get("page") is not None and meta["page"]>knowledge.cutoff_page:return False
    if knowledge.cutoff_chapter is not None and meta.get("chapter") is not None and meta["chapter"]>knowledge.cutoff_chapter:return False
    return True
def retrieve_knowledge(db,character_id,query,limit=4,room_id=None):
    rows=[]
    seen=set()
    for link in db.query(CharacterKnowledge).filter_by(character_id=character_id).all():
        for chunk in db.query(DocumentChunk).filter_by(document_id=link.document_id).all():
            meta=json.loads(chunk.meta)
            if allowed(meta,link): rows.append((similarity(query,chunk.text),chunk,meta));seen.add(chunk.id)
    if room_id:
        for link in db.query(RoomDocument).filter_by(room_id=room_id).all():
            document=db.get(Document,link.document_id)
            if not document or document.status!="ready":continue
            for chunk in db.query(DocumentChunk).filter_by(document_id=link.document_id).all():
                if chunk.id not in seen:
                    meta=json.loads(chunk.meta);meta["filename"]=document.filename
                    rows.append((similarity(query,chunk.text),chunk,meta));seen.add(chunk.id)
    rows.sort(key=lambda x:x[0],reverse=True)
    explicitly_asks_for_document=bool(re.search(r"\b(tài liệu|tai lieu|file|tệp|tep|đính kèm|dinh kem|nội dung|noi dung|tóm tắt|tom tat|document|attachment|attached|summari[sz]e)\b",query,re.I))
    return [{"text":c.text[:1800],"document_id":c.document_id,**m} for s,c,m in rows[:limit] if s>.02 or explicitly_asks_for_document]

def room_document_manifest(db,room_id):
    result=[]
    for link in db.query(RoomDocument).filter_by(room_id=room_id).all():
        document=db.get(Document,link.document_id)
        if document:result.append({"document_id":document.id,"filename":document.filename,"status":document.status})
    return result
def retrieve_memories(db,user_id,character_id,room_id,query,limit=5):
    rows=db.query(Memory).filter_by(user_id=user_id).all()
    visible=[m for m in rows if (m.visibility=="USER_GLOBAL" or m.visibility=="CHARACTER_PRIVATE" and m.character_id==character_id or m.visibility=="ROOM_SHARED" and m.room_id==room_id)]
    if any(m.type=="world_shared" for m in visible):
        from .moonfall_store import shared_memories
        verified={m.id for m in shared_memories(db,user_id,character_id)}
        visible=[m for m in visible if m.type!="world_shared" or m.id in verified]
    relevance = dict(zip((m.id for m in visible), rank_scores(query, [m.content for m in visible])))
    def score(memory):
        try:
            created=datetime.fromisoformat(memory.created_at);created=created if created.tzinfo else created.replace(tzinfo=timezone.utc)
            age_days=max(0,(datetime.now(timezone.utc)-created).total_seconds()/86400)
            recency=1/(1+age_days/30)
        except Exception:recency=.5
        emotional=.12 if memory.type in ("event","preference","llm_extracted") else 0
        confidence = max(0, min(1, memory.confidence if memory.confidence is not None else .5))
        return relevance[memory.id]*.55 + memory.importance*.16 + recency*.09 + emotional*.5 + confidence*.08 + memory.pinned*.06
    pinned=sorted((memory for memory in visible if memory.pinned),key=score,reverse=True)
    # Do not fill the prompt with unrelated recent facts just to reach the limit.
    unpinned=sorted((memory for memory in visible if not memory.pinned and relevance[memory.id]>0),
                    key=lambda m:(score(m), m.created_at, m.id),reverse=True)
    return (pinned+unpinned)[:limit]
def store_memory(db,**values):
    existing=db.query(Memory).filter_by(user_id=values["user_id"],visibility=values["visibility"],character_id=values.get("character_id"),room_id=values.get("room_id")).all()
    for m in existing:
        if same_statement(m.content,values["content"]):
            m.importance=max(m.importance,values.get("importance",.5));db.commit();return m
    from .schemas import uid
    m=Memory(id=uid(),**values);db.add(m);db.commit();return m
