"""Moonfall Chapter 1: firewall, CMS, privacy, voice roles and explicit memory bridge."""
import json
from copy import deepcopy
import pytest
import httpx
from character_chat import moonfall as story, moonfall_store as storage, main, engine, jev
from character_chat.models import AppSetting,Memory,ModelConfig,Character,Room,RoomMember,Message,Relationship
from character_chat.schemas import CharacterSpec
from test_worlds import world_client

@pytest.fixture
def moonfall(world_client,monkeypatch,tmp_path):
    monkeypatch.setenv("DATA_DIR",str(tmp_path/"data"))
    client,factory,user=world_client
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","false")
    monkeypatch.setenv("WORLD_INTRO_PREPARE_ON_SAVE","false")
    main.app.dependency_overrides[main.docs_auth]=lambda:None
    monkeypatch.setattr(jev,"enabled",lambda task:True)
    cfg=story.seed();cfg["entry_gate"]["min_meaningful_turns"]=0
    cfg.update(model_id="mf-chat",tts_model_id="mf-tts",narrator_voices={"en":"narr-en","vi":"narr-vi"})
    with factory() as db:
        db.add(AppSetting(key=storage.CONFIG_KEY,value=json.dumps(cfg,ensure_ascii=False)))
        db.add(ModelConfig(id="mf-chat",name="Dialogue",model_id="test-model",provider="test",api_base="https://example.test/v1",enabled=1))
        db.add(ModelConfig(id="mf-tts",name="Speech",model_id="tts-model",provider="test",api_base="https://example.test/v1",enabled=1))
        db.add(AppSetting(key="model_profile:mf-tts",value=json.dumps({"purposes":["tts"],"tts_default_voice":"selene-en"})))
        card=CharacterSpec(id="selene",name="Selene Moonbrook",system_prompt="SELENE_ORIGINAL_PERSONALITY",tts_voice_en="selene-en",tts_voice_vi="selene-vi")
        db.get(Character,"selene").spec=card.model_dump_json();db.commit()
    monkeypatch.setattr(main,"credential_for_model",lambda *args:"fixture-not-real")
    monkeypatch.setattr(main,"message_speech_info",lambda *a,**kw:{})
    return client,factory,user

def start(client,lang="en"):
    r=client.post("/v1/moonfall",json={"character_id":"selene","content_language":lang})
    assert r.status_code==200,r.text
    return r.json()

def act(client,s,action,value="",**kwargs):
    return client.post("/v1/moonfall/"+s["id"]+"/act",json={"revision":s["revision"],"request_id":kwargs.pop("request_id","act-"+str(s["revision"])),"action":action,"value":value,**kwargs})

def complete(client,s):
    s=act(client,s,"intro_complete").json();s=act(client,s,"go","outer_ruins").json()
    s=act(client,s,"inspect","rune").json();s=act(client,s,"inspect","statue").json()
    assert s["completed"]
    return s

def test_seed_and_config_schema():
    cfg=story.validate(story.seed())
    assert sum(c["enabled"] for c in cfg["chapters"])==1
    assert len(cfg["chapters"])==8 and cfg["bgm"]=="shared:"
    for edit in ("path","future","threshold","locale","scope"):
        bad=deepcopy(cfg)
        if edit=="path":bad["assets"][0]["path"]="../../secrets.vault.json"
        elif edit=="future":bad["chapters"][1]["enabled"]=True
        elif edit=="threshold":bad["relationship_delta_cap"]=9
        elif edit=="locale":bad["intro_narration"]={"vi":"xin chao"}
        else:bad["chapters"][0]["reward"]["scope"]="PUBLIC_ALL"
        with pytest.raises(ValueError):story.validate(bad)

