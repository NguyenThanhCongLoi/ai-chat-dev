"""Full deterministic arc, spoiler firewall, four endings, optional media and save/resume."""
from copy import deepcopy
import json
import pytest
from character_chat.adventure.loader import seed
from character_chat.adventure import engine
from character_chat.adventure.conditions import allows
from character_chat.adventure.schema import validate
from character_chat.adventure.knowledge import context


def investigate(s, optional=True):
    from character_chat.adventure.exploration import next_object
    ch=engine.chapter(s)
    for place in ch["scenes"]:
        s=engine.advance(s,"go",place["id"])
        while True:
            target=next_object(s,place)
            if not target or (target[1]["optional"] and not optional):break
            s=engine.advance(s,"inspect",target[1]["id"])
    return s


def play_to_final(optional=True):
    cfg=validate(seed())
    s=engine.fresh("alice","selene","",cfg,"en",.5)
    s=engine.advance(s,"intro_complete")
    for index,ch in enumerate(cfg["chapters"]):
        assert s["chapter_id"]==ch["id"]
        s=investigate(s,optional)
        for puzzle in ch["puzzles"]:
            s=engine.advance(s,"go",puzzle["scene"])
            s=engine.advance(s,"solve",json.dumps({"id":puzzle["id"],"answer":puzzle["solution"]}))
        assert engine.ready(s)
        if index==7:return s
        choice=ch["choice"]["options"][2]
        s=engine.advance(s,"choice",choice["id"])
        if s["phase"]=="gate_ready":s=engine.advance(s,"open_gate");s=engine.advance(s,"finish_gate_cinematic")
        while s["phase"]=="memory":s=engine.advance(s,"continue")
        assert s["completed"]
        s=engine.select_chapter(s,cfg["chapters"][index+1]["id"])
    raise AssertionError()

@pytest.mark.parametrize("ending",["remember_me","let_me_forget","new_keeper","between_memory_and_moonlight"])
def test_all_eight_chapters_and_four_endings(ending):
    s=play_to_final()
    if ending=="between_memory_and_moonlight":
        assert allows(s["config"]["adventure"]["hidden_ending"],s)
        s["ending_offer_at"]=0;choice="remember_without_becoming"
    else:choice=s["config"]["chapters"][7]["choice"]["options"][["remember_me","let_me_forget","new_keeper"].index(ending)]["id"]
    s=engine.advance(s,"choice",choice)
    assert s["ending"] is None and s["phase"]=="confirm"
    s=engine.advance(s,"confirm_ending")
    while s["phase"]=="memory":s=engine.advance(s,"continue")
    assert s["ending"]==ending and len(s["completed_chapters"])==8
    assert ("M08" in s["core_memories"])==(ending=="between_memory_and_moonlight")
    assert len(s["core_memories"])==(8 if ending=="between_memory_and_moonlight" else 7)
    roundtrip=json.loads(json.dumps(s))
    assert roundtrip["ending"]==ending

def test_hidden_ending_requires_more_than_a_stat():
    s=play_to_final(optional=False)
    s["stats"]["understanding"]=100
    assert not allows(s["config"]["adventure"]["hidden_ending"],s)
    s["ending_offer_at"]=0
    with pytest.raises(ValueError):engine.advance(s,"choice","remember_without_becoming")

def test_bad_puzzle_no_rewards_and_future_lore_not_in_context():
    s=engine.fresh("alice","selene","",seed(),"en",0)
    s=engine.advance(s,"intro_complete")
    with pytest.raises(ValueError):engine.select_chapter(s,"selene_08")
    ch=engine.chapter(s);p=ch["puzzles"][0]
    with pytest.raises(ValueError):engine.advance(s,"solve",json.dumps({"id":p["id"],"answer":p["solution"]}))
    known=json.dumps(context(s,{"name":"Selene"}))
    assert "Pale Moon" not in known and "memory separation" not in known.lower()
    assert "hidden_ending" not in known and chr(34)+"solution"+chr(34)+":" not in known

def test_optional_reward_is_idempotent():
    s=engine.fresh("alice","selene","",seed(),"en",0)
    s=engine.advance(s,"intro_complete")
    ident=engine.scene(s)["hotspots"][0]["id"]
    s=engine.advance(s,"inspect",ident);inventory=list(s["inventory"]);event_ids=[e["id"] for e in s["events"]]
    s=engine.advance(s,"inspect",ident)
    assert inventory==s["inventory"]
    assert event_ids==[e["id"] for e in s["events"]]

