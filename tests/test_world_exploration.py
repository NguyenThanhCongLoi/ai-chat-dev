"""Ordered discovery survives resume; completed chapters become silent map browsing."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from character_chat.adventure.props import manifest_assets
from test_chapter_one_sequence import gate_ready

def started():
    cfg = seed()
    cfg.setdefault("revision", 1)
    return engine.advance(engine.fresh("alice", "selene", "", cfg, "en", 0), "intro_complete")

def test_gate_first_then_key_then_next_map_and_resume():
    s = started()
    v = view(s, {"name": "Selene"})
    assert [o["id"] for o in v["objects"]] == ["selene_01_old_gate"]
    assert all(p["locked"] for p in v["locations"][1:])
    with pytest.raises(ValueError):
        engine.advance(s, "inspect", "selene_01_collapsed_path")
    with pytest.raises(ValueError):
        engine.advance(s, "go", "outer_ruins")
    s = engine.advance(s, "inspect", "selene_01_old_gate")
    assert any(o["id"] == "selene_01_collapsed_path" for o in view(s, {"name": "Selene"})["objects"])
    s = engine.advance(s, "inspect", "selene_01_collapsed_path")
    s = json.loads(json.dumps(s))
    assert not view(s, {"name": "Selene"})["locations"][1]["locked"]
    s = engine.advance(s, "go", "side_path")
    s = engine.advance(s, "go", "ancient_gate")
    assert not view(s, {"name": "Selene"})["locations"][1]["locked"]

def test_all_chapters_enforce_order_and_preserve_previously_visited_scenes():
    s = started()
    for ch in s["config"]["chapters"]:
        state = deepcopy(s)
        state.update(chapter_id=ch["id"], location=ch["scenes"][0]["id"], visited=[], inspected=[])
        with pytest.raises(ValueError):
            engine.advance(state, "go", ch["scenes"][-1]["id"])
        state["visited"].append(ch["id"] + ":" + ch["scenes"][-1]["id"])
        assert engine.advance(state, "go", ch["scenes"][-1]["id"])["location"] == ch["scenes"][-1]["id"]

def test_completed_admin_chapter_stays_completed_and_review_emits_nothing():
    s = gate_ready()
    for action in ("open_gate", "finish_gate_cinematic", "finish_memory_cinematic"):
        s = engine.advance(s, action)
    s["admin_preview"] = True
    before = deepcopy(s)
    reviewed = engine.select_chapter(s, s["chapter_id"])
    assert reviewed["reviewing"] and reviewed["completed"] and reviewed["phase"] == "explore"
    assert reviewed["completed_chapters"] == before["completed_chapters"]
    for place in engine.chapter(reviewed)["scenes"]:
        reviewed = engine.advance(reviewed, "go", place["id"])
    assert reviewed["events"] == before["events"]
    assert reviewed["memories"] == before["memories"]
    assert not view(reviewed, {"name": "Selene"})["memory_video"]
    assert all(not e["auto_voice"] for e in view(reviewed, {"name": "Selene"})["events"])

def test_initial_manifest_has_future_scene_images_patches_and_story_movies():
    s = started()
    manifest = manifest_assets(s["config"])
    root = Path("image/worlds/selene/moonfall")
    for ch in s["config"]["chapters"]:
        s.update(chapter_id=ch["id"], location=ch["scenes"][0]["id"])
        initial = view(s, {"name": "Selene"})
        urls = {a["url"] for a in initial["assets"].values()}
        assert all((root / manifest[k]["path"]).is_file() for k in initial["chapter_media"])
        for place in ch["scenes"]:
            s["location"] = place["id"]
            output = view(s, {"name": "Selene"})
            if output["embedded_scene"]:
                asset = output["embedded_scene"]["background"]
                assert output["assets"][asset]["url"] in urls
        s["phase"] = "memory"
        if ch["order"] == 8:
            s["pending_ending"] = "remember_me"
        memory = view(s, {"name": "Selene"})["memory_video"]
        if memory:
            assert memory["url"] in urls
        s["phase"] = "explore"

def test_shared_background_is_one_map_but_required_steps_still_advance():
    s = started()
    cfg = s["config"]
    for ch in cfg["chapters"]:
        state = deepcopy(s)
        state.update(chapter_id=ch["id"],location=ch["scenes"][0]["id"],inspected=[],visited=[])
        output = view(state, {"name":"Selene"})
        assert len({p["background"] for p in output["locations"]}) == len(output["locations"])
        assert not output["supporting_cast"]
        # Every original logical stage is represented once, inside a physical map.
        assert {i for p in output["locations"] for i in p["scene_ids"]} == {p["id"] for p in ch["scenes"]}
    for obj in ("selene_01_old_gate", "selene_01_collapsed_path"):
        s=engine.advance(s,"inspect",obj)
    s=engine.advance(s,"go","side_path")
    for obj in ("selene_01_clear_stones","selene_01_footprints","selene_01_arrow_trap"):
        s=engine.advance(s,"inspect",obj)
    assert s["location"]=="ward_aftermath"
    output=view(s,{"name":"Selene"})
    assert len(output["locations"])==3
    assert next(p for p in output["locations"] if p["id"]==s["location"])["name"]=="Forgotten side path"
    with pytest.raises(ValueError):
        engine.advance(s,"go","outer_ruins")

def test_returning_to_map_does_not_append_narration_or_voice_button_entries():
    s = started()
    for obj in ("selene_01_old_gate","selene_01_collapsed_path"):
        s=engine.advance(s,"inspect",obj)
    s=engine.advance(s,"go","side_path")
    count=len(s["events"])
    s=engine.advance(s,"go","ancient_gate")
    s=engine.advance(s,"go","side_path")
    assert len(s["events"])==count
    # Old saved map-name narration is hidden without deleting saved story data.
    engine.emit(s,{"type":"narration","text":engine.scene(s)["title"]})
    output=view(s,{"name":"Selene"})
    assert s["events"][-1]["id"] not in {e["id"] for e in output["events"]}

def test_admin_can_restart_any_chapter_and_chapter_one_at_any_time():
    s=started();s["admin_preview"]=True
    s=engine.advance(s,"inspect","selene_01_old_gate")
    first=engine.advance(s,"chapter","selene_01")
    assert first["id"]==s["id"] and first["admin_preview"]
    assert first["phase"]=="intro" and not first["inspected"] and not first["intro_seen"]
    assert first["attempt_number"]==2
    eighth=engine.advance(first,"chapter","selene_08")
    assert eighth["chapter_id"]=="selene_08" and eighth["phase"]=="explore"
    assert {"silver_pendant","ancient_journal","crystal_fragment"} <= set(eighth["inventory"])
    again=engine.advance(eighth,"chapter","selene_08")
    assert again["attempt_number"]==4 and not again["reviewing"]
    assert not again["inspected"]
    assert s["inspected"]==["selene_01_old_gate"]
