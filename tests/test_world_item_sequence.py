"""Only one unresolved target is clickable on each map, including admin previews."""
from copy import deepcopy
import pytest
from character_chat.adventure import engine
from character_chat.adventure.exploration import next_object, same_map
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view

@pytest.mark.parametrize("number",range(1,9))
@pytest.mark.parametrize("preview",[False,True])
def test_every_chapter_exposes_one_target_and_rejects_early_clicks(number,preview):
    cfg=seed()
    s=engine.fresh("alice","selene","",cfg,"vi",0)
    s["admin_preview"]=True
    if number==1:
        s=engine.advance(s,"intro_complete")
    else:
        s=engine.select_chapter(s,f"selene_{number:02}")
    s["admin_preview"]=preview
    ch=engine.chapter(s)
    for place in ch["scenes"]:
        s=engine.advance(s,"go",place["id"])
        while (target:=next_object(s,place)):
            obj=target[1]
            output=view(s,{"name":"Selene"})
            assert [o["id"] for o in output["objects"] if o["interactive"]]==[obj["id"]]
            future=next((o for p in ch["scenes"] if same_map(s,p["id"],place["id"])
                         for o in p["hotspots"] if o["id"] not in s["inspected"] and o["id"]!=obj["id"]),None)
            if future:
                before=deepcopy(s)
                with pytest.raises(ValueError):
                    engine.advance(s,"inspect",future["id"])
                assert s==before
            known=set(s["inspected"])
            s=engine.advance(s,"inspect",obj["id"])
            assert set(s["inspected"])-known=={obj["id"]}
    assert set(ch["required_inspections"])<=set(s["inspected"])

@pytest.mark.parametrize("preview",[False,True])
def test_key_is_covered_until_gate_reaction_then_disappears_after_collection(preview):
    s=engine.advance(engine.fresh("alice","selene","",seed(),"vi",0),"intro_complete")
    s["admin_preview"]=preview
    initial=view(s,{"name":"Selene"})
    assert [o["id"] for o in initial["objects"] if o["interactive"]]==["selene_01_old_gate"]
    assert initial["embedded_scene"]["covers"][0]["visible"]
    s=engine.advance(s,"inspect","selene_01_old_gate")
    unlocked=view(s,{"name":"Selene"})
    assert [o["id"] for o in unlocked["objects"] if o["interactive"]]==["selene_01_collapsed_path"]
    assert not unlocked["embedded_scene"]["covers"][0]["visible"]
    assert any(e["type"]=="CHARACTER_SPEECH" and "Nó bị khóa rồi" in e["text"] for e in unlocked["events"])
    s=engine.advance(s,"inspect","selene_01_collapsed_path")
    assert view(s,{"name":"Selene"})["embedded_scene"]["covers"][0]["visible"]
    assert "ancient_key" in s["inventory"]

def test_gate_copy_upgrade_is_multilingual_and_preserves_custom_cms_text():
    from character_chat.adventure.guidance import changes, upgrade
    cfg=seed()
    ch=cfg["chapters"][0]
    latest=[r for r in changes() if r["chapter"]=="selene_01"][-6:]
    for row in latest:
        ch["localization"][row["key"]]=row["old"]
    upgrade(cfg)
    for row in latest:
        assert all(ch["localization"][row["key"]].get(lang) for lang in ("vi","en","ja","zh","ko","my","km"))
        assert ch["localization"][row["key"]]["vi"]==row["new"]["vi"]
    custom={"vi":"CMS custom VI","en":"CMS custom EN"}
    ch["localization"]["selene_01.line.004"]=custom.copy()
    upgrade(cfg)
    assert ch["localization"]["selene_01.line.004"]==custom

def test_elder_elf_copy_is_multilingual_and_updates_old_text():
    from character_chat.adventure.guidance import changes, upgrade
    cfg=seed();key="selene_04.line.019"
    expected=cfg["chapters"][3]["localization"][key]
    assert "older elf" in expected["en"] and "elf lớn tuổi" in expected["vi"]
    assert all(expected.get(lang) for lang in ("vi","en","ja","zh","ko","my","km"))
    row=next(r for r in reversed(changes()) if r["chapter"]=="selene_04" and r["key"]==key)
    cfg["chapters"][3]["localization"][key]=row["old"]
    upgrade(cfg)
    assert cfg["chapters"][3]["localization"][key]==expected