from test_moonfall import moonfall
from test_worlds import world_client
from character_chat import moonfall_store as storage,main
from character_chat.models import AppSetting,Memory

def test_v2_http_arc_privacy_cms_and_memory(moonfall,monkeypatch):
    client,factory,user=moonfall
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    monkeypatch.setattr(main,"direct_completion",lambda *a,**k:"Selene remembers the events we actually discovered together.")
    cms=client.get("/v1/admin/moonfall").json()["config"]
    cms["adventure"]["pacing"]["enabled"]=False  # This test exercises the full arc, not pacing.
    assert cms["schema_version"]==2
    assert client.put("/v1/admin/moonfall",json=cms).status_code==200
    s=client.post("/v1/moonfall",json={"character_id":"selene","content_language":"en"}).json()
    assert s["engine_version"]==2
    ident=s["id"]
    def act(action,value=""):
        nonlocal s
        response=client.post("/v1/moonfall/"+ident+"/act",json={"revision":s["revision"],"request_id":"v2-"+str(s["revision"]),"action":action,"value":value})
        assert response.status_code==200,response.text
        s=response.json()
        assert "hidden_ending" not in s and "config" not in s
    act("language","vi")
    assert s["content_language"]=="vi"
    act("language","en")
    act("intro_complete")
    for n,ch in enumerate(cms["chapters"]):
        for place in ch["scenes"]:
            act("go",place["id"])
            for obj in place["hotspots"]:
                if not obj["optional"]:act("inspect",obj["id"])
        for puzzle in ch["puzzles"]:
            act("go",puzzle["scene"])
            act("solve",json.dumps({"id":puzzle["id"],"answer":puzzle["solution"]}))
        assert not any(c.get("unexpected") for c in s["choices"])
        act("choice",ch["choice"]["options"][0]["id"])
        if n==7:act("confirm_ending")
        if s["phase"]=="gate_ready":act("open_gate");act("finish_gate_cinematic")
        while s["phase"]=="memory":act("continue")
        assert s["completed"]
        if n==0:
            before=s["revision"]
            r=client.post("/v1/moonfall/"+ident+"/reflection")
            assert r.status_code==200,r.text
            s=r.json();assert s["reflection"]
            r=client.post("/v1/moonfall/"+ident+"/return-to-chat",json={"sync_memory":True})
            assert r.status_code==200,r.text
            s=client.get("/v1/moonfall/"+ident).json()
            with factory() as db:assert db.query(Memory).filter_by(user_id="alice",type="world_shared").count()==1
        if n<7:act("chapter",cms["chapters"][n+1]["id"])
    assert s["ending"]["id"]=="remember_me"
    assert len(s["completed_chapters"])==8
    assert client.post("/v1/moonfall/"+ident+"/chronicle").status_code==200
    user["id"]="bob"
    assert client.get("/v1/moonfall/"+ident).status_code==404
    assert client.post("/v1/moonfall/"+ident+"/reflection").status_code==404
    user["id"]="alice"
    with factory() as db:assert storage.shared_memories(db,"alice","selene")

def test_admin_preview_unlocks_all_chapters_without_publishing(moonfall,monkeypatch):
    from character_chat.models import UserAccount
    client,factory,user=moonfall
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    with factory() as db:
        cfg=storage.config(db)
        cfg["entry_gate"]["min_meaningful_turns"]=99
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg)
        db.add(UserAccount(user_id="alice",username="fixture-admin",display_name="Admin",password_hash="not-a-real-password",is_admin=1,status="active"));db.commit()
    r=client.get("/v1/moonfall/chapters?character_id=selene")
    assert all(c["available"] for c in r.json()["chapters"])
    r=client.post("/v1/moonfall",json={"character_id":"selene","chapter_id":"selene_08","content_language":"en"})
    assert r.status_code==200,r.text
    s=r.json();assert s["admin_preview"] and s["chapter_id"]=="selene_08"
    assert {"silver_pendant","ancient_journal","crystal_fragment"}<=set(s["inventory"])
    assert client.post("/v1/moonfall/"+s["id"]+"/return-to-chat",json={"sync_memory":True}).status_code==409
    back=client.post("/v1/moonfall/"+s["id"]+"/return-to-chat",json={"sync_memory":False})
    assert back.status_code==200,back.text
    assert "/role-play-ai?" in back.json()["url"] and not back.json()["synced"]
    with factory() as db:
        assert not db.query(Memory).filter_by(user_id="alice",type="world_shared").count()
        assert storage.user_runs(db,"alice")==[]
        db.get(UserAccount,"alice").is_admin=0;db.commit()
    assert client.get("/v1/moonfall/"+s["id"]).status_code==403
    assert not any(c["available"] for c in client.get("/v1/moonfall/chapters?character_id=selene").json()["chapters"])
    assert client.post("/v1/moonfall",json={"character_id":"selene","chapter_id":"selene_08","content_language":"en","preview":True}).status_code==403