def test_entry_is_meaningful_completed_chat_not_raw_spam(moonfall):
    client,factory,_=moonfall
    with factory() as db:
        cfg=storage.config(db);cfg["entry_gate"]["min_meaningful_turns"]=2
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg,ensure_ascii=False)
        db.add(Room(id="solo",user_id="alice",name="Selene"))
        db.add(RoomMember(id="solo-s",room_id="solo",character_id="selene"))
        for i,text in enumerate(["hello"]*4+["I hope we can talk about the strange dreams I had last night."]*3+["Would you walk with me through the old library and tell me what you find interesting?"]):
            db.add(Message(id="input-"+str(i),room_id="solo",sender_type="user",text=text))
            db.add(Message(id="reply-"+str(i),room_id="solo",sender_type="character",character_id="selene",reply_to_message_id="input-"+str(i),text="Welcome.",finish_status="partial" if i==7 else "complete"))
        db.commit()
    status=client.get("/v1/moonfall/eligibility?character_id=selene").json()
    assert not status["eligible"] and "trust" not in status
    assert client.post("/v1/moonfall",json={"character_id":"selene","content_language":"en"}).status_code==409
    with factory() as db:
        db.get(Message,"reply-7").finish_status="complete";db.commit()
    assert client.get("/v1/moonfall/eligibility?character_id=selene").json()["eligible"]
    with factory() as db:
        spec=CharacterSpec(id="selene",name="Selene Moonbrook")
        prompt,_=engine.assemble(db,"alice","solo",spec,"What shall we do next?")
        assert "optional_world_invitation" in db.query(main.PromptTrace).order_by(main.PromptTrace.created_at.desc()).first().layers
        assert "The runes at Moonfall" in str(prompt) and "Elarion" not in str(prompt)

def test_owner_state_snapshot_and_typed_outputs(moonfall):
    client,factory,user=moonfall
    s=start(client)
    assert [e["type"] for e in s["events"]]==["NARRATION","CHARACTER_SPEECH","CHARACTER_THOUGHT"]
    assert [e["voice_role"] for e in s["events"]]==["NARRATOR","CHARACTER",None]
    assert not s["intro_seen"] and s["journal"]==[]
    assert "world_trust" not in s and "config" not in s and "canon" not in s
    assert client.post("/v1/moonfall",json={"character_id":"ren","content_language":"en"}).status_code==404
    user["id"]="bob"
    for suffix in ("","/act","/return-to-chat","/voice/"+s["events"][0]["id"]):
        result=client.get("/v1/moonfall/"+s["id"]) if not suffix else client.post("/v1/moonfall/"+s["id"]+suffix,json={})
        assert result.status_code==404,result.text
    assert client.get("/v1/moonfall").json()["runs"]==[]

def test_clue_gates_replay_no_farming_and_complete(moonfall):
    client,factory,_=moonfall;s=start(client)
    assert act(client,s,"go","gate").status_code==422
    assert act(client,s,"inspect","rune").status_code==422
    changed=act(client,s,"go","outer_ruins",request_id="one")
    assert changed.status_code==200
    assert act(client,s,"go","outer_ruins",request_id="one").json()["revision"]==changed.json()["revision"]
    assert act(client,s,"hint",request_id="different").status_code==409
    s=act(client,changed.json(),"inspect","rune").json()
    with factory() as db:before=json.loads(db.get(AppSetting,storage.run_key("alice",s["id"])).value)["world_trust"]
    s=act(client,s,"inspect","rune").json()
    with factory() as db:
        persisted=json.loads(db.get(AppSetting,storage.run_key("alice",s["id"])).value)
        assert persisted["world_trust"]==before
        assert persisted["discovered"]==["rune"]
    assert not s["completed"] and s["memories"]==[]
    s=act(client,s,"inspect","statue").json()
    assert s["completed"] and len(s["memories"])==1
    assert client.get("/v1/moonfall/"+s["id"]).json()["completed"]
    with factory() as db:assert db.query(Memory).filter_by(type="world_shared").count()==0

def test_hint_escalates_and_cooldown_is_enforced():
    cfg=story.seed();s=story.fresh("alice","selene","",cfg,"en",.2)
    s=story.advance(s,"go","outer_ruins")
    assert story.hint(s) and s["hint_level"]==1
    first=s["events"][-1]
    assert first["type"]=="CHARACTER_THOUGHT" and first["voice_role"] is None
    assert not story.hint(s)
    s["last_hint"]=0;assert story.hint(s) and s["hint_level"]==2
    s["last_hint"]=0;assert story.hint(s) and s["hint_level"]==3
    assert "Inspect" in story.localized(s["events"][-1]["text"],"en")
    s["last_hint"]=0
    assert not story.hint(s,manual=False)  # not stalled or idle yet
    s["last_progress"]=0
    assert story.hint(s,manual=False)

