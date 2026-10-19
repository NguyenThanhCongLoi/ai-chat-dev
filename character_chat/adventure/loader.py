"""Load the eight authored chapters and extend the existing World configuration."""
from copy import deepcopy
import json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/"story_data"
def legacy_seed():
    return json.loads((ROOT/"echoes_of_moonfall.json").read_text(encoding="utf-8"))
def seed(previous=None):
    base=legacy_seed()
    arc=json.loads((ROOT/"moonfall_arc/arc.json").read_text(encoding="utf-8"))
    chapters=[json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT/"moonfall_arc").glob("ch??.json"))]
    cfg=deepcopy(base);cfg.update(schema_version=2,chapters=chapters,adventure=arc)
    if previous:
        for key in base:
            if key not in {"schema_version","chapters","assets","visual_events","intro_asset","intro_narration"} and key in previous:cfg[key]=deepcopy(previous[key])
    assets={a["id"]:a for a in cfg["assets"]}
    def add(ident,path,kind="IMAGE",fallback="",duration=0):
        row=deepcopy(base["assets"][0])
        row.update(id=ident,path=path,type=kind,fallback=fallback,duration=duration,loop=False,audio_category="",locale_if_any="",mobile_variant="")
        assets[ident]=row
    for ident,path in {
        "selene_neutral":"neutral.webp","selene_serious":"serious.webp","selene_worried":"worry.webp","selene_determined":"determined.webp","selene_fear":"fear.webp",
        "selene_touch_pendant":"touch pendant.webp","selene_magic":"magic.webp"
    }.items():add(ident,"characters/"+path,fallback="selene_thinking")
    for ident,path in {"council_record":"Elven Council.webp","moonflower_petal":"moonflower_petal.webp","mirror_shard":"mirror_shard.webp","torn_diary_page":"torn_diary_page.webp","memory_fragment_core":"memory_fragment_core.webp"}.items():add(ident,"props/"+path)
    for ident in ("moonbrook_rooftop","council_chamber","memory_corridor","pale_moon_chamber"):add(ident,"backgrounds/"+ident+".webp",fallback="memory_space")
    for n in range(1,9):add("memory_video_"+str(n).zfill(2),"video/memories/memory_"+str(n).zfill(2)+".webm","VIDEO","memory_space",9 if n in (1,4) else 10)
    names=("academy_corridor","moonlit_rooftop","ritual_chamber","collapsing_academy","council_archive","erasure_chamber","lunar_seal","peaceful_rooftop")
    media=Path(os.getenv("CHARACTER_IMAGE_DIR","image"))/"worlds/selene/moonfall"
    for n,name in enumerate(names,1):
        ident="memory_location_"+str(n).zfill(2)
        path="backgrounds/memory_locations/loc_"+str(n).zfill(2)+"_"+name+".jpg"
        webp=path[:-4]+".webp"
        if not (media/path).is_file() and (media/webp).is_file():path=webp
        add(ident,path,fallback="memory_space")
        if (media/path).is_file():chapters[n-1]["memory"]["background"]=ident
    from .asset_variants import presentation_path
    for asset in assets.values():asset["path"]=presentation_path(media,asset["path"])
    from .replacement_media import assets as replacement_assets,visuals as replacement_visuals
    cfg["assets"]=list(replacement_assets(assets).values())
    cfg["visual_events"]=replacement_visuals(cfg["visual_events"])
    from .chapter_one import DEFAULT as CHAPTER_ONE
    cfg["adventure"].setdefault("chapter_one_flow",deepcopy(CHAPTER_ONE))
    from .pacing import policy
    cfg["adventure"].setdefault("pacing",policy(cfg))
    from .story_enrichment import DATA as STORY_BEATS
    cfg["adventure"].setdefault("story_beats",deepcopy(STORY_BEATS))
    cfg["adventure"].setdefault("enrichment_enabled",True)
    cfg["adventure"].setdefault("music_levels",{"master":.85,"music":.45,"ambient":.2,"effects":.22,"narrator":.9,"character":.9,"duck_gain":.35})
    cfg["intro_narration"]={"vi":"Selene trở lại Moonbrook, nơi đã biến mất khỏi bản đồ mới. Một ký ức chưa hoàn chỉnh đang chờ giữa những tàn tích.","en":"Selene returns to Moonbrook, a place missing from modern maps. An incomplete memory waits among its ruins."}
    cfg["chapters"][3]["memory"]["flags"]={"young_selene_warning_seen":True}
    cfg["chapters"][2]["memory"].setdefault("background","council_chamber")
    cfg["chapters"][7]["memory"].setdefault("background","moonbrook_rooftop")
    from .props import editor_config
    from .languages import enrich
    return editor_config(enrich(cfg))
