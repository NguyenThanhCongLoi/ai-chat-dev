"""Deterministic Memory Adventure state. No DB, provider, or browser dependencies."""
from copy import deepcopy
import json,time,uuid
from .conditions import allows
from .puzzles import check
def chapter(s):
    return next(c for c in s["config"]["chapters"] if c["id"]==s["chapter_id"])
def scene(s):
    return next(p for p in chapter(s)["scenes"] if p["id"]==s["location"])
def text(ch,key):
    return deepcopy(ch["localization"][key])
def effects(s,stats=None,flags=None,tags=None):
    for key,n in (stats or {}).items():s["stats"][key]+=n
    s["flags"].update(flags or {})
    for tag in tags or []:
        if tag not in s["behavior_tags"]:s["behavior_tags"].append(tag)
def emit(s,raw,ch=None):
    from ..moonfall import emit as base_emit
    ch=ch or chapter(s)
    kind=raw["type"]
    value=text(ch,raw["text_key"]) if "text_key" in raw else raw.get("text",{})
    typed={"narration":"NARRATION","dialogue":"CHARACTER_SPEECH","character_thought":"CHARACTER_THOUGHT"}.get(kind,"SYSTEM")
    visuals={"narration":"","dialogue":"CHARACTER_ENTER","character_thought":"CHARACTER_THOUGHT","visual_effect":"MAGIC_ACTIVATED","character_action":"CHARACTER_REALIZATION","memory_unlock":"MEMORY_UNLOCKED","chapter_complete":"CHAPTER_COMPLETE","arc_complete":"ARC_COMPLETE"}
    if typed in {"CHARACTER_SPEECH","CHARACTER_THOUGHT"}:
        previous=next((e for e in reversed(s["events"]) if e["type"]==typed and e.get("speaker")==raw.get("speaker","selene" if typed=="CHARACTER_SPEECH" else "narrator") and e.get("chapter_id")==s["chapter_id"] and e["text"]==value),None)
        if previous:return previous
    row=base_emit(s,typed,value,raw.get("visual_event",visuals.get(kind,"")),raw.get("expression","thinking"))
    row.update(speaker=raw.get("speaker","selene" if typed=="CHARACTER_SPEECH" else "narrator"),
               event_type=kind,character_action=raw.get("action",""),effect=raw.get("effect",""),chapter_id=s["chapter_id"],scene_id=s["location"])
    if row.get("speaker") not in {"selene","narrator"}:row["voice_role"]=None
    return row
def fresh(owner,actor,source,config,language,trust):
    s=dict(id=uuid.uuid4().hex,owner=owner,character_id=actor,source_id=source,config=deepcopy(config),
        engine_version=2,config_revision=config["revision"],revision=0,content_language=language,chapter_id=config["chapters"][0]["id"],
        location=config["chapters"][0]["scenes"][0]["id"],intro_seen=False,completed=False,events=[],memories=[],receipts=[],turn_count=0,
        created_at=int(time.time()),synced=False,world_trust=trust,meaningful=[],last_hint=0,hint_level=0,stalled_turns=0,
        stats=dict(trust=0,truth=0,understanding=0,sacrifice=0),flags={},inventory=[],core_memories=[],artifacts=[],echoes=[],lore_fragments=[],choices=[],behavior_tags=[],
        inspected=[],solved=[],visited=[],completed_chapters=[],reflections={},post_chat_messages={},chronicle=None,ending=None,proposed_ending=None,
        phase="intro",memory_cursor=0,chapter_bookmarks={},reviewing=False,latest_chapter=config["chapters"][0]["id"],last_progress=time.time(),event_history=[])
    emit(s,{"type":"narration","text":config["intro_narration"],"visual_event":"WORLD_INTRO"})
    return s
