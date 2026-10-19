"""World demo invariants: ownership, canon, visibility, branches, retries, moderation."""
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from character_chat import world_engine as engine
from character_chat.models import Base,User,Character,CharacterPublication,Memory,Relationship,AppSetting,ModelConfig
from character_chat.schemas import CharacterSpec
import character_chat.main as main

@pytest.fixture
def world_client(monkeypatch):
    db_engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(db_engine);factory=sessionmaker(db_engine,expire_on_commit=False)
    with factory() as db:
        db.add_all([User(id="alice"),User(id="bob")])
        for ident,owner,name in [("selene","alice","Selene Moonbrook"),("ren","alice","Ren Quickshade"),("bob-private","bob","Private NPC"),("shared","bob","Mira Sunpetal")]:
            spec=CharacterSpec(id=ident,name=name,description="A traveller who only knows what they witnessed.")
            db.add(Character(id=ident,user_id=owner,name=name,spec=spec.model_dump_json()))
        db.add(CharacterPublication(character_id="shared",creator_user_id="bob",is_public=1))
        db.add(Memory(id="alice-memory",user_id="alice",character_id="selene",visibility="CHARACTER_PRIVATE",content="A promise from an old chat",pinned=1))
        db.add(Memory(id="bob-memory",user_id="bob",character_id="bob-private",visibility="CHARACTER_PRIVATE",content="BOB_SECRET",pinned=1))
        db.add(Relationship(id="rel",user_id="alice",character_id="selene",trust=.6))
        db.commit()
    def dependency():
        with factory() as db:yield db
    user={"id":"alice"}
    previous_overrides=dict(main.app.dependency_overrides)
    main.app.dependency_overrides[main.db_session]=dependency
    main.app.dependency_overrides[main.current_user]=lambda:user["id"]
    monkeypatch.setenv("WORLD_DEMO_ENABLED","true")
    monkeypatch.setenv("WORLD_SYSTEM_CHARACTERS_ONLY","false")
    monkeypatch.setenv("COMMUNITY_CHARACTER_PUBLICATION_ENABLED","true")
    monkeypatch.delenv("WORLD_MODERATION_API_KEY",raising=False)
    monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    monkeypatch.setattr(main,"ensure_safe_content",lambda *args:None)
    client=TestClient(main.app)
    try:yield client,factory,user
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(previous_overrides)
        db_engine.dispose()

def start(client,**extra):
    r=client.post("/v1/worlds/journeys",json={"character_ids":["selene","ren"],**extra})
    assert r.status_code==200,r.text
    return r.json()

def act(client,c,action,value="",request_id=None,speaker="selene"):
    return client.post("/v1/worlds/journeys/"+c["id"]+"/act",json={"revision":c["revision"],"request_id":request_id or __import__("uuid").uuid4().hex,"action":action,"value":value,"speaker":speaker})

def test_shared_catalog_but_private_characters_and_memories(world_client):
    client,_,user=world_client
    ids={c["id"] for c in client.get("/v1/worlds/characters").json()}
    assert {"selene","ren","shared"}<=ids
    assert "bob-private" not in ids
    assert client.post("/v1/worlds/journeys",json={"character_ids":["bob-private"]}).status_code==404
    assert "BOB_SECRET" not in client.get("/v1/worlds/memories").text
    c=start(client);user["id"]="bob"
    assert client.get("/v1/worlds/journeys/"+c["id"]).status_code==404
    assert client.delete("/v1/worlds/journeys/"+c["id"]).status_code==404
    assert client.post("/v1/worlds/journeys/"+c["id"]+"/checkpoints").status_code==404
    assert not client.get("/v1/worlds/journeys").json()

@pytest.mark.parametrize("language",["vi","en"])
def test_language_stable_ids_hidden_lore_and_idempotency(world_client,language):
    client,_,_=world_client
    c=start(client,language=language)
    assert c["language"]==language and c["location"]=="square"
    assert len(c["lore"])==2
    assert "Someone in the moonlight" not in json.dumps(c) and "Người trong ánh trăng" not in json.dumps(c)
    assert "narrator_prompt" not in json.dumps(c) and '"world": {"id"' in json.dumps(c)
    r=act(client,c,"search",request_id="same-request")
    assert r.status_code==200,r.text
    updated=r.json();assert updated["turn"]==1 and len(updated["clues"])==1
    assert act(client,c,"search",request_id="same-request").json()["turn"]==1
    assert act(client,c,"wait").status_code==409
    assert act(client,updated,"travel","observatory").status_code==422
    assert act(client,updated,"travel","tavern").status_code==200