def test_conversation_knows_visible_objects_without_revealing_contents():
    s=engine.advance(engine.fresh("alice","selene","",seed(),"en",0),"intro_complete")
    ctx=context(s,{"name":"Selene"})
    assert ctx["scene_title"]=="Ancient Gate"
    assert ctx["visible_objects"] and not ctx["known_lore"]
    assert all(not o["inspected"] for o in ctx["visible_objects"])
    assert all(set(o)=={"id","title","inspected","position"} for o in ctx["visible_objects"])
    assert not engine.hint(s,manual=False)


def test_free_chat_uses_llm_and_does_not_append_canned_hint(moonfall,monkeypatch):
    client,_,_=moonfall
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    calls=[]
    def completion(messages,*args,**kwargs):
        calls.append(messages)
        return "We can talk here. The gate lock is to our left; take your time."
    monkeypatch.setattr(main,"direct_completion",completion)
    run=client.post("/v1/moonfall",json={"character_id":"selene","content_language":"en"}).json()
    def act(action,value=""):
        nonlocal run
        response=client.post("/v1/moonfall/"+run["id"]+"/act",json={
            "revision":run["revision"],"request_id":"talk-"+str(run["revision"]),"action":action,"value":value})
        assert response.status_code==200,response.text
        run=response.json()
    act("intro_complete")
    previous={e["id"] for e in run["events"]}
    act("say","Where is the gate lock? Can we just talk?")
    fresh=[e for e in run["events"] if e["id"] not in previous]
    assert [e["type"] for e in fresh]==["USER","CHARACTER_SPEECH"]
    assert calls and "visible_objects" in calls[0][-1]["content"]
    assert fresh[-1]["text"].startswith("We can talk here.")

def test_cinematic_finish_and_skip_persist_same_memory_without_voice_overlap():
    s=engine.advance(engine.fresh("alice","selene","",seed(),"en",0),"intro_complete")
    ch=engine.chapter(s)
    for place in ch["scenes"]:
        s=engine.advance(s,"go",place["id"])
        for obj in place["hotspots"]:
            if allows(obj.get("requires"),s):s=engine.advance(s,"inspect",obj["id"])
    for puzzle in ch["puzzles"]:
        s=engine.advance(s,"go",puzzle["scene"])
        s=engine.advance(s,"solve",json.dumps({"id":puzzle["id"],"answer":puzzle["solution"]}))
    s=engine.advance(s,"choice",ch["choice"]["options"][1]["id"])
    assert s["phase"]=="gate_ready"
    s=engine.advance(s,"open_gate");s=engine.advance(s,"finish_gate_cinematic")
    assert s["phase"]=="memory"
    ids={e["id"] for e in s["events"]}
    done=engine.advance(s,"finish_memory_cinematic")
    assert done["phase"]=="complete" and done["core_memories"]==["M01"]
    after=[e for e in done["events"] if e["id"] not in ids]
    assert any(e["type"]=="CHARACTER_SPEECH" for e in after)
    assert all(e["voice_role"] is None for e in after if e["type"]=="NARRATION")
    with pytest.raises(ValueError):engine.advance(done,"finish_memory_cinematic")


def test_scripted_speech_and_manual_hints_do_not_repeat():
    s=engine.advance(engine.fresh("alice","selene","",seed(),"en",0),"intro_complete")
    raw=engine.scene(s)["events"][-1]
    count=len(s["events"])
    engine.emit(s,raw)
    assert len(s["events"])==count
    assert engine.hint(s)
    count=len(s["events"]);s["last_hint"]=0
    assert not engine.hint(s)
    assert len(s["events"])==count