def enter_scene(s,ident):
    target=next((p for p in chapter(s)["scenes"] if p["id"]==ident),None)
    if not target:raise ValueError("Scene unavailable")
    from .exploration import scene_open
    if not scene_open(s,target):raise ValueError("Finish investigating the current path first")
    token=s["chapter_id"]+":"+ident
    if token in s["visited"] and s["location"]==ident:return
    s["location"]=ident
    if s.get("reviewing"):
        if token not in s["visited"]:s["visited"].append(token)
        return
    if token not in s["visited"]:
        s["visited"].append(token)
        for index,raw in enumerate(target["events"]):
            event=emit(s,raw)
            if index==0:
                event["action_sound"]="footstep"
                from .chapter_one import enabled as gate_enabled
                if ident=="outer_ruins" and not gate_enabled(s):event["visual_event"]="LOCATION_ENTER"
    # Returning to an explored map is navigation, not another narrated story beat.

def ready(s):
    ch=chapter(s)
    return set(ch["required_inspections"])<=set(s["inspected"]) and all(p["id"] in s["solved"] for p in ch["puzzles"])
def inspect(s,ident):
    from .exploration import object_open,same_map
    place=next((p for p in chapter(s)["scenes"] if any(o["id"]==ident for o in p["hotspots"])),None)
    obj=next((o for o in place["hotspots"] if o["id"]==ident),None) if place else None
    if not obj or not same_map(s,place["id"],s["location"]) or not object_open(s,place,obj):raise ValueError("Object unavailable")
    if ident in s["inspected"]:return
    s["inspected"].append(ident);s["last_progress"]=time.time();s["hint_level"]=0
    for index,raw in enumerate(obj["events"]):
        # Older saved/CMS chapters may reuse one generic line for every object.
        # Keep new clue narration, but never repeat that same scripted speech.
        if raw["type"]=="dialogue":
            value=text(chapter(s),raw["text_key"]) if "text_key" in raw else raw.get("text",{})
            if any(e["type"]=="CHARACTER_SPEECH" and e.get("chapter_id")==s["chapter_id"] and e["text"]==value for e in s["events"]):continue
        event=emit(s,raw)
        event["target_id"]=ident
        if index==0 and not event["visual_event"]:event["visual_event"]="CLUE_DISCOVERED"
        if index==0 and obj.get("item") in {"torn_diary_page","council_record","burned_letter"}:event["action_sound"]="turn page"
    from .story_enrichment import extra
    for raw in extra(s,ident):
        emit(s,raw)["target_id"]=ident
    if ident=="selene_02_pendant":emit(s,{"type":"visual_effect","visual_event":"MEMORY_TRIGGER","effect":"MEMORY_GLOW"})
    if ident=="selene_08_archive":emit(s,{"type":"visual_effect","visual_event":"MEMORY_SPACE_BACKGROUND","effect":"MEMORY_GLOW"})
    item=obj["item"]
    if item and item not in s["inventory"]:
        s["inventory"].append(item);s["artifacts"].append(item)
        emit(s,{"type":"item_acquired","text":obj["title"],"visual_event":"CLUE_DISCOVERED"})
    for field,key in (("echo","echoes"),("lore","lore_fragments")):
        if obj[field] and obj[field] not in s[key]:s[key].append(obj[field])
    effects(s,obj["effects"],obj["flags"],obj["tags"])
    from .exploration import advance_same_map
    advance_same_map(s)
def hint(s,manual=True):
    if not s["config"]["hints"]["enabled"] or s["phase"]!="explore" or s["reviewing"]:return False
    cfg=s["config"]["hints"]
    if time.time()-s["last_hint"]<cfg["cooldown_seconds"]:return False
    if not manual and s["stalled_turns"]<cfg["stalled_turns"] and time.time()-s["last_progress"]<cfg["idle_seconds"]:return False
    missing=[i for i in chapter(s)["required_inspections"] if i not in s["inspected"]]
    if missing:
        from .exploration import object_open
        candidates=[o for p in chapter(s)["scenes"] for o in p["hotspots"] if o["id"] in missing and object_open(s,p,o)]
        obj=next((o for o in candidates if any(x["id"]==o["id"] for x in scene(s)["hotspots"])),candidates[0] if candidates else None)
        if not obj:return False
        from .guidance import observation
        message=observation(s,obj)
    else:
        puzzle=next((p for p in chapter(s)["puzzles"] if p["id"] not in s["solved"]),None)
        message=puzzle["hints"][min(2,s["hint_level"])] if puzzle else {"vi":"Hãy chọn cách bạn muốn đáp lại Selene.","en":"Choose how you wish to answer Selene."}
    if any(e["type"]=="CHARACTER_THOUGHT" and e.get("scene_id")==s["location"] and e["text"]==message for e in s["events"][-12:]):return False
    emit(s,{"type":"character_thought","text":message,"expression":"thinking"})
    s["hint_level"]+=1;s["last_hint"]=time.time();return True
