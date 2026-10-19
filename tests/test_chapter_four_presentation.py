"""Chapter four's artifacts fit the physical corridor and keep saved progression."""
from copy import deepcopy
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from character_chat.adventure.exploration import same_map

def state():
    s=engine.fresh("alice","selene","",seed(),"en",.5)
    s["admin_preview"]=True
    s=engine.select_chapter(s,"selene_04")
    return engine.advance(s,"go","past")

def test_corridor_has_small_floor_artifacts_and_embedded_echo():
    s=state()
    before=deepcopy(s)
    out=view(s,{"name":"Selene"})
    assert s==before
    assert same_map(s,"past","collapse_passage")
    bg=out["embedded_scene"]["background"]
    from character_chat.adventure.props import manifest_assets
    assert manifest_assets(s["config"])[bg]["path"].endswith("ch04_corridor_aged.webp")
    crystal=next(o for o in out["objects"] if o["id"]=="selene_04_crystal")
    assert crystal["mode"]=="floor" and crystal["width"]<.1 and crystal["y"]>.75
    s=engine.advance(s,"inspect","selene_04_crystal")
    assert "crystal_fragment" in s["inventory"]
    from character_chat.adventure.embedded_scenes import object_layout
    place=next(p for p in engine.chapter(s)["scenes"] if p["id"]=="past")
    echo=object_layout(s,next(o for o in place["hotspots"] if o["id"]=="selene_04_echo"),place)
    assert echo["mode"]=="embedded" and not echo["asset"]
    tablet=next(o for o in view(s,{"name":"Selene"})["objects"] if o["id"]=="selene_04_tablet")
    assert tablet["mode"]=="floor" and tablet["width"]<.1 and tablet["y"]>.75
    s=engine.advance(s,"inspect","selene_04_tablet")
    assert "broken_tablet" in s["inventory"]

def test_return_to_artifact_map_after_collapse_keeps_aftermath():
    s=state()
    s=engine.advance(s,"go","collapse_passage")
    s["inspected"]=[o["id"] for p in engine.chapter(s)["scenes"] if p["id"]=="past" for o in p["hotspots"]]
    s=engine.advance(s,"inspect","selene_04_falling_ceiling")
    s=engine.advance(s,"go","past")
    assert view(s,{"name":"Selene"})["embedded_scene"]["background"]=="official_bg_ch04_collapsed_aftermath"


def test_memory_corridor_uses_existing_runes_and_broken_mirror():
    from character_chat.adventure.embedded_scenes import object_layout
    s=engine.fresh("alice","selene","",seed(),"en",.5)
    s["admin_preview"]=True
    s=engine.select_chapter(s,"selene_06")
    s=engine.advance(s,"go","corridor")
    place=engine.scene(s)
    for obj in place["hotspots"]:
        visual=object_layout(s,obj,place)
        assert visual["mode"]=="embedded" and not visual["asset"]
        assert len(visual["polygon"])>=4
    s=engine.advance(s,"inspect","selene_06_separation")
    s=engine.advance(s,"inspect","selene_06_stops")
    assert {"selene_06_separation","selene_06_stops"}<=set(s["inspected"])