def test_free_chat_resolves_current_object_without_future_spoilers(moonfall,monkeypatch):
    client,factory,_=moonfall;s=start(client)
    with factory() as db:
        row=db.get(AppSetting,storage.run_key("alice",s["id"]));raw=json.loads(row.value)
        raw["config"]["chapters"][1]["reward"]["fact"]["en"]="FUTURE_MENTOR_SECRET_ELARION"
        row.value=json.dumps(raw,ensure_ascii=False);db.commit()
    captures=[]
    def answer(messages,*args):
        captures.append(json.dumps(messages))
        return "The dust is undisturbed. Let's look closely."
    monkeypatch.setattr(main,"direct_completion",answer)
    s=act(client,s,"go","outer_ruins").json()
    response=act(client,s,"say","Can you explain the rune on this stone and what its pulse means?")
    assert response.status_code==200,response.text
    s=response.json()
    assert "rune" in {c["id"] for c in s["journal"]}
    assert "SELENE_ORIGINAL_PERSONALITY" in captures[0]
    assert "FUTURE_MENTOR_SECRET" not in captures[0] and "Elarion" not in captures[0]
    assert "A promise from an old chat" not in captures[0] and "BOB_SECRET" not in captures[0]
    assert s["events"][-1]["type"]=="CHARACTER_SPEECH"
    assert "FUTURE_MENTOR_SECRET" not in client.get("/v1/moonfall/"+s["id"]).text

def test_failed_provider_and_moderation_do_not_save_progress(moonfall,monkeypatch):
    client,_,_=moonfall;s=start(client);s=act(client,s,"go","outer_ruins").json()
    monkeypatch.setattr(main,"direct_completion",lambda *a,**k:(_ for _ in ()).throw(RuntimeError("provider")))
    result=act(client,s,"say","What do the runes suggest about the path ahead?")
    assert result.status_code==503
    assert client.get("/v1/moonfall/"+s["id"]).json()["revision"]==s["revision"]
    monkeypatch.setattr(main,"ensure_safe_content",lambda *a:(_ for _ in ()).throw(ValueError("blocked")))
    assert act(client,s,"say","blocked").status_code==422
    assert client.get("/v1/moonfall/"+s["id"]).json()["revision"]==s["revision"]

def test_only_unlocked_selected_memory_returns_to_correct_chat(moonfall):
    client,factory,_=moonfall;s=start(client)
    endpoint="/v1/moonfall/"+s["id"]+"/return-to-chat"
    assert client.post(endpoint,json={"sync_memory":True}).status_code==409
    with factory() as db:
        before=db.query(Relationship).filter_by(user_id="alice",character_id="selene").first().trust
    s=complete(client,s)
    assert client.post(endpoint,json={"sync_memory":False}).status_code==200
    with factory() as db:assert db.query(Memory).filter_by(type="world_shared").count()==0
    result=client.post(endpoint,json={"sync_memory":True});assert result.status_code==200,result.text
    assert client.post(endpoint,json={"sync_memory":True}).status_code==200
    with factory() as db:
        memories=db.query(Memory).filter_by(type="world_shared").all()
        assert len(memories)==1 and memories[0].character_id=="selene" and memories[0].user_id=="alice"
        assert memories[0].visibility=="CHARACTER_PRIVATE" and "Elarion" not in memories[0].content
        assert db.query(Relationship).filter_by(user_id="alice",character_id="selene").first().trust==before
        for actor,expected in (("selene",True),("ren",False)):
            room=Room(id="normal-"+actor,user_id="alice",name="Ordinary chat");db.add(room);db.flush()
            prompt,_=engine.assemble(db,"alice",room.id,CharacterSpec(id=actor,name=actor),"What happened at Moonfall?")
            assert ("newly awakened runes at Moonfall" in str(prompt))==expected