def test_witnesses_cannot_leak_to_other_actors(world_client):
    client,factory,_=world_client
    c=act(client,start(client),"travel","tavern").json()
    c=act(client,c,"search").json()
    assert c["clues"][0]["scope"]=="witnessed"
    with factory() as db:state=json.loads(db.get(AppSetting,"world_campaign:"+c["id"]).value)["state"]
    assert len(engine.knowledge(state,"selene")[1])==1
    assert not engine.knowledge(state,"ren")[1]
    c=act(client,c,"share",c["clues"][0]["id"]).json()
    with factory() as db:state=json.loads(db.get(AppSetting,"world_campaign:"+c["id"]).value)["state"]
    assert len(engine.knowledge(state,"ren")[1])==1

@pytest.mark.parametrize("mode,trust,memory_count",[("fresh",0,0),("selected",0,1),("continue",60,1)])
def test_memory_modes_are_snapshots(world_client,mode,trust,memory_count):
    client,factory,_=world_client
    c=start(client,memory_mode=mode,memory_ids=["alice-memory","bob-memory"])
    assert c["trust"]["selene"]==trust and len(c["memories"])==memory_count
    assert "BOB_SECRET" not in json.dumps(c)
    with factory() as db:assert db.get(Relationship,"rel").trust==.6

def test_checkpoints_and_branches_preserve_parent(world_client):
    client,_,_=world_client
    c=start(client)
    c=client.post("/v1/worlds/journeys/"+c["id"]+"/checkpoints").json()
    progressed=act(client,c,"search").json()
    branch=client.post("/v1/worlds/journeys/"+c["id"]+"/branch",json={"checkpoint_id":c["checkpoints"][0]["id"]}).json()
    assert branch["id"]!=c["id"] and branch["turn"]==0 and not branch["clues"]
    changed=act(client,branch,"travel","tower").json()
    parent=client.get("/v1/worlds/journeys/"+c["id"]).json()
    assert parent["turn"]==progressed["turn"] and parent["location"]=="square" and len(parent["clues"])==1
    assert changed["location"]=="tower"

def test_free_text_and_publication_fail_closed_without_provider(world_client):
    client,_,user=world_client
    c=start(client)
    assert act(client,c,"say","A harmless question").status_code==503
    assert client.post("/v1/worlds/journeys/"+c["id"]+"/notes",json={"text":"A private note"}).status_code==503
    draft=client.post("/v1/worlds/drafts",json={"title":{"vi":"Thế giới riêng"},"pitch":{"vi":"Khám phá"},"opening":{"vi":"Một đêm mới"}})
    assert draft.status_code==200,draft.text
    world_id=draft.json()["id"]
    assert client.post("/v1/worlds/"+world_id+"/submit").status_code==503
    user["id"]="bob"
    assert world_id not in {w["id"] for w in client.get("/v1/worlds").json()}
    assert client.post("/v1/worlds/"+world_id+"/submit").status_code==404
    assert client.post("/v1/worlds/journeys",json={"world_id":world_id,"character_ids":["shared"]}).status_code==404
    assert client.get("/v1/admin/worlds").status_code==401

def test_publication_requires_admin_review_even_after_moderation(world_client,monkeypatch):
    import httpx
    client,_,user=world_client
    monkeypatch.setenv("WORLD_MODERATION_API_KEY","fixture-key")
    actual=httpx.Client
    def respond(request):return httpx.Response(200,json={"results":[{"flagged":False}]})
    monkeypatch.setattr(httpx,"Client",lambda **kw:actual(transport=httpx.MockTransport(respond),**kw))
    draft=client.post("/v1/worlds/drafts",json={"title":{"vi":"Riêng tư"},"opening":{"vi":"Xin chào"}}).json()
    assert client.post("/v1/worlds/"+draft["id"]+"/submit").json()["status"]=="pending"
    user["id"]="bob"
    assert draft["id"] not in {w["id"] for w in client.get("/v1/worlds").json()}

def test_seed_template_changes_do_not_mutate_running_journey(world_client,monkeypatch):
    client,factory,_=world_client;c=start(client)
    with factory() as db:
        definition=engine.seed();definition["version"]=2;definition["title"]["vi"]="New canon"
        db.add(AppSetting(key="world_template:moonfall",value=json.dumps(definition,ensure_ascii=False)));db.commit()
    assert "moonfall" not in {w["id"] for w in client.get("/v1/worlds").json()}
    assert client.post("/v1/worlds/journeys",json={"world_id":"moonfall","character_ids":["selene"]}).json()["world"]["title"]=="New canon"
    unchanged=client.get("/v1/worlds/journeys/"+c["id"]).json()
    assert unchanged["world"]["version"]==1 and unchanged["world"]["title"]!= "New canon"

