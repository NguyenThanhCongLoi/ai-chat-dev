"""Magic media and VFX survive old CMS snapshots and retain object targets."""
import pytest,json
from pathlib import Path
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from character_chat.adventure.conditions import allows

@pytest.mark.parametrize("number,event,asset",[(3,"MAGIC_SEAL_ACTIVATE","seal_activation"),(6,"VAULT_AWAKEN","deep_vault_awaken"),(7,"MAGIC_SEAL_ACTIVATE","seal_activation")])
def test_solving_chapter_magic_keeps_realtime_effect_without_retired_movie(number,event,asset):
    cfg=seed()
    cfg["visual_events"].pop(event,None)
    s=engine.fresh("alice","selene","",cfg,"en",.5);s["admin_preview"]=True
    s=engine.select_chapter(s,f"selene_{number:02}")
    ch=engine.chapter(s)
    from test_memory_adventure import investigate
    s=investigate(s)
    p=ch["puzzles"][0]
    s=engine.advance(s,"go",p["scene"])
    s=engine.advance(s,"solve",json.dumps({"id":p["id"],"answer":p["solution"]}))
    out=view(s,{"id":"selene","name":"Selene"})
    assert any(e["visual_event"]==event for e in out["events"])
    assert out["visual_events"][event]["cinematic"]==""
    assert asset not in out["chapter_media"]

def test_inspection_vfx_is_targeted_without_awarding_extra_items():
    s=engine.advance(engine.fresh("alice","selene","",seed(),"en",.5),"intro_complete")
    obj=engine.scene(s)["hotspots"][0]
    before=list(s["inventory"])
    s=engine.advance(s,"inspect",obj["id"])
    out=view(s,{"id":"selene","name":"Selene"})
    assert any(e["visual_event"]=="CLUE_DISCOVERED" and e["target_id"]==obj["id"] for e in out["events"])
    if not obj["item"]:assert s["inventory"]==before

def test_cms_explicitly_disabled_magic_video_is_respected():
    from character_chat.adventure.story_enrichment import visuals
    cfg=seed();cfg["visual_events"]["MAGIC_SEAL_ACTIVATE"]["cinematic"]=""
    assert visuals(cfg)["MAGIC_SEAL_ACTIVATE"]["cinematic"]==""