def test_secret_reward_never_syncs_or_leaks_into_journal(moonfall):
    client,factory,_=moonfall
    with factory() as db:
        cfg=storage.config(db);cfg["chapters"][0]["reward"]["scope"]="SECRET"
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg,ensure_ascii=False);db.commit()
    s=complete(client,start(client))
    assert s["memories"]==[]
    assert client.post("/v1/moonfall/"+s["id"]+"/return-to-chat",json={"sync_memory":True}).status_code==200
    with factory() as db:assert db.query(Memory).filter_by(type="world_shared").count()==0

def test_cms_isolated_versioned_and_validated(moonfall):
    client,factory,_=moonfall
    before=client.get("/v1/admin/moonfall").json()["config"]
    s=start(client)
    changed=deepcopy(before);changed["intro_narration"]["en"]="CMS_EDITED_NARRATOR"
    changed["hints"]["idle_seconds"]=45
    r=client.put("/v1/admin/moonfall",json=changed);assert r.status_code==200,r.text
    assert r.json()["revision"]==before["revision"]+1
    assert client.put("/v1/admin/moonfall",json=changed).status_code==409
    assert "CMS_EDITED_NARRATOR" not in client.get("/v1/moonfall/"+s["id"]).text  # immutable playthrough
    bad=deepcopy(r.json());bad["assets"][0]["path"]="https://evil.test/asset.webp"
    assert client.put("/v1/admin/moonfall",json=bad).status_code==422
    with factory() as db:
        assert db.get(AppSetting,"ai_world_config") is None
        assert db.get(AppSetting,"project_prompt:response") is None
        assert "SELENE_ORIGINAL_PERSONALITY" in db.get(Character,"selene").spec

