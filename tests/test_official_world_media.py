"""Official files must prepare completely and never drive story rewards."""
from pathlib import Path
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from character_chat.adventure.props import manifest_assets, media_root
from character_chat.adventure.embedded_scenes import DATA
from character_chat.adventure.story_enrichment import visuals

def test_every_chapter_preparation_resolves_existing_visuals():
    cfg=seed()
    assets=manifest_assets(cfg)
    for ch in cfg["chapters"]:
        s=engine.fresh("alice","selene","",cfg,"en",.5)
        s["admin_preview"]=True
        s=engine.admin_preview_chapter(s,ch["id"])
        out=view(s,{"name":"Selene"})
        for ident in out["chapter_media"]:
            assert (media_root()/assets[ident]["path"]).is_file(),(ch["id"],ident)
        for ident in ("map_world_select","memory_space","chapter_complete_background"):
            assert (media_root()/assets[ident]["path"]).is_file()
    for row in DATA["scenes"].values():
        assert row["path"].startswith("backgrounds/echoes_bg_16x9/")
        assert (media_root()/row["path"]).is_file()

def test_collapse_changes_persisted_scene_after_ceiling_inspection():
    s=engine.fresh("alice","selene","",seed(),"en",.5)
    s["admin_preview"]=True
    s=engine.admin_preview_chapter(s,"selene_04")
    s=engine.advance(s,"go","collapse_passage")
    before=view(s,{"name":"Selene"})
    assert before["embedded_scene"]["background"]=="official_bg_ch04_corridor_aged"
    assert "official_bg_ch04_collapsed_aftermath" in before["chapter_media"]
    from character_chat.adventure.exploration import next_object
    while (target:=next_object(s,engine.scene(s))) and target[1]["id"]!="selene_04_falling_ceiling":
        s=engine.advance(s,"inspect",target[1]["id"])
    s=engine.advance(s,"inspect","selene_04_falling_ceiling")
    after=view(s,{"name":"Selene"})
    assert after["embedded_scene"]["background"]=="official_bg_ch04_collapsed_aftermath"
    assert sum(e["visual_event"]=="ACADEMY_COLLAPSE" for e in s["events"])==1
    reloaded=view(__import__("json").loads(__import__("json").dumps(s)),{"name":"Selene"})
    assert reloaded["embedded_scene"]==after["embedded_scene"]

def test_chapter_seven_has_no_generic_replayed_cinematics():
    mapping=visuals(seed())
    for name in ("MAGIC_SEAL_ACTIVATE","MEMORY_TRIGGER","MEMORY_RECONSTRUCTION_START",
                 "MEMORY_RECONSTRUCTION_END","MEMORY_SPACE_BACKGROUND","CHAPTER_COMPLETE"):
        assert not mapping.get(name,{}).get("cinematic"),name
    assert mapping["PALE_MOON_MANIFESTATION"]["cinematic"]=="story_pale_moon_manifestation"
