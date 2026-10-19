"""CMS schema validation and development diagnostics for the complete arc."""
from copy import deepcopy
from pathlib import Path
import re
from .loader import legacy_seed
from .puzzles import TYPES
EVENT_TYPES={"narration","dialogue","character_thought","character_expression","character_action","background_change","foreground_change","bgm","ambient_audio","sfx","voice","wait","visual_effect","explore","hotspot","inspect","item_acquired","item_removed","puzzle","choice","conditional","state_update","memory_unlock","echo_unlock","lore_unlock","video","cinematic","goto","chapter_complete","arc_complete"}
def validate(cfg):
    from .. import moonfall
    if not isinstance(cfg,dict) or cfg.get("schema_version")!=2:raise ValueError("Expected Memory Adventure v2")
    if len(str(cfg))>900000:raise ValueError("Arc too large")
    base=deepcopy(cfg);arc=base.pop("adventure",None)
    if not isinstance(arc,dict) or set(arc)-{"speaker_voices","chapter_one_flow","pacing","enrichment_enabled","story_beats","music_levels"}!={"id","engine","version","allow_replay","hidden_ending","items","prompts","endings"}:raise ValueError("Invalid arc definition")
    if "pacing" in arc:
        from .pacing import validate as validate_pacing
        validate_pacing(arc["pacing"])
    if "music_levels" in arc:
        levels=arc["music_levels"]
        if not isinstance(levels,dict) or set(levels)-{"master","music","ambient","effects","narrator","character","duck_gain"} or any(type(v) not in (int,float) or not 0<=v<=1 for v in levels.values()):raise ValueError("Audio levels must be between 0 and 1")
    if arc["id"]!=cfg["id"] or arc["engine"]!="memory_adventure":raise ValueError("Wrong arc")
    base["schema_version"]=1;base["chapters"]=legacy_seed()["chapters"]
    moonfall.validate(base) # reuse existing media/model/authored-text safety checks
    ids={a["id"] for a in cfg["assets"]}
    def texts(v):
        if not isinstance(v,dict) or not {"vi","en"}<=set(v) or set(v)-set(moonfall.LANGUAGES) or any(not isinstance(t,str) or not t.strip() or len(t)>6000 for t in v.values()):raise ValueError("Provide EN/VI text; other locales optional")
    if "chapter_one_flow" in arc:
        flow=arc["chapter_one_flow"]
        if not isinstance(flow,dict) or set(flow)!={"enabled","gate_prompt","chapter_end","scroll_title","scroll_body"} or type(flow["enabled"]) is not bool:raise ValueError("Invalid Chapter 1 sequence")
        for field in ("gate_prompt","chapter_end","scroll_title","scroll_body"):texts(flow[field])
    if "speaker_voices" in arc:
        voices=arc["speaker_voices"]
        if not isinstance(voices,dict) or set(voices)-{"young_selene","elarion","unknown_girl"}:raise ValueError("Unknown supporting voice")
        for row in voices.values():
            if not isinstance(row,dict) or set(row)-{"vi","en"} or any(not isinstance(v,str) or len(v)>160 for v in row.values()):raise ValueError("Invalid supporting voice")
    if "enrichment_enabled" in arc and type(arc["enrichment_enabled"]) is not bool:raise ValueError("Invalid expansion switch")
    if "story_beats" in arc:
        beats=arc["story_beats"]
        if not isinstance(beats,dict) or not isinstance(beats.get("beats"),dict) or len(beats["beats"])>80:raise ValueError("Invalid story beats")
        valid_hotspots={o["id"] for c in cfg["chapters"] for p in c["scenes"] for o in p["hotspots"]}
        valid_hotspots.update(p["id"] for c in cfg["chapters"] for p in c["puzzles"])
        if set(beats["beats"])-valid_hotspots:raise ValueError("Unknown story beat trigger")
        for rows in beats["beats"].values():
            if not isinstance(rows,list) or len(rows)>8:raise ValueError("Too many beat lines")
            for row in rows:
                if row.get("type") not in {"dialogue","narration","character_thought"} or row.get("speaker") not in {"selene","narrator","young_selene","elarion","unknown_girl"}:raise ValueError("Invalid beat speaker")
                texts(row["text"])
        for group in ("outros","stages","scene_notes"):
            for value in beats.get(group,{}).values():texts(value)
        for value in beats.get("speakers",{}).values():texts(value)
    def unique(rows,label):
        values=[r["id"] for r in rows]
        if len(values)!=len(set(values)) or any(not isinstance(i,str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}",i) for i in values):raise ValueError("Invalid/duplicate "+label)
    unique(arc["items"],"items");items={i["id"] for i in arc["items"]}
    for item in arc["items"]:
        texts(item["title"])
        if item["asset"] not in ids or item["category"] not in {"UNKNOWN","ARTIFACTS"}:raise ValueError("Invalid item art/category")
    def condition(c,depth=0):
        if not isinstance(c,dict) or depth>8:raise ValueError("Invalid condition")
        if not c:return
        if "all" in c or "any" in c:
            key="all" if "all" in c else "any"
            if set(c)!={key} or not isinstance(c[key],list) or not 1<=len(c[key])<=30:raise ValueError("Invalid condition group")
            for child in c[key]:condition(child,depth+1)
        elif "not" in c:condition(c["not"],depth+1)
        elif "stat" in c:
            if c["stat"] not in {"trust","truth","understanding","sacrifice"} or type(c.get("gte")) not in (int,float) or not 0<=c["gte"]<=1000:raise ValueError("Invalid stat gate")
        elif "inventory" in c:
            if c["inventory"] not in items:raise ValueError("Unknown condition item")
        elif not set(c)<={"flag","memory","chapter","choice","echo_count","memory_count","lore_count"}:raise ValueError("Unknown condition")
    condition(arc["hidden_ending"])
    for name in ("chapter_reflection","post_chapter_chat","memory_chronicle","free_chat"):
        p=arc["prompts"].get(name)
        if not p or type(p["version"]) is not int or not isinstance(p["template"],str) or not 20<=len(p["template"])<=10000:raise ValueError("Missing/invalid prompt")
    unique(arc["endings"],"endings")
    if {e["id"] for e in arc["endings"]}!={"remember_me","let_me_forget","new_keeper","between_memory_and_moonlight"}:raise ValueError("Keep four ending identities")
    chapters=cfg["chapters"]
    if len(chapters)!=8 or [c["order"] for c in chapters]!=list(range(1,9)):raise ValueError("Eight ordered chapters required")
    unique(chapters,"chapters")
    def effects(stats,flags,tags):
        if set(stats)-{"trust","truth","understanding","sacrifice"} or any(type(v) is not int or not -10<=v<=10 for v in stats.values()):raise ValueError("Invalid choice stats")
        if not isinstance(flags,dict) or any(not isinstance(k,str) or type(v) is not bool for k,v in flags.items()):raise ValueError("Invalid flags")
        if not isinstance(tags,list) or any(not isinstance(t,str) or len(t)>80 for t in tags):raise ValueError("Invalid tags")
    for ch in chapters:
        texts(ch["title"]);texts(ch["objective"])
        if type(ch["enabled"]) is not bool or ch["implemented"] is not True:raise ValueError("Invalid chapter availability")
        for value in ch["localization"].values():texts(value)
        def events(rows):
            if not isinstance(rows,list) or len(rows)>100:raise ValueError("Invalid events")
            for e in rows:
                if e["type"] not in EVENT_TYPES:raise ValueError("Unknown event type")
                if "text_key" in e and e["text_key"] not in ch["localization"]:raise ValueError("Missing localization key")
                if "text" in e:texts(e["text"])
                if "asset" in e and e["asset"] not in ids:raise ValueError("Missing event asset")
                if e.get("type")=="goto" and e.get("target") not in places:raise ValueError("Missing goto target")
        for scene in ch["scenes"]:
            if "effect_profile" in scene and (type(scene["effect_profile"]) is not int or not 1<=scene["effect_profile"]<=8):raise ValueError("Effect profile must be 1–8")
        unique(ch["scenes"],"scenes");places={p["id"] for p in ch["scenes"]}
        inspected=set()
        for p in ch["scenes"]:
            texts(p["title"])
            if p["background"] not in ids:raise ValueError("Missing background")
            events(p["events"]);unique(p["hotspots"],"hotspots")
            for h in p["hotspots"]:
                if h["id"] in inspected:raise ValueError("Duplicate hotspot")
                inspected.add(h["id"]);texts(h["title"]);events(h["events"])
                if any(type(h[k]) not in (int,float) or not 0<=h[k]<=1 for k in ("x","y","width","height")) or h["width"]<=0 or h["height"]<=0 or h["x"]+h["width"]>1 or h["y"]+h["height"]>1:raise ValueError("Use normalized hotspot rectangles")
                if h.get("scene_asset") and h["scene_asset"] not in ids:raise ValueError("Unknown scene asset")
                if h.get("presentation_mode","floor") not in {"floor","floor_flat","table","wall","light","warm","detail","marker"}:raise ValueError("Invalid presentation mode")
                if h["item"] and h["item"] not in items:raise ValueError("Unknown collectible")
                effects(h["effects"],h["flags"],h["tags"]);condition(h.get("requires",{}))
        if not set(ch["required_inspections"])<=inspected:raise ValueError("Missing required hotspot")
        unique(ch["puzzles"],"puzzles")
        for p in ch["puzzles"]:
            if p["type"] not in TYPES or p["scene"] not in places or not set(p["requires_inspections"])<=inspected or not set(p["required_items"])<=items:raise ValueError("Invalid puzzle references")
            unique(p["options"],"puzzle options");options={o["id"] for o in p["options"]}
            expected=p["solution"] if isinstance(p["solution"],list) else [p["solution"]]
            if not expected or not set(expected)<=options:raise ValueError("Missing puzzle solution")
            for hint in p["hints"]:texts(hint)
            if len(p["hints"])!=3:raise ValueError("Three hint levels required")
            events(p["events"])
        choice=ch["choice"]
        if choice["prompt_key"] not in ch["localization"] or len(choice["options"])<2:raise ValueError("Missing choice")
        unique(choice["options"],"choices")
        for c in choice["options"]:
            if c["label_key"] not in ch["localization"]:raise ValueError("Missing choice text")
            effects(c["effects"],c["flags"],c["tags"]);events(c["events"])
        if ch["memory"]["video"] not in ids or ch["memory"]["fact_key"] not in ch["localization"]:raise ValueError("Missing memory")
        texts(ch["memory"]["title"]);events(ch["memory"]["events"])
    for e in arc["endings"]:
        texts(e["title"])
        for row in e["events"]:texts(row["text"])
    return deepcopy(cfg)
def report(cfg,root=None):
    warnings=[];errors=[]
    try:validate(cfg)
    except (ValueError,KeyError,TypeError,AttributeError) as e:errors.append(str(e))
    root=Path(root or "image/worlds/selene/moonfall")
    used={cfg["intro_asset"],"map_world_select","memory_space","chapter_complete_background"}
    for ch in cfg["chapters"]:
        used.update(h.get("scene_asset") for p in ch["scenes"] for h in p["hotspots"] if h.get("scene_asset"))
        used.update(p["background"] for p in ch["scenes"]);used.add(ch["memory"]["video"])
        used.add(ch["memory"].get("background","memory_space"))
    used.update(i["asset"] for i in cfg["adventure"]["items"])
    used.update(a["id"] for a in cfg["assets"] if a["id"].startswith("selene_"))
    for a in cfg["assets"]:
        if not(root/a["path"]).is_file():warnings.append(dict(type="missing_optional_asset",id=a["id"],path=a["path"],fallback=a["fallback"]))
        if a["id"] not in used:warnings.append(dict(type="unused_asset",id=a["id"],path=a["path"]))
    for ch in cfg["chapters"]:
        for key,values in ch["localization"].items():
            missing=sorted(set(("vi","en","zh","ja","ko","my","km"))-set(values))
            if missing:warnings.append(dict(type="localization_fallback",id=key,languages=missing,fallback="en"))
    return dict(valid=not errors,errors=errors,warnings=warnings)