def mock_audio(monkeypatch):
    captured=[];original=httpx.AsyncClient
    def respond(request):
        captured.append(json.loads(request.content));return httpx.Response(200,headers={"content-type":"audio/mpeg"},content=b"ID3-fixture-audio")
    monkeypatch.setattr(httpx,"AsyncClient",lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    async def selected(*args):return "selene-en" if args[3]=="en" else "selene-vi"
    monkeypatch.setattr(main,"selected_speech_voice",selected)
    return captured

@pytest.mark.parametrize("language",["vi","en"])
def test_distinct_voice_roles_and_never_read_thoughts(moonfall,monkeypatch,language):
    client,_,_=moonfall;s=start(client,language);requests=mock_audio(monkeypatch)
    for e in s["events"]:
        r=client.post("/v1/moonfall/"+s["id"]+"/voice/"+e["id"],json={"voice_language":language})
        assert r.status_code==(422 if e["type"]=="CHARACTER_THOUGHT" else 200),r.text
    assert [r["voice"] for r in requests]==["narr-"+language,"selene-"+language]
    assert s["events"][2]["text"] not in [r["input"] for r in requests]

def test_unsupported_content_language_needs_explicit_voice_choice(moonfall,monkeypatch):
    client,_,_=moonfall;s=start(client,"ja");requests=mock_audio(monkeypatch)
    event=s["events"][0];endpoint="/v1/moonfall/"+s["id"]+"/voice/"+event["id"]
    assert not s["voice_supported"] and s["content_language"]=="ja" and s["story_language"]=="ja"
    assert client.post(endpoint,json={}).status_code==422
    assert client.post(endpoint,json={"voice_language":"en"}).status_code==422
    assert requests==[]
    assert client.post(endpoint,json={"voice_language":"vi","explicit_user_choice":True}).status_code==200
    assert requests[0]["input"]==story.seed()["intro_narration"]["vi"]
    assert client.get("/v1/moonfall/"+s["id"]).json()["content_language"]=="ja"

def test_assets_are_safe_public_media_with_missing_file_fallback(moonfall,monkeypatch,tmp_path):
    client,_,_=moonfall
    monkeypatch.setenv("CHARACTER_IMAGE_DIR",str(tmp_path))
    assert client.get("/v1/moonfall/assets/moonfall_intro").status_code==404
    assert client.get("/v1/moonfall/assets/not_in_manifest").status_code==404
    s=start(client)
    assert set(s["assets"]) and "moonfall_past" not in s["assets"]
    assert "Narrator" not in json.dumps(s["assets"])  # never expose hidden story scripts

def test_selene_reuses_existing_reaction_elf_sheet(moonfall):
    client,factory,_=moonfall
    from character_chat.bundled_expressions import sheet_for
    with factory() as db:
        spec=main.spec(db.get(Character,"selene"))
        key,path=sheet_for(spec)
        assert key=="elf" and path.name=="elf.webp"
    result=client.get("/v1/characters/selene/expression/surprised")
    assert result.status_code==200 and result.headers["content-type"].startswith("image/")
    assert len(result.content)>100

def test_forged_memory_type_cannot_bypass_world_unlock(moonfall):
    client,factory,_=moonfall
    from character_chat.retrieval import retrieve_memories
    with factory() as db:
        db.add(Memory(id="forged",user_id="alice",character_id="selene",type="world_shared",visibility="CHARACTER_PRIVATE",content="FORGED_FUTURE_MEMORY",pinned=1))
        db.commit()
        assert not any(m.id=="forged" for m in retrieve_memories(db,"alice","selene","any","Moonfall"))
        db.add(Room(id="ordinary",user_id="alice",name="Private"))
        db.flush()
        prompt,_=engine.assemble(db,"alice","ordinary",CharacterSpec(id="selene",name="Selene Moonbrook"),"Tell me about Moonfall")
        assert "FORGED_FUTURE_MEMORY" not in str(prompt)

def test_hidden_reward_title_and_flagged_clue_are_not_public():
    cfg=story.seed();cfg["chapters"][0]["reward"]["scope"]="SECRET"
    cfg["chapters"][0]["reward"]["title"]={"vi":"HIDDEN_REWARD","en":"HIDDEN_REWARD"}
    cfg["chapters"][0]["clues"][2]["unlock_condition"]="future_flag"
    s=story.fresh("alice","selene","",cfg,"en",.8)
    s=story.advance(s,"go","outer_ruins");s=story.advance(s,"inspect","rune")
    s=story.advance(s,"go","gate")
    with pytest.raises(ValueError):story.advance(s,"inspect","inscription")
    assert story.projection(s,{})["objects"]==[]
    s=story.advance(s,"go","outer_ruins");s=story.advance(s,"inspect","statue")
    assert "HIDDEN_REWARD" not in json.dumps(story.projection(s,{}))

def test_clue_reward_does_not_claim_unseen_inscription():
    s=story.fresh("alice","selene","",story.seed(),"en",.6)
    s=story.advance(s,"go","outer_ruins")
    s=story.advance(s,"inspect","rune")
    s=story.advance(s,"inspect","statue")
    assert s["completed"] and "inscription" not in s["discovered"]
    assert "inscription" not in s["memories"][0]["fact"]["en"].lower()
    assert s["memories"][0]["scope"]=="NORMAL_CHAT_SHARED"


def test_cinematic_registry_is_presentation_only():
    cfg=story.seed()
    assert story.validate(cfg)
    bad=deepcopy(cfg);bad["visual_events"]["WORLD_INTRO"]["cinematic"]="not_an_asset"
    with pytest.raises(ValueError):story.validate(bad)
    old=story.fresh("alice","selene","",cfg,"en",.6)
    no_movies=deepcopy(old)
    for event in no_movies["config"]["visual_events"].values():event.pop("cinematic",None)
    for state in (old,no_movies):
        state=story.advance(state,"go","outer_ruins")
        state=story.advance(state,"inspect","rune")
        state=story.advance(state,"inspect","statue")
        assert state["completed"] and len(state["memories"])==1
        assert "deep_vault_awaken" not in story.projection(state,{})["assets"]

def test_narrator_voice_catalog_uses_selected_provider_without_exposing_key(moonfall,monkeypatch):
    client,factory,_=moonfall
    calls=[]
    async def catalog(base,key):
        calls.append((base,key))
        return [{"id":"voice-vi","name":"Narrator VI","language":"vi-VN","gender":"female"},{"id":"voice-en","name":"Narrator EN","language":"en-US","gender":"male"}]
    monkeypatch.setattr(main,"vbee_voices",catalog)
    with factory() as db:
        db.add(ModelConfig(id="draft-tts",name="Other provider",model_id="speech",provider="test",api_base="https://draft.example/v1",enabled=1))
        db.add(AppSetting(key="model_profile:draft-tts",value=json.dumps({"purposes":["tts"]})))
        db.commit()
    response=client.get("/v1/admin/moonfall/voices?model_id=draft-tts")
    assert response.status_code==200,response.text
    assert response.json()["model"]=="draft-tts"
    assert len(response.json()["voices"])==2
    assert calls==[("https://draft.example/v1","fixture-not-real")]
    assert "fixture-not-real" not in response.text
    with factory() as db:assert storage.config(db)["tts_model_id"]=="mf-tts"
    assert client.get("/v1/admin/moonfall/voices?model_id=mf-chat").status_code==503
    assert client.get("/v1/admin/moonfall/voices?model_id=unknown").status_code==503
    monkeypatch.setattr(main,"credential_for_model",lambda *args:"")
    assert client.get("/v1/admin/moonfall/voices?model_id=mf-tts").status_code==503


def test_narrator_voice_catalog_requires_admin(moonfall):
    client,_,_=moonfall
    main.app.dependency_overrides.pop(main.docs_auth)
    try:
        assert client.get("/v1/admin/moonfall/voices").status_code==401
    finally:main.app.dependency_overrides[main.docs_auth]=lambda:None

def test_chapter_picker_shows_locked_chapters_and_owner_only(moonfall,monkeypatch):
    client,factory,user=moonfall
    with factory() as db:
        cfg=storage.config(db);cfg["entry_gate"]["min_meaningful_turns"]=2
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg);db.commit()
    response=client.get("/v1/moonfall/chapters?character_id=selene")
    assert response.status_code==200
    result=response.json()
    assert len(result["chapters"])==8
    assert result["chapters"][0]["lock_reason"]=="continue_chat"
    assert not any(c["available"] for c in result["chapters"])
    assert all(c["lock_reason"]=="coming_soon" for c in result["chapters"][1:])
    assert "world_trust" not in response.text and "canon" not in response.text
    with factory() as db:
        cfg=storage.config(db);cfg["entry_gate"]["min_meaningful_turns"]=0
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg);db.commit()
    assert client.get("/v1/moonfall/chapters?character_id=selene").json()["chapters"][0]["available"]
    monkeypatch.setenv("WORLD_DEMO_ENABLED","false")
    result=client.get("/v1/moonfall/chapters?character_id=selene").json()
    assert not result["enabled"] and all(c["lock_reason"]=="feature_disabled" for c in result["chapters"])
    user["id"]="bob"
    assert client.get("/v1/moonfall/chapters?character_id=selene").status_code==404

