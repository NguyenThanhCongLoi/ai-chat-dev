"""Visual mapping contracts across all eight chapters, independent of rewards."""
from pathlib import Path
from character_chat.adventure.loader import seed
from character_chat.adventure.engine import fresh
from character_chat.adventure.embedded_scenes import DATA,object_layout,scene_view
from character_chat.adventure.props import hotspot_art,manifest_assets,media_root
from character_chat.adventure.exploration import same_map

def test_all_68_targets_have_real_art_or_reviewed_embedded_regions():
    cfg=seed();assets=manifest_assets(cfg)
    state=fresh("alice","selene","",cfg,"en",.5)
    count=0
    for chapter in cfg["chapters"]:
        state["chapter_id"]=chapter["id"]
        for place in chapter["scenes"]:
            state["location"]=place["id"]
            art=scene_view(state,place)
            assert art and (media_root()/assets[art["background"]]["path"]).is_file()
            from PIL import Image
            with Image.open(media_root()/assets[art["background"]]["path"]) as image:
                assert image.size==(art["width"],art["height"])
            for obj in place["hotspots"]:
                count+=1
                visual={**hotspot_art(obj,place),**object_layout(state,obj,place)}
                assert visual["mode"]!="marker",obj["id"]
                assert all(0<=visual[k]<=1 for k in ("x","y","width","height"))
                if visual["mode"]=="embedded":
                    assert len(visual["polygon"])>=3
                    assert all(0<=v<=1 for p in visual["polygon"] for v in p)
                else:
                    assert (media_root()/assets[visual["asset"]]["path"]).is_file(),obj["id"]
    assert count==68

def test_clock_comparison_returns_to_the_actual_clock_room_not_an_unrelated_background():
    cfg=seed();state=fresh("alice","selene","",cfg,"en",.5);state["chapter_id"]="selene_06"
    chapter=cfg["chapters"][5]
    clock=next(p for p in chapter["scenes"] if p["id"]=="clock_landing")
    assert scene_view(state,clock)["background"]=="replacement_ch06_deep_vault"
    assert same_map(state,"clock_landing","vault")
    assert not same_map(state,"clock_landing","corridor")
    assert "selene_06_midnight" in DATA["hotspots"]
    assert "selene_06_elapsed_time" in DATA["hotspots"]

def test_secret_petal_uses_a_real_petal_prop_instead_of_an_empty_patch_or_silver_leaf():
    from character_chat.adventure.props import inventory_art
    cfg=seed();state=fresh("alice","selene","",cfg,"en",.5);state["chapter_id"]="selene_02"
    garden=cfg["chapters"][1]["scenes"][1]
    petal=next(o for o in garden["hotspots"] if o["id"]=="selene_02_moonflower")
    art=object_layout(state,petal,garden)
    assert art["mode"]=="floor" and art["asset"]=="prop_ch02_petal_under_stone"
    assert petal["optional"]
    assert inventory_art("moonflower_petal",manifest_assets(cfg))==art["asset"]