def memory_events(s):
    if chapter(s)["order"]==8 and s.get("pending_ending"):
        ending=next(e for e in s["config"]["adventure"]["endings"] if e["id"]==s["pending_ending"])
        return chapter(s)["memory"]["events"]+ending["events"] if ending["id"]=="between_memory_and_moonlight" else ending["events"]
    return chapter(s)["memory"]["events"]
def begin_memory(s):
    s["phase"]="memory";s["memory_cursor"]=0
    emit(s,{"type":"visual_effect","visual_event":"MEMORY_RECONSTRUCTION_START","effect":"MEMORY_GLOW"})
    emit(s,memory_events(s)[0])
def complete(s):
    ch=chapter(s);ident=ch["id"]
    if ident in s["completed_chapters"]:return
    if ch["order"]==8:
        from .replays import ending_allowed,record
        if not ending_allowed(s,s.get("pending_ending")):raise ValueError("Complete the full current route before an ending")
        record(s)
    s["completed_chapters"].append(ident);s["completed"]=True;s["phase"]="complete"
    hidden=s.get("pending_ending")=="between_memory_and_moonlight"
    if ch["order"]<8 or hidden:
        mid=ch["memory"]["id"]
        if mid not in s["core_memories"]:s["core_memories"].append(mid)
        effects(s,flags=ch["memory"].get("flags",{}))
        reward=dict(id=mid,scope="NORMAL_CHAT_SHARED",title=ch["memory"]["title"],fact=text(ch,ch["memory"]["fact_key"]))
    else:
        end=next(e for e in s["config"]["adventure"]["endings"] if e["id"]==s["pending_ending"])
        reward=dict(id="ENDING_"+end["id"],scope="NORMAL_CHAT_SHARED",title=end["title"],fact=deepcopy(end["events"][0]["text"]))
    if s.get("attempt_id"):reward["attempt_id"]=s["attempt_id"]
    s["memories"].append(reward);s["synced"]=False
    emit(s,{"type":"memory_unlock","text":reward["title"],"visual_event":"MEMORY_UNLOCKED"})
    emit(s,{"type":"visual_effect","visual_event":"MEMORY_RECONSTRUCTION_END","effect":"MEMORY_GLOW"})
    emit(s,{"type":"chapter_complete","text":ch["title"],"visual_event":"CHAPTER_COMPLETE"})
    if ch["order"]==8:
        s["ending"]=s["pending_ending"];s["phase"]="arc_complete"
        emit(s,{"type":"arc_complete","text":reward["title"],"visual_event":"ARC_COMPLETE"})
def select_chapter(old,ident):
    s=deepcopy(old);target=next((c for c in s["config"]["chapters"] if c["id"]==ident and (c["enabled"] or s.get("admin_preview"))),None)
    if not target:raise ValueError("Chapter unavailable")
    order=target["order"]
    if s.get("admin_preview"):
        for prior in s["config"]["chapters"][:order-1]:
            for place in prior["scenes"]:
                for obj in place["hotspots"]:
                    if obj["item"] and obj["item"] not in s["inventory"]:s["inventory"].append(obj["item"])
    if not s.get("admin_preview") and order>1 and s["config"]["chapters"][order-2]["id"] not in s["completed_chapters"]:raise ValueError("Chapter locked")
    if ident==s["chapter_id"]:
        if ident in s["completed_chapters"]:
            s["completed"]=True;s["reviewing"]=True;s["phase"]="explore"
        return s
    s["chapter_bookmarks"][s["chapter_id"]]={k:deepcopy(s[k]) for k in ("location","phase","memory_cursor","proposed_ending","completed") }
    s["chapter_id"]=ident;s["location"]=target["scenes"][0]["id"];s["completed"]=ident in s["completed_chapters"];s["reviewing"]=s["completed"]
    s["intro_seen"]=True;s["proposed_ending"]=None;s["hint_level"]=0
    if s["reviewing"]:s["phase"]="explore"
    else:
        s["latest_chapter"]=ident
        if ident in s["chapter_bookmarks"]:s.update(deepcopy(s["chapter_bookmarks"][ident]))
        else:s["phase"]="explore";s["pending_ending"]=None;enter_scene(s,s["location"])
    return s