def test_transparent_derivatives_and_archived_sources_support_old_manifests():
    from pathlib import Path
    from PIL import Image
    from character_chat.adventure.asset_variants import VARIANTS,presentation_path
    root=Path("image/worlds/selene/moonfall")
    for original,variant in VARIANTS.items():
        assert presentation_path(root,original)==variant
        with Image.open(root/variant) as image:
            assert image.mode=="RGBA"
            alpha=image.getchannel("A")
            assert alpha.getextrema()[0]==0 and alpha.getextrema()[1]>240
            assert alpha.getpixel((0,0))<10
    assert presentation_path(root,"characters/custom.webp")=="characters/custom.webp"

def test_return_after_chapter_eight_survives_optional_llm_failure(moonfall,monkeypatch):
    client,factory,_=moonfall
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    s=play_to_final()
    s=engine.advance(s,"choice",engine.chapter(s)["choice"]["options"][0]["id"])
    s=engine.advance(s,"confirm_ending")
    s=engine.advance(s,"finish_memory_cinematic")
    with factory() as db:
        db.add(AppSetting(key=storage.run_key("alice",s["id"]),value=json.dumps(s,ensure_ascii=False)))
        db.commit()
    def unavailable(*args,**kwargs):raise RuntimeError("mock provider offline")
    monkeypatch.setattr(main,"direct_completion",unavailable)
    response=client.post("/v1/moonfall/"+s["id"]+"/return-to-chat",json={"sync_memory":True})
    assert response.status_code==200,response.text
    assert response.json()["synced"] and response.json()["room"]["id"]
    with factory() as db:
        assert db.query(Memory).filter_by(user_id="alice",type="world_shared").count()==8

def test_archived_background_paths_still_resolve():
    from pathlib import Path
    from character_chat.adventure.asset_variants import SOURCE_ALIASES,presentation_path
    root=Path("image/worlds/selene/moonfall")
    for source,replacement in SOURCE_ALIASES.items():
        assert presentation_path(root,source)==replacement
        assert (root/replacement).is_file()

def test_new_props_cover_every_hotspot_and_preserve_old_save_state():
    from character_chat.adventure.props import DATA
    from character_chat.adventure.projection import view
    from pathlib import Path
    cfg=seed()
    expected={o["id"] for c in cfg["chapters"] for p in c["scenes"] for o in p["hotspots"]}
    assert set(DATA["hotspots"])<=expected and len(DATA['hotspots'])==34
    new={o['id'] for c in cfg['chapters'] for p in c['scenes'] for o in p['hotspots'] if '.expanded.' in next((e.get('text_key','') for e in o['events'] if e.get('text_key')),'')}
    assert expected-set(DATA['hotspots'])==new
    names=set(DATA["items"].values())|{p["asset"] for p in DATA["hotspots"].values()}|set(DATA.get("reserved_art",{}))
    sources={p.stem for p in Path("image/worlds/selene/moonfall/props").iterdir() if p.is_file() and p.suffix.lower() in {".webp",".png"}}
    # Unmapped uploads are allowed while the author prepares future assets.
    assert {r["asset"] for r in DATA["hotspots"].values()}<=names
    assert all((Path("image/worlds/selene/moonfall/props/prepared")/(n+".webp")).is_file() for n in names)
    # An existing snapshot has no new presentation asset rows.
    cfg["assets"]=[a for a in cfg["assets"] if not a["id"].startswith("prop_")]
    s=engine.fresh("alice","selene","",cfg,"en",0)
    s["admin_preview"]=True
    for chapter in cfg["chapters"]:
        s=engine.admin_preview_chapter(s,chapter["id"])
        if s["phase"]=="intro":s=engine.advance(s,"intro_complete")
        for place in chapter["scenes"]:
            s=engine.advance(s,"go",place["id"])
            before=deepcopy(s)
            output=view(s,{"id":"selene","name":"Selene"})
            assert s==before
            for obj in output["objects"]:
                if obj['id'] in new:
                    assert obj['mode'] in ('marker','embedded') and not obj['asset']
                    continue
                expected=DATA["hotspots"][obj["id"]]
                if obj["mode"]=="embedded":
                    assert not obj["asset"] and len(obj["polygon"])>=3
                else:
                    assert obj["asset"] in output["assets"]
                assert output["embedded_scene"]["background"] in output["assets"]
                assert 0<=obj["x"]<1 and obj["x"]+obj["width"]<=1
                assert 0<=obj["y"]<1 and obj["y"]+obj["height"]<=1
                from character_chat.adventure.exploration import same_map
                origin=next(p for p in chapter["scenes"] if any(o["id"]==obj["id"] for o in p["hotspots"]))
                assert same_map(s,origin["id"],place["id"])