def test_home_atlas_is_private_read_only_and_uses_system_catalog(moonfall,monkeypatch):
    client,factory,user=moonfall
    names=["Liost","Nguyễn Vũ","Merr","Ruby","Kim Anh","Trịnh Khải Nguyên",
           "Aurelion Voss","Selene Moonbrook","Mira Sunpetal","Ren Quickshade","Lyra Ashveil"]
    sources=[CharacterSpec(id="source-"+str(i),preset_type="public-"+str(i),name=name) for i,name in enumerate(names)]
    monkeypatch.setattr(main,"effective_presets",lambda db:sources+[sources[7],CharacterSpec(id="hidden",preset_type="hidden",name="Unpublished NPC",category="entertainment")])
    with factory() as db:
        before=(db.query(Character).count(),db.query(AppSetting).count())
    response=client.get("/v1/moonfall/hub")
    assert response.status_code==200,response.text
    atlas=response.json()
    assert len(atlas["characters"])==11
    lit=[c for c in atlas["characters"] if c["unlocked"]]
    assert len(lit)==1 and lit[0]["character_id"]=="selene"
    assert "BOB_SECRET" not in response.text and all("trust" not in c for c in atlas["characters"])
    with factory() as db:
        assert before==(db.query(Character).count(),db.query(AppSetting).count())
    user["id"]="bob"
    atlas=client.get("/v1/moonfall/hub").json()
    assert not any(c["unlocked"] for c in atlas["characters"])
    assert all(c["character_id"] is None for c in atlas["characters"])
    user["id"]="alice"
    with factory() as db:
        cfg=storage.config(db);cfg["entry_gate"]["min_meaningful_turns"]=2
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg);db.commit()
    assert not any(c["unlocked"] for c in client.get("/v1/moonfall/hub").json()["characters"])
    assert client.get("/v1/moonfall/hub/assets/not-a-manifest-file").status_code==404

