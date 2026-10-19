"""Task-specific guidance and compatibility with published CMS/save snapshots."""
from copy import deepcopy
import json
import pytest
from test_moonfall import moonfall
from test_worlds import world_client
from character_chat.adventure.loader import seed
from character_chat.adventure import engine
from character_chat.adventure.guidance import upgrade,changes,observation

@pytest.mark.parametrize("number",range(1,9))
def test_each_scene_and_object_has_distinct_task_dialogue(number):
    cfg=seed();ch=cfg["chapters"][number-1]
    rows=[]
    for place in ch["scenes"]:
        for raw in place["events"]:
            if raw["type"]=="dialogue":rows.append(ch["localization"][raw["text_key"]]["en"])
        for obj in place["hotspots"]:
            raw=next((e for e in obj["events"] if e["type"]=="dialogue"),None)
            if raw:rows.append(ch["localization"][raw["text_key"]]["en"])
    assert len(rows)==len(set(rows))

def test_upgrade_preserves_cms_edits_and_changes_only_authored_text():
    cfg=seed();baseline=deepcopy(cfg)
    rows=changes();a,b=rows[:2]
    ch=cfg["chapters"][0]
    ch["localization"][a["key"]]=deepcopy(a["old"])
    ch["localization"][b["key"]]={"vi":"Lời tôi biên soạn","en":"My CMS scene text"}
    upgraded=upgrade(cfg)
    assert upgraded["chapters"][0]["localization"][a["key"]]["en"]==baseline["chapters"][0]["localization"][a["key"]]["en"]
    assert upgraded["chapters"][0]["localization"][b["key"]]["en"]=="My CMS scene text"
    for c,original in zip(upgraded["chapters"],baseline["chapters"]):
        for key in ("puzzles","memory","choice","required_inspections","unlock_conditions"):
            if key in original:assert c[key]==original[key]
    assert upgrade(deepcopy(upgraded))==upgraded

def test_hint_targets_missing_local_clue_and_does_not_solve_puzzle():
    s=engine.advance(engine.fresh("alice","selene","",seed(),"en",0),"intro_complete")
    ch=engine.chapter(s)
    s=engine.advance(s,"inspect","selene_01_old_gate")
    s["last_hint"]=0
    before=deepcopy(s["solved"])
    assert engine.hint(s)
    missing=next(o for o in ch["scenes"][0]["hotspots"] if o["id"]=="selene_01_collapsed_path")
    assert s["events"][-1]["text"]==observation(s,missing)
    assert s["solved"]==before
    from character_chat.adventure.exploration import next_object
    for place in ch["scenes"]:
        s=engine.advance(s,"go",place["id"])
        if place["id"]=="outer_ruins":break
        while (target:=next_object(s,place)):
            s=engine.advance(s,"inspect",target[1]["id"])
    s["last_hint"]=0
    assert engine.hint(s)
    obj=next(p for p in ch["scenes"] if p['id']=='outer_ruins')["hotspots"][0]
    assert s["events"][-1]["text"]==observation(s,obj)
    # Inspecting a new clue resets escalation; the next hint starts gently.
    s["hint_level"]=2
    s=engine.advance(s,"inspect",obj["id"])
    assert s["hint_level"]==0

def test_wrong_answer_uses_the_current_puzzle_hint():
    s=engine.advance(engine.fresh("alice","selene","",seed(),"en",0),"intro_complete")
    for place in engine.chapter(s)["scenes"]:
        s=engine.advance(s,"go",place["id"])
        for obj in place["hotspots"]:s=engine.advance(s,"inspect",obj["id"])
    puzzle=engine.chapter(s)["puzzles"][0]
    s=engine.advance(s,"solve",json.dumps({"id":puzzle["id"],"answer":["blood","moon","memory"]}))
    assert s["events"][-1]["text"]==puzzle["hints"][0]
    assert not s["solved"]

def test_translations_cover_all_new_guidance():
    from character_chat.adventure.languages import enrich
    for row in changes():
        assert all(enrich(row["new"]).get(lang) for lang in ("vi","en","ja","zh","ko","my","km"))

def test_existing_save_and_cms_receive_copy_without_reset(moonfall,monkeypatch):
    from character_chat import moonfall_store as storage
    from character_chat.models import AppSetting
    client,factory,_=moonfall
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    cfg=seed()
    for row in changes():
        ch=next(c for c in cfg["chapters"] if c["id"]==row["chapter"])
        ch["localization"][row["key"]]=deepcopy(row["old"])
    s=engine.advance(engine.fresh("alice","selene","",cfg,"en",.5),"intro_complete")
    s=engine.advance(s,"inspect","selene_01_old_gate")
    with factory() as db:
        db.add(AppSetting(key=storage.run_key("alice",s["id"]),value=json.dumps(s,ensure_ascii=False)))
        row=db.get(AppSetting,storage.CONFIG_KEY)
        if row:row.value=json.dumps(cfg,ensure_ascii=False)
        else:db.add(AppSetting(key=storage.CONFIG_KEY,value=json.dumps(cfg,ensure_ascii=False)))
        db.commit()
        assert storage.config(db)["chapters"][0]["localization"][changes()[0]["key"]]["en"]==seed()["chapters"][0]["localization"][changes()[0]["key"]]["en"]
    reply=client.get("/v1/moonfall/"+s["id"])
    assert reply.status_code==200,reply.text
    with factory() as db:
        saved=json.loads(db.get(AppSetting,storage.run_key("alice",s["id"])).value)
    assert saved["revision"]==s["revision"]+1
    for field in ("inspected","solved","stats","choices","memories","events","phase","location","inventory"):
        assert saved[field]==s[field]
    assert saved["config"]["chapters"][0]["localization"][changes()[0]["key"]]["en"]==seed()["chapters"][0]["localization"][changes()[0]["key"]]["en"]