def test_four_new_inventory_icons_keep_alpha_and_are_available_in_old_saves(moonfall,monkeypatch):
    import numpy as np
    from PIL import Image
    from character_chat.adventure.props import DATA,manifest_assets,inventory_art
    from pathlib import Path
    client,_,_=moonfall
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    assert not DATA["missing_inventory_art"] and len(DATA["items"])==14
    assets=manifest_assets(seed())
    root=Path("image/worlds/selene/moonfall/props")
    for name in ("moon_rune","moonstone","witch_symbol","seal_stone"):
        source=root/(name+".png");target=root/"prepared"/(name+".webp")
        with Image.open(target) as after:
            assert after.mode=="RGBA"
            if source.exists():
                with Image.open(source) as before:
                    assert before.size==after.size
                    assert np.array_equal(np.asarray(before.getchannel("A")),np.asarray(after.getchannel("A")))
            assert after.getpixel((0,0))[3]==0
            assert np.asarray(after.getchannel("A")).max()==255
        assert inventory_art(name,assets)=="prop_"+name
        response=client.get("/v1/moonfall/assets/prop_"+name)
        assert response.status_code==200
        import io
        with Image.open(io.BytesIO(response.content)) as served:
            assert served.mode=="RGBA" and served.getpixel((0,0))[3]==0


def test_story_translations_cover_all_chapters_and_preserve_cms_overrides():
    from character_chat import moonfall
    from character_chat.adventure.languages import enrich,catalog
    catalog.cache_clear()
    cfg=seed();checked=[]
    def walk(value):
        if isinstance(value,dict):
            if "vi" in value and "en" in value and isinstance(value["vi"],str) and value["vi"] and value["en"]:
                assert value.get('vi') and value.get('en')
                # Old config snapshots/events containing only VI/EN also resolve.
                old={k:value[k] for k in ("vi","en")}
                for lang in moonfall.LANGUAGES:
                    assert moonfall.localized(old,lang)
                    expected=lang if lang in ('vi','en') or enrich(old).get(lang) else 'en'
                    assert moonfall.language_of(old,lang)==expected
                assert enrich({**old,"ja":"CMS custom text"})["ja"]=="CMS custom text"
                checked.append(value)
            else:
                for item in value.values():walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
    walk(cfg)
    assert len(checked)>300


def test_action_sounds_follow_new_story_events_without_replaying_inspection():
    from character_chat.adventure.projection import view
    cfg=seed();s=engine.fresh("alice","selene","",cfg,"en",.5)
    s=engine.advance(s,"intro_complete")
    assert any(e.get("action_sound")=="footstep" for e in s["events"])
    # Use a real paper item from Chapter 2 in isolated admin preview.
    s["admin_preview"]=True;s=engine.select_chapter(s,"selene_02")
    place=next(p for p in engine.chapter(s)["scenes"] if any(o["item"]=="torn_diary_page" for o in p["hotspots"]))
    s=engine.advance(s,"go",place["id"])
    obj=next(o for o in place["hotspots"] if o["item"]=="torn_diary_page")
    s=engine.advance(s,"inspect","selene_02_journal")
    s=engine.advance(s,"inspect",obj["id"])
    assert any(e.get("action_sound")=="turn page" for e in s["events"])
    count=len(s["events"])
    s=engine.advance(s,"inspect",obj["id"])
    assert len(s["events"])==count
    for lang in ("en","vi","ja","zh","ko","my","km"):
        s["content_language"]=lang
        projected=view(s,{"id":"selene","name":"Selene"})
        assert any(e.get("action_sound")=="turn page" for e in projected["events"])