def test_hub_media_is_public_range_enabled_and_has_no_private_progress(moonfall):
    client,_,_=moonfall
    public=client.get("/v1/moonfall/hub/presentation")
    assert public.status_code==200
    assert set(public.json())=={"background","intro","standard_intro"}
    for clip in public.json()["intro"]:
        response=client.get(clip["url"],headers={"Range":"bytes=0-127"})
        assert response.status_code==206
        assert len(response.content)==128
        assert response.headers["content-type"].startswith("video/webm")
        assert response.headers["accept-ranges"]=="bytes"
        assert response.headers["cache-control"]=="public, max-age=300"

def test_intro_cms_seven_languages_timing_and_version(moonfall):
    client,_,_=moonfall
    endpoint="/v1/admin/moonfall/hub-narration"
    cfg=client.get(endpoint).json()
    assert len(cfg["cues"])==10
    assert set(cfg["cues"][0]["text"])=={"vi","en","zh","ja","ko","my","km"}
    assert cfg["cues"][0]["start"]==0
    bad=deepcopy(cfg);del bad["cues"][0]["text"]["km"]
    assert client.put(endpoint,json=bad).status_code==422
    bad=deepcopy(cfg);bad["cues"][1]["start"]=2
    assert client.put(endpoint,json=bad).status_code==422
    updated=client.put(endpoint,json=cfg)
    assert updated.status_code==200,updated.text
    assert client.put(endpoint,json=cfg).status_code==409
    assert client.get("/v1/moonfall/hub").json()["narration"]["revision"]==cfg["revision"]+1

