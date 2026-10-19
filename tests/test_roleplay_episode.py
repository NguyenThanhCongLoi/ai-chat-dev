"""Episode notes remain private, attributed, consent-bound and cheap on repeat."""
import json
import pytest
from test_roleplay_continuity import chat_tools
from test_worlds import world_client
from character_chat import main, roleplay_episode as episodes, roleplay_continuity as continuity
from character_chat.models import AppSetting,Message
from character_chat.schemas import CharacterSpec

BASE="/v1/roleplay/rooms/chat/episode"

def install(monkeypatch):
    calls=[]
    def generate(messages,schema,**kw):
        data=json.loads(messages[-1]["content"]);calls.append(data)
        return episodes.Episode(summary="The user made a promise.",perspective="Selene may value this promise.",
            events=[episodes.StoryEvent(text="The user said they would keep the stone safe.",source_ids=["source"],kind="promise")])
    monkeypatch.setattr(main.llm,"json",generate)
    monkeypatch.setattr(main.llm,"model","test-model")
    return calls

def test_generate_cached_per_actor_and_edit_delete(chat_tools,monkeypatch):
    client,factory,_=chat_tools
    calls=install(monkeypatch)
    r=client.post(BASE,json={"character_id":"selene"})
    assert r.status_code==200,r.text
    assert r.json()["graph"]["nodes"][0]["source_ids"]==["source"]
    assert client.post(BASE,json={"character_id":"selene"}).json()["cached"]
    assert len(calls)==1
    assert client.get(BASE,params={"character_id":"ren"}).json()["episode"] is None
    note=r.json()["episode"]
    edited=client.put(BASE,json={"character_id":"selene","revision":note["revision"],"summary":"A reported promise.","perspective":"Uncertain."})
    assert edited.status_code==200 and edited.json()["episode"]["edited_by_user"]
    assert client.put(BASE,json={"character_id":"selene","revision":note["revision"],"summary":"stale","perspective":""}).status_code==409
    assert client.delete(BASE,params={"character_id":"selene"}).status_code==200
    assert client.get(BASE,params={"character_id":"selene"}).json()["episode"] is None

def test_ownership_consent_and_source_invalidation(chat_tools,monkeypatch):
    client,factory,user=chat_tools
    calls=install(monkeypatch)
    assert client.post(BASE,json={"character_id":"not-a-member"}).status_code==404
    user["id"]="bob"
    assert client.get(BASE,params={"character_id":"selene"}).status_code==404
    user["id"]="alice"
    with factory() as db:
        config=continuity.defaults();config["auto_memory"]=False
        db.add(AppSetting(key=continuity.PREFIX+"chat",value=json.dumps(config)));db.commit()
    assert client.post(BASE,json={"character_id":"selene"}).status_code==409
    assert not calls
    with factory() as db:
        db.get(AppSetting,continuity.PREFIX+"chat").value=json.dumps(continuity.defaults());db.commit()
    assert client.post(BASE,json={"character_id":"selene"}).status_code==200
    with factory() as db:
        db.get(Message,"source").text="Changed source.";db.commit()
    assert client.get(BASE,params={"character_id":"selene"}).json()["episode"] is None

def test_invalid_model_references_not_persisted(chat_tools,monkeypatch):
    client,factory,_=chat_tools
    install(monkeypatch)
    monkeypatch.setattr(main.llm,"json",lambda *a,**kw:episodes.Episode(summary="oops",perspective="",
        events=[episodes.StoryEvent(text="Secret",source_ids=["bob-source"])]))
    assert client.post(BASE,json={"character_id":"selene"}).status_code==503
    with factory() as db:assert db.get(AppSetting,episodes.key("chat","selene")) is None

def test_no_private_lore_or_memory_sent_and_prompt_respects_toggle(chat_tools,monkeypatch):
    client,factory,_=chat_tools
    calls=install(monkeypatch)
    assert client.post(BASE,json={"character_id":"selene"}).status_code==200
    assert set(calls[0])=={"language","character","dialogue"}
    with factory() as db:
        c=CharacterSpec(id="selene",name="Selene")
        ctx=episodes.prompt_context(db,"alice","chat",c,"hello",[])
        assert ctx["episode"]["perspective"]
        assert episodes.prompt_context(db,"bob","chat",c,"hello",[])=={}
        config=continuity.defaults();config["use_memory"]=False
        db.add(AppSetting(key=continuity.PREFIX+"chat",value=json.dumps(config)));db.commit()
        assert episodes.prompt_context(db,"alice","chat",c,"hello",[])=={}

def test_initiative_is_readonly_and_has_cooldown(chat_tools):
    _,factory,_=chat_tools
    with factory() as db:
        for i in range(3):db.add(Message(id="u"+str(i),room_id="chat",sender_type="user",text="hello",created_at=str(i)))
        db.commit()
        c=CharacterSpec(id="selene",name="Selene")
        assert "initiative" in episodes.prompt_context(db,"alice","chat",c,"hello",[])
        assert "initiative" not in episodes.prompt_context(db,"alice","chat",c,"just listen",[])
        db.add(Message(id="extra",room_id="chat",sender_type="user",text="hello"));db.commit()
        assert "initiative" not in episodes.prompt_context(db,"alice","chat",c,"hello",[])

def test_generation_race_does_not_restore_deleted_message(chat_tools,monkeypatch):
    client,factory,_=chat_tools
    install(monkeypatch)
    def generate(*a,**kw):
        with factory() as db:db.delete(db.get(Message,"source"));db.commit()
        return episodes.Episode(summary="Old",perspective="",events=[])
    monkeypatch.setattr(main.llm,"json",generate)
    assert client.post(BASE,json={"character_id":"selene"}).status_code==409
    with factory() as db:assert db.get(AppSetting,episodes.key("chat","selene")) is None

def test_graph_edges_do_not_claim_causation():
    value={"events":[{"text":"A","source_ids":["1"],"kind":"statement"},{"text":"B","source_ids":["2"],"kind":"question"}]}
    assert episodes.graph(value)["edges"]==[{"from":"0","to":"1","relation":"listed_after"}]


def test_source_purge_removes_derived_notes(chat_tools,monkeypatch):
    client,factory,_=chat_tools
    install(monkeypatch)
    assert client.post(BASE,json={"character_id":"selene"}).status_code==200
    with factory() as db:
        main.purge_message_dependents(db,["source"])
        db.commit()
        assert db.get(AppSetting,episodes.key("chat","selene")) is None