def test_dice_failure_and_three_endings_are_rules_not_model_output():
    c=engine.fresh(engine.seed(),[{"id":"a","name":"A"}],"en","fresh",[])
    c,_=engine.advance(c,"travel","forest")
    failed,e=engine.advance(c,"search",speaker="a",roll=lambda:1)
    assert e["roll"]==1 and not failed["clues"]
    c,_=engine.advance(c,"search",speaker="a",roll=lambda:20)
    c,_=engine.advance(c,"travel","square");c,_=engine.advance(c,"search")
    c,_=engine.advance(c,"travel","tower");c,_=engine.advance(c,"search")
    c,_=engine.advance(c,"travel","observatory")
    for ending in ("protect","reveal","seal"):
        done,_=engine.advance(c,"resolve",ending)
        assert done["ending"]["id"]==ending and done["trust"]["a"]>0
    assert c["ending"] is None

def test_feature_flag_defaults_off(world_client,monkeypatch):
    client,_,_=world_client
    monkeypatch.delenv("WORLD_DEMO_ENABLED",raising=False)
    assert client.get("/v1/worlds/config").json()["enabled"] is False
    assert client.get("/v1/worlds").status_code==404


def test_moonrise_memento_is_once_only_and_not_quest_evidence():
    state=engine.fresh(engine.seed(),[{"id":"a","name":"A"}],"en","fresh",[])
    with pytest.raises(ValueError):engine.advance(state,"listen",speaker="a")
    for _ in range(4):state,_=engine.advance(state,"wait")
    rewarded,_=engine.advance(state,"listen",speaker="a")
    assert rewarded["trust"]["a"]==1 and len(rewarded["inventory"])==1
    repeated,_=engine.advance(rewarded,"listen",speaker="a")
    assert repeated["trust"]["a"]==1 and len(repeated["inventory"])==1 and not repeated["clues"]


def test_remove_carried_memory_does_not_delete_chat_source(world_client):
    client,factory,_=world_client
    journey=start(client,memory_mode="selected",memory_ids=["alice-memory"])
    result=client.delete("/v1/worlds/journeys/"+journey["id"]+"/memories/alice-memory")
    assert result.status_code==200 and not result.json()["memories"]
    with factory() as db:assert db.get(Memory,"alice-memory") is not None


def test_invalid_lore_field_is_validation_error(world_client):
    client,_,_=world_client
    response=client.post("/v1/worlds/drafts",json={"title":{"en":"Draft"},"lore":[{"scope":"public","title":[]}]})
    assert response.status_code==422


def test_chapter_report_api_checks_state_and_receipt(world_client):
    client,_,_=world_client
    c=start(client)
    assert act(client,c,"report","witness").status_code==422
    assert act(client,c,"accept","mirror").status_code==422
    c=act(client,c,"accept","witness").json()
    c=act(client,c,"go","tavern").json()
    c=act(client,c,"search",speaker="ren").json()
    c=act(client,c,"go","square").json()
    response=act(client,c,"report","witness",request_id="report-once")
    assert response.status_code==200,response.text
    done=response.json()
    assert done["chapter"]["completed"]==1 and done["trust"]["selene"]==2
    duplicate=act(client,c,"report","witness",request_id="report-once")
    assert duplicate.json()["trust"]["selene"]==2
    assert act(client,done,"report","witness").status_code==422


def test_narrator_receives_only_target_actor_knowledge_and_blocks_output(world_client,monkeypatch):
    import httpx
    client,factory,_=world_client
    c=start(client)
    c=act(client,c,"travel","tavern").json()
    c=act(client,c,"search",speaker="selene").json()
    with factory() as db:
        stored=db.get(AppSetting,"world_campaign:"+c["id"])
        record=json.loads(stored.value)
        record["state"]["world"]["narrator_model_id"]="world-fixture"
        stored.value=json.dumps(record,ensure_ascii=False)
        db.add(ModelConfig(id="world-fixture",name="Fixture",provider="fixture",model_id="fixture",api_base="https://fixture.invalid"))
        db.commit()
    captured=[]
    def completion(messages,*args):
        captured.append(json.loads(messages[-1]["content"]))
        return "BLOCKED_NARRATION"
    monkeypatch.setattr(main,"direct_completion",completion)
    monkeypatch.setattr(main,"credential_for_model",lambda *args:"fixture-only")
    monkeypatch.setenv("WORLD_MODERATION_API_KEY","fixture-only")
    actual=httpx.Client
    monkeypatch.setattr(httpx,"Client",lambda **kw:actual(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={"results":[{"flagged":True}]})),**kw))
    result=act(client,c,"talk","evidence",speaker="ren")
    assert result.status_code==200,result.text
    assert captured and captured[0]["actor"]["id"]=="ren"
    assert not captured[0]["evidence"]
    assert "BLOCKED_NARRATION" not in result.text
    assert result.json()["turn"]==c["turn"]+1
