"""Authored speech only. Preparing audio never emits story events."""
import hashlib,json
from .engine import chapter

def audio_key(event,language):
    text=event.get("text",{}).get(language,"")
    return hashlib.sha256(json.dumps([event["type"],event.get("speaker") or ("narrator" if event["type"]=="NARRATION" else "selene"),text],ensure_ascii=False).encode()).hexdigest()

def script_events(s,language,include_all_endings=False):
    ch=chapter(s);result={}
    def add(event):
        if event.get("type") not in ("NARRATION","CHARACTER_SPEECH"):return
        speaker=event.get("speaker") or ("narrator" if event["type"]=="NARRATION" else "selene")
        if speaker not in ("narrator","selene") and not s["config"]["adventure"].get("speaker_voices",{}).get(speaker,{}).get(language):return
        if not event.get("text",{}).get(language):return
        row={**event,"speaker":speaker,"source":"authored"}
        result[audio_key(row,language)]=row
    def walk(value):
        if isinstance(value,dict):
            if value.get("type") in ("narration","dialogue"):
                add(dict(type="NARRATION" if value["type"]=="narration" else "CHARACTER_SPEECH",speaker=value.get("speaker"),text=ch["localization"].get(value.get("text_key"),value.get("text",{}))))
            else:
                for item in value.values():walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
    for key in ("scenes","puzzles","choice"):walk(ch[key])
    if ch["order"]<8:walk(ch["memory"]["events"])
    else:
        for ending in s["config"]["adventure"]["endings"]:
            if include_all_endings or ending["id"]!="between_memory_and_moonlight" or s.get("pending_ending")==ending["id"]:walk(ending["events"])
        if include_all_endings or s.get("pending_ending")=="between_memory_and_moonlight":walk(ch["memory"]["events"])
    from .story_enrichment import extra
    for place in ch["scenes"]:
        for obj in place["hotspots"]:walk(extra(s,obj["id"]))
    for puzzle in ch["puzzles"]:walk(extra(s,puzzle["id"]))
    if ch["order"]==1:
        from .chapter_one import config
        add(dict(type="NARRATION",speaker="narrator",text=config(s)["gate_prompt"]))
    # Revisit labels and generated guidance are not fixed chapter assets.
    # Adding them here made the gate->memory preload demand audio CMS could not prepare.
    if ch['order']==1:add(dict(type='NARRATION',speaker='narrator',text=s['config']['intro_narration']))
    return result
