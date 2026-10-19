"""The browser gets current affordances, never puzzle answers or hidden-ending formula."""
import time
from .engine import chapter,scene,ready
from .conditions import allows
def view(s,character):
    from ..moonfall import localized,language_of
    lang=s["content_language"];ch=chapter(s);place=scene(s)
    def loc(value):return localized(value,lang)
    from .asset_variants import VARIANTS
    from .props import manifest_assets,inventory_art,hotspot_art,DATA
    from .embedded_scenes import scene_view,object_layout,DATA as EMBEDDED
    painted=scene_view(s,place)
    from .chapter_scroll import projection as scroll_projection
    from .chapter_one import projection as gate_projection
    gate_flow=gate_projection(s,loc)
    def presentation(obj):
        origin=next(p for p in ch["scenes"] if any(o["id"]==obj["id"] for o in p["hotspots"]))
        return {**hotspot_art(obj,origin),**object_layout(s,obj,origin)}
    def asset_url(ident):
        path=assets[ident]["path"]
        if assets[ident]["type"]=="VIDEO":
            from .asset_variants import video_version
            from .props import media_root
            return "/v1/moonfall/assets/"+ident+"?v="+video_version(media_root(),path)
        return "/v1/moonfall/assets/"+ident+("?v="+EMBEDDED["version"] if path.startswith(("backgrounds/interactive/","backgrounds/echoes_bg_16x9/")) else "?v="+DATA["version"] if path.startswith("props/") else "?v=cutout1" if path in VARIANTS or "/cutouts/" in path else "")
    from .story_enrichment import outro,speaker_name,shuffled,visuals,stage_view
    selected=set();assets=manifest_assets(s["config"])
    from .chapter_media import asset_ids
    chapter_media=asset_ids(s,assets)
    selected.update(chapter_media)
    selected.add(inventory_art("moon_rune",assets))
    from .exploration import scene_open,object_open,locations,same_map
    if painted:
        selected.add(painted["background"]);selected.update(p["asset"] for p in painted["cleanups"]);selected.update(p["asset"] for p in painted.get("covers",[]))
    stages,scene_note=stage_view(s)
    from .embedded_scenes import DATA as LAYOUT
    selected.update(o["cleanup"]["asset"] for p in ch["scenes"] for obj in p["hotspots"] if (o:=LAYOUT["hotspots"].get(obj["id"],{})).get("cleanup"))
    visual_events=visuals(s["config"])
    selected.update(v["cinematic"] for v in visual_events.values() if v.get("cinematic") in assets)
    selected.add("enter_ruins_video")
    selected.update(a for a in assets if a.startswith("selene_"))
    selected.update(("map_world_select","memory_space","chapter_complete_background",s["config"]["intro_asset"]))
    selected.update(p["background"] for p in ch["scenes"])
    selected.update(presentation(obj)["asset"] for obj in place["hotspots"] if allows(obj.get("requires"),s))
    selected.update(inventory_art(i,assets) for i in s["inventory"])
    from .replacement_media import memory_asset
    if s["phase"]=="memory":
        mid=memory_asset(s,ch)
        if mid:selected.add(mid)
        selected.add(ch["memory"].get("background","memory_space"))
    if ch["order"]<8:selected.add(ch["memory"]["video"])
    # Ending movies are only exposed for the outcome that is actually being played.
    # Ending variants are prepared only within chapter eight.
    if s["phase"]=="memory" and (ending_movie:=memory_asset(s,ch)):
        selected.add(ending_movie)
    if ch["order"]==8 and s.get("ending")=="between_memory_and_moonlight":
        selected.add("ending_video_hidden")
    events=[];seen_scripted=set()
    navigation_titles={loc(p["title"]) for c in s["config"]["chapters"] for p in c["scenes"]}
    for e in s["events"]:
        if e["type"]=="NARRATION" and e.get("source")=="authored" and loc(e["text"]) in navigation_titles:continue
        if s["reviewing"] and e.get("chapter_id") not in (None,ch["id"]):continue
        if e.get("source")=="authored" and e["type"] in {"CHARACTER_SPEECH","CHARACTER_THOUGHT"}:
            signature=(e.get("chapter_id"),e["type"],e.get("speaker"),loc(e["text"]))
            if signature in seen_scripted:continue
            seen_scripted.add(signature)
        row={k:e[k] for k in ("id","type","visual_event","expression","voice_role","source")}
        row.update(scene_id=e.get("scene_id"),sequence_segment=e.get("sequence_segment",0),presentation=e.get("presentation","main"),auto_voice=not s["reviewing"] and e.get("auto_voice",True),beat_id=e.get("beat_id"),target_id=e.get("target_id"),chapter_id=e.get("chapter_id"),speaker_name=loc(speaker_name(s,e.get("speaker"))) if speaker_name(s,e.get("speaker")) else character["name"] if e["type"]=="CHARACTER_SPEECH" else "",text=loc(e["text"]),text_language=language_of(e["text"],lang),
                   event_type=e.get("event_type",""),speaker=e.get("speaker",""),character_action=e.get("character_action",""),effect=e.get("effect",""),action_sound=e.get("action_sound", "footstep" if e.get("visual_event")=="LOCATION_ENTER" else ""))
        from .authored_audio import audio_key
        row["audio_key"]=audio_key(e,lang) if e.get("source")=="authored" and lang in ("vi","en") and e.get("speaker") in (None,"","selene","narrator") else ""
        events.append(row)
    archive={"CORE MEMORIES":[],"ARTIFACTS":[],"ECHOES":[],"LORE":[],"???":[]}
    for memory in s["memories"]:
        if memory["id"] in s["core_memories"]:archive["CORE MEMORIES"].append(dict(id=memory["id"],title=loc(memory["title"]),text=loc(memory["fact"])))
    item_defs={i["id"]:i for i in s["config"]["adventure"]["items"]}
    for ident in s["inventory"]:
        item=item_defs[ident]
        archive["???" if item["category"]=="UNKNOWN" else "ARTIFACTS"].append(dict(id=ident,title=loc(item["title"]),asset=inventory_art(ident,assets),crop=DATA.get("inventory_crops",{}).get(ident),text=""))
    for ident in s["echoes"]:archive["ECHOES"].append(dict(id=ident,title=loc(next((o["title"] for c in s["config"]["chapters"] for p in c["scenes"] for o in p["hotspots"] if o.get("echo")==ident),{"vi":ident,"en":ident})),text=""))
    for ident in s["lore_fragments"]:archive["LORE"].append(dict(id=ident,title=loc({"vi":"Nhớ lại không có nghĩa là trở thành.","en":"To remember is not to become."}),text=""))
    puzzles=[]
    if s["phase"]=="explore" and not s["reviewing"]:
        for p in ch["puzzles"]:
            if same_map(s,p["scene"],s["location"]):
                puzzles.append(dict(id=p["id"],type=p["type"],title=loc(p["title"]),
                    options=shuffled([dict(id=o["id"],label=loc(o["label"])) for o in p["options"]],s,p["id"]),
                    ready=set(p["requires_inspections"])<=set(s["inspected"]) and set(p["required_items"])<=set(s["inventory"]),
                    solved=p["id"] in s["solved"]))
    choices=[]
    if s["phase"]=="explore" and ready(s) and not s["reviewing"]:
        choices=[dict(id=c["id"],label=loc(ch["localization"][c["label_key"]])) for c in ch["choice"]["options"]]
    choices=shuffled(choices,s,"choices")
    offer=s.get("ending_offer_at")
    qualified=ch["order"]==8 and ready(s) and (s.get("admin_preview") or allows(s["config"]["adventure"]["hidden_ending"],s))
    if qualified and choices and (s.get("admin_preview") or offer and time.time()>=offer):
        end=s["config"]["adventure"]["endings"][3];choices.append(dict(id="remember_without_becoming",label=loc(end["label"]),unexpected=True))
    video=None
    if s["phase"]=="memory":
        ident=memory_asset(s,ch)
        if ident in assets:video=dict(id=ident,url=asset_url(ident),key=s["id"]+":"+str(s.get("attempt_number",1))+":"+ch["id"]+":"+str(s.get("pending_ending"))+":"+str(s.get("review_playback",0)),fallback=ch["memory"].get("background","memory_space"),duration=assets[ident]["duration"])
    from .replays import collected
    collection=collected(s)
    return dict(id=s["id"],engine_version=2,admin_preview=bool(s.get("admin_preview") or s.get("debug_only")),revision=s["revision"],config_revision=s["config_revision"],content_language=lang,
        story_language=language_of(ch["title"],lang),character=character,title=loc(s["config"]["title"]),
        scene_effect=ch["order"] if s["phase"]=="memory" else place.get("effect_profile",{"moonbrook_rooftop":8,"council_chamber":3,"underground_chamber":3,"deep_vault":6,"memory_corridor":6,"pale_moon_chamber":7,"moonfall_past":4,"ancient_archive":5}.get(place["background"],1)),
        preview_endings=[dict(id=e["id"],title=loc(e["title"])) for e in s["config"]["adventure"]["endings"]] if s.get("admin_preview") else [],preview_chapters=[dict(id=c["id"],title=loc(c["title"])) for c in s["config"]["chapters"]] if s.get("admin_preview") else [],chapter_one_flow=gate_flow,chapter_scroll=scroll_projection(s,loc),embedded_scene=painted,story_stages=[{**stage,"title":loc(stage["title"])} for stage in stages],scene_note=loc(scene_note),chapter_id=ch["id"],chapter_title=loc(ch["title"]),objective=loc(ch["objective"]),location=s["location"],phase=s["phase"],
        intro_seen=s["intro_seen"],intro_asset=s["config"]["intro_asset"],completed=s["completed"],synced=s["synced"],reviewing=s["reviewing"],
        attempt_number=s.get("attempt_number",1),ending_is_new=s.get("ending_is_new",True),can_restart=bool(s.get("ending") and len(s["completed_chapters"])==8  ),ending_collection=[dict(id=e["id"],title=loc(e["title"]) if e["id"] in collection else "???",discovered=e["id"] in collection) for e in s["config"]["adventure"]["endings"]],can_replay_memory=bool(s["reviewing"] and ch["order"]<8),chapter_media=sorted(chapter_media),corner_asset=inventory_art("moon_rune",assets),events=events,assets={i:dict(id=i,type=a["type"],url=asset_url(i),fallback=a["fallback"],loop=a["loop"],duration=a["duration"]) for i,a in assets.items() if i in selected},
        visual_events=visual_events,bgm=s["config"]["bgm"],access="OPEN",
        return_hint=loc({"vi":"Chương tiếp theo sẽ mở dần qua những cuộc trò chuyện với Selene.","en":"The next chapter will open through your conversations with Selene."}) if ch["order"]<8 else "",chapter_outro=loc(outro(s)),music_levels=s["config"]["adventure"].get("music_levels",{}),
        supporting_cast=[],
        locations=[dict(id=p["id"],name=loc(p["title"]),background=p["background"],scene_ids=p["scene_ids"],x=20+i*50,y=50,locked=p["locked"],ambient="",cinematic="") for i,p in enumerate(locations(s))],
        objects=[dict(id=o["id"],title=loc(o["title"]),**presentation(o),interaction_action="open_gate" if s["phase"]=="gate_ready" and o["id"]=="selene_01_old_gate" else "inspect",interactive=(s["phase"]=="gate_ready" and o["id"]=="selene_01_old_gate") or (s["phase"]=="explore" and not s["reviewing"] and o["id"] not in s["inspected"]),discovered=o["id"] in s["inspected"],collectible=bool(o["item"]) and o.get("remove_on_collect",o["id"] not in {"selene_01_old_gate","selene_01_collapsed_path","selene_01_broken_statue","selene_03_ritual_circle","selene_03_blood_rune","selene_03_council_seal"}),optional=o["optional"]) for origin in ch["scenes"] if same_map(s,origin["id"],place["id"]) for o in origin["hotspots"] if object_open(s,origin,o)],
        puzzles=puzzles,choices=choices,choice_prompt=loc(ch["localization"][ch["choice"]["prompt_key"]]) if choices else "",
        choice_refresh_at=offer if qualified and offer and time.time()<offer else None,
        archive=archive,stats=s["stats"],inventory=s["inventory"],core_memories=s["core_memories"],
        completed_chapters=s["completed_chapters"],memories=[dict(id=m["id"],scope=m["scope"],title=loc(m["title"]),text=loc(m["fact"])) for m in s["memories"]],
        journal=[dict(id=o["id"],title=loc(o["title"]),text=loc(c["localization"][next(e["text_key"] for e in o["events"] if e.get("type")=="narration" and "text_key" in e)]),kind="FACT") for c in s["config"]["chapters"] for p in c["scenes"] for o in p["hotspots"] if o["id"] in s["inspected"]],
        reflection=s["reflections"].get(ch["id"]),reflection_fallback=loc(ch["localization"][ch["reflection_key"]]),
        ending=None if not s["ending"] or ch["order"]!=8 else dict(id=s["ending"],title=loc(next(e["title"] for e in s["config"]["adventure"]["endings"] if e["id"]==s["ending"]))),
        chronicle=s["chronicle"],memory_video=video,memory_position=s["memory_cursor"],
        has_next=False,hints=s["config"]["hints"])