def test_intro_voice_uses_cms_provider_and_reuses_cache(moonfall,monkeypatch,tmp_path):
    client,_,_=moonfall
    monkeypatch.setenv("DATA_DIR",str(tmp_path))
    captured=[];original=httpx.AsyncClient
    def respond(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,headers={"content-type":"audio/mpeg"},content=b"fixture-audio")
    monkeypatch.setattr(httpx,"AsyncClient",lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    url="/v1/moonfall/hub/narration/intro_door?language=vi"
    assert client.get(url).status_code==409
    assert captured==[]
    assert client.post("/v1/admin/moonfall/hub-narration/prepare").json()["ready"]
    for _ in range(2):
        r=client.get(url);assert r.status_code==200,r.text
        assert r.content==b"fixture-audio"
    assert len(captured)==20 and captured[0]["voice"]=="narr-vi"
    assert "cánh cửa" in captured[0]["input"]
    assert client.get("/v1/moonfall/hub/narration/not-a-cue").status_code==404
    assert client.get("/v1/moonfall/hub/narration/intro_door?language=xx").status_code==422
    saved=client.get("/v1/admin/moonfall/hub-narration").json()
    saved["cues"][0]["text"]["vi"]="Một câu chuyện mới đang chờ bạn."
    assert client.put("/v1/admin/moonfall/hub-narration",json=saved).status_code==200
    assert client.get(url).status_code==409
    assert client.post("/v1/admin/moonfall/hub-narration/prepare").json()["ready"]
    assert client.get(url).status_code==200
    assert len(captured)==21
    main.app.dependency_overrides.pop(main.docs_auth,None)
    assert client.get("/v1/admin/moonfall/hub-narration").status_code==401

def test_intro_prepare_materializes_both_languages_once(moonfall,monkeypatch,tmp_path):
    client,_,_=moonfall
    monkeypatch.setenv("DATA_DIR",str(tmp_path))
    captured=[];original=httpx.AsyncClient
    def respond(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200,content=b"prepared-narration",headers={"content-type":"audio/mpeg"})
    monkeypatch.setattr(main.httpx,"AsyncClient",lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    for _ in range(2):
        result=client.post("/v1/admin/moonfall/hub-narration/prepare")
        assert result.status_code==200,result.text
        assert result.json()["ready"]
        assert len(result.json()["results"])==20
    assert len(captured)==20
    assert {item["voice"] for item in captured}=={"narr-en","narr-vi"}

def test_intro_save_prepares_audio_and_version_changes_on_voice(moonfall,monkeypatch,tmp_path):
    client,factory,_=moonfall
    monkeypatch.setenv("DATA_DIR",str(tmp_path))
    monkeypatch.setenv("WORLD_INTRO_PREPARE_ON_SAVE","true")
    monkeypatch.setattr(main,"Session",factory)
    calls=[];original=httpx.AsyncClient
    def respond(request):
        data=json.loads(request.content);calls.append(data)
        return httpx.Response(200,content=data["voice"].encode(),headers={"content-type":"audio/mpeg"})
    monkeypatch.setattr(main.httpx,"AsyncClient",lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    endpoint="/v1/admin/moonfall/hub-narration"
    cfg=client.get(endpoint).json()
    cfg["cues"][0]["text"]["vi"]="Nội dung mới được chuẩn bị trước."
    assert client.put(endpoint,json=cfg).status_code==200
    assert len(calls)==20
    old=client.get("/v1/moonfall/hub/narration-config").json()["audio_version"]
    world=client.get("/v1/admin/moonfall").json()["config"]
    world["narrator_voices"]["vi"]="new-voice"
    assert client.put("/v1/admin/moonfall",json=world).status_code==200
    assert len(calls)==30 # Ten VI lines changed; EN remains cached.
    new=client.get("/v1/moonfall/hub/narration-config").json()["audio_version"]
    assert old!=new
    url="/v1/moonfall/hub/narration/intro_door?language=vi&v="
    assert client.get(url+old).status_code==409
    r=client.get(url+new)
    assert r.status_code==200 and r.content==b"new-voice"
    assert "no-cache" in r.headers["cache-control"]
    assert len(calls)==30 # Viewing never calls TTS.

def test_cms_editorial_changes_do_not_use_conversation_moderation(moonfall,monkeypatch):
    client,_,_=moonfall
    calls=[]
    def reject(value,*args,**kwargs):
        calls.append(value)
        raise ValueError("fixture moderation rejection")
    monkeypatch.setattr(main,"ensure_safe_content",reject)
    cfg=client.get("/v1/admin/moonfall").json()["config"]
    cfg["narrator_voices"]["vi"]="voice-only-change"
    r=client.put("/v1/admin/moonfall",json=cfg)
    assert r.status_code==200,r.text
    intro=client.get("/v1/admin/moonfall/hub-narration").json()
    intro["music_gain"]=.4
    r=client.put("/v1/admin/moonfall/hub-narration",json=intro)
    assert r.status_code==200,r.text
    assert calls==[]
    intro=r.json();intro["cues"][0]["text"]["vi"]="Changed authored narration."
    r=client.put("/v1/admin/moonfall/hub-narration",json=intro)
    assert r.status_code==200,r.text
    cfg=client.get("/v1/admin/moonfall").json()["config"]
    cfg["chapters"][0]["title"]["vi"]="Chương biên tập trong CMS"
    r=client.put("/v1/admin/moonfall",json=cfg)
    assert r.status_code==200,r.text
    assert r.json()["chapters"][0]["title"]["vi"]=="Chương biên tập trong CMS"
    invalid=r.json();invalid["chapters"][0]["id"]="invalid-chapter"
    assert client.put("/v1/admin/moonfall",json=invalid).status_code==422
    invalid_intro=client.get("/v1/admin/moonfall/hub-narration").json()
    invalid_intro["cues"][0]["end"]=-1
    assert client.put("/v1/admin/moonfall/hub-narration",json=invalid_intro).status_code==422
    assert calls==[]