def _advance(old,action,value="",manual=True):
    s=deepcopy(old);ch=chapter(s)
    if action in {"open_gate","finish_gate_cinematic"}:
        from .chapter_one import act as gate_action
        return gate_action(s,action)
    if action=="preview_ending":
        from .replays import preview_ending
        return preview_ending(s,value)
    if action=="restart":
        from .replays import restart
        return restart(s)
    if action=="language":
        from ..moonfall import LANGUAGES
        if value not in LANGUAGES:raise ValueError("Unsupported language")
        s["content_language"]=value
        return s
    if action=="chapter":return replay_preview(s,value) if s.get("admin_preview") else select_chapter(s,value)
    if action=="review":
        if s["chapter_id"] not in s["completed_chapters"]:raise ValueError("Complete this chapter first")
        s["reviewing"]=True;s["completed"]=True;s["phase"]="explore"
        return s
    if s["reviewing"]:
        if action=="go" and s["phase"]=="explore":
            enter_scene(s,value)
        elif action=="review_memory" and s["phase"]=="explore":
            if ch["order"]==8:raise ValueError("Endings are revealed once")
            s["phase"]="memory";s["review_playback"]=s.get("review_playback",0)+1
            narration=next((e for e in memory_events(s) if e["type"]=="narration"),None)
            if narration:emit(s,narration)
        elif action=="finish_memory_cinematic" and s["phase"]=="memory":
            s["phase"]="explore"
        else:raise ValueError("This completed chapter is read-only")
        return s
    if action=="intro_complete":
        if s["phase"]=="intro":s["intro_seen"]=True;s["phase"]="explore";enter_scene(s,s["location"])
    elif action=="go":
        if s["phase"]!="explore":raise ValueError("Finish this moment before moving")
        enter_scene(s,value)
    elif action=="inspect":
        if s["phase"]!="explore":raise ValueError("Exploration is closed")
        inspect(s,value)
    elif action=="hint":hint(s,manual)
    elif action=="solve":
        from .exploration import same_map
        data=json.loads(value);p=next((p for p in ch["puzzles"] if p["id"]==data.get("id") and same_map(s,p["scene"],s["location"])),None)
        if s["phase"]!="explore" or not p or not set(p["requires_inspections"])<=set(s["inspected"]):raise ValueError("Gather the evidence first")
        if p["id"] not in s["solved"]:
            if check(p,data.get("answer"),s):
                s["solved"].append(p["id"]);s["flags"].update(p["flags"]);s["hint_level"]=0
                for raw in p["events"]:emit(s,raw)
                from .story_enrichment import extra
                for raw in extra(s,p["id"]):emit(s,raw)
                if ch["order"] in (3,7):emit(s,{"type":"visual_effect","visual_event":"MAGIC_SEAL_ACTIVATE","effect":"MAGIC_PULSE"})
                if ch["order"]==6:emit(s,{"type":"visual_effect","visual_event":"VAULT_AWAKEN","effect":"MAGIC_PULSE"})
                if ch["order"]==8:s["ending_offer_at"]=time.time()+1.8
            else:emit(s,{"type":"character_thought","text":p["hints"][0]})
    elif action=="choice":
        if s["phase"]!="explore" or not ready(s) or any(c["chapter"]==ch["id"] for c in s["choices"]):raise ValueError("Choice unavailable")
        choices=ch["choice"]["options"];pick=next((c for c in choices if c["id"]==value),None)
        if ch["order"]==8:
            final_ids={c["id"]:e["id"] for c,e in zip(choices,s["config"]["adventure"]["endings"][:3])}
            if value=="remember_without_becoming":
                if not s.get("admin_preview") and (not allows(s["config"]["adventure"]["hidden_ending"],s) or time.time()<s.get("ending_offer_at",0)):raise ValueError("Choice unavailable")
                ending="between_memory_and_moonlight"
            else:ending=final_ids.get(value)
            if not ending:raise ValueError("Choice unavailable")
            s["proposed_ending"]=ending;s["phase"]="confirm"
        else:
            if not pick:raise ValueError("Choice unavailable")
            s["choices"].append(dict(id=pick["id"],chapter=ch["id"],label=text(ch,pick["label_key"])))
            effects(s,pick["effects"],pick["flags"],pick["tags"])
            for raw in pick["events"]:emit(s,raw)
            from .chapter_one import enabled as gate_enabled,await_gate
            if gate_enabled(s):await_gate(s)
            else:begin_memory(s)
    elif action=="reconsider":
        if s["phase"]!="confirm":raise ValueError("Not confirming")
        s["phase"]="explore";s["proposed_ending"]=None
    elif action=="confirm_ending":
        if s["phase"]!="confirm" or not s["proposed_ending"]:raise ValueError("Choose first")
        from .replays import ending_allowed,collected
        if not ending_allowed(s,s["proposed_ending"]):raise ValueError("Complete the current route and ending clues first")
        s["pending_ending"]=s["proposed_ending"]
        s["choices"].append(dict(id=s["pending_ending"],chapter=ch["id"],label=next(e["title"] for e in s["config"]["adventure"]["endings"] if e["id"]==s["pending_ending"])))
        if s["pending_ending"] in collected(s):
            # Repeat outcomes keep their identity without replaying a reveal/reward.
            s["ending_is_new"]=False
            s["completed_chapters"].append(ch["id"]);s["completed"]=True
            s["ending"]=s["pending_ending"];s["phase"]="arc_complete"
        else:begin_memory(s)
    elif action=="finish_memory_cinematic":
        if s["phase"]!="memory":raise ValueError("Nothing to finish")
        # Presentation may end, be skipped, or fail. Persist the same authored
        # memory outcome; neither video timing nor TTS decides rewards.
        remaining=memory_events(s)[s["memory_cursor"]+1:]
        for raw in remaining:
            row=emit(s,raw)
            if row["type"]=="NARRATION":row["voice_role"]=None
        s["memory_cursor"]=len(memory_events(s))
        complete(s)
    elif action=="continue":
        if s["phase"]!="memory":raise ValueError("Nothing to advance")
        s["memory_cursor"]+=1
        if s["memory_cursor"]>=len(memory_events(s)):complete(s)
        else:emit(s,memory_events(s)[s["memory_cursor"]])
    else:raise ValueError("Unknown action")
    s["event_history"].append(dict(action=action,value=value[:300],chapter=s["chapter_id"],at=time.time()))
    s["event_history"]=s["event_history"][-2000:]
    return s
def prepare_conversation(old,value):
    s=deepcopy(old)
    emit(s,{"type":"user","text":{s["content_language"]:value}})
    s["events"][-1].update(type="USER",voice_role=None,source="user")
    return s


def replay_preview(old,ident):
    if not old.get("admin_preview"):raise ValueError("Admin preview required")
    if not any(c["id"]==ident for c in old["config"]["chapters"]):raise ValueError("Chapter unavailable")
    s=fresh(old["owner"],old["character_id"],old["source_id"],old["config"],old["content_language"],old["world_trust"])
    s.update(id=old["id"],revision=old["revision"],admin_preview=True,debug_only=True,
             attempt_number=old.get("attempt_number",1)+1,receipts=list(old.get("receipts",[])))
    return admin_preview_chapter(s,ident)


def admin_preview_chapter(s,ident):
    if not s.get("admin_preview"):raise ValueError("Admin preview required")
    # Start chapter one through the normal opening; other chapters receive only prerequisite items.
    if ident==s["chapter_id"]:return s
    return select_chapter(s,ident)


def advance(old,action,value="",manual=True):
    from .presentation_beats import mark
    return mark(old,_advance(old,action,value,manual))
