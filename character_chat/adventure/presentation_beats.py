"""Presentation budgets preserve every authored fact in the saved event history."""
import uuid

def budget(events):
    seen={};segment=0
    movies={"ARROW_TRAP","ECHO_GIRL","SEAL_TRAP","ACADEMY_COLLAPSE","ARCHIVE_AWAKENS","MIRROR_DESYNC","PALE_MOON_MANIFESTATION","MAGIC_SEAL_ACTIVATE","VAULT_AWAKEN","MAJOR_REVEAL","CHAPTER_COMPLETE"}
    for event in events:
        if event.get("visual_event") in movies:segment+=1
        event["sequence_segment"]=segment
        beat=event.get("beat_id")
        if not beat or event.get("type") not in ("NARRATION","CHARACTER_SPEECH","CHARACTER_THOUGHT"):continue
        key=(beat,segment,event["type"])
        hidden=key in seen
        seen[key]=True
        event["presentation"]="archive" if hidden else "main"
        event["auto_voice"]=not hidden

def mark(old,new):
    previous={e["id"] for e in old.get("events",[])}
    fresh=[e for e in new.get("events",[]) if e["id"] not in previous]
    # These puzzle movies show the reveal that the following line reacts to.
    if set(new.get("solved",[]))-set(old.get("solved",[])):
        movies=[e for e in fresh if e.get("visual_event") in {"MAGIC_SEAL_ACTIVATE","VAULT_AWAKEN","MAJOR_REVEAL"}]
        if movies:
            fresh=movies+[e for e in fresh if e not in movies]
            new['events']=[e for e in new['events'] if e['id'] in previous]+fresh
    ident=uuid.uuid4().hex
    for event in fresh:event["beat_id"]=ident
    budget(fresh)
    return new
