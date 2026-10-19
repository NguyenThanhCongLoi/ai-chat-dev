"""Chapter navigation, owner-isolated awards and resilient character return."""
import json
from test_worlds import world_client
from test_moonfall import moonfall
from test_world_pacing import first_complete
from character_chat import main,moonfall_store as storage
from character_chat.models import AppSetting,Relationship,RelationshipEvent,Message
from character_chat.adventure import engine

def store(factory,s):
    with factory() as db:
        db.add(AppSetting(key=storage.run_key("alice",s["id"]),value=json.dumps(s)));db.commit()

def test_completed_chapters_can_be_revisited_without_chat_gate(moonfall,monkeypatch):
    client,factory,_=moonfall;monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    s=first_complete();s["attempt_number"]=2
    store(factory,s)
    got=client.get("/v1/moonfall/"+s["id"]).json()
    assert got["has_next"] and got["next_chapter_id"]=="selene_02"
    response=client.post("/v1/moonfall/"+s["id"]+"/act",json={"revision":got["revision"],"request_id":"next","action":"chapter","value":"selene_02"})
    assert response.status_code==200,response.text
    assert response.json()["chapter_id"]=="selene_02"
    chapters=client.get("/v1/moonfall/chapters?character_id=selene").json()["chapters"]
    assert chapters[1]["conditions"]["previous"]==1
    assert chapters[1]["conditions"]["replay"]
    assert chapters[0]["conditions"]["kind"]=="entry"

def test_return_fallback_speaks_as_selene_and_awards_only_once(moonfall,monkeypatch):
    client,factory,_=moonfall;monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    calls=[]
    def broken(*a,**k):
        calls.append(True)
        raise RuntimeError("Provider unavailable")
    monkeypatch.setattr(main,"direct_completion",broken)
    s=first_complete();store(factory,s)
    endpoint="/v1/moonfall/"+s["id"]+"/return-to-chat"
    result=client.post(endpoint,json={"sync_memory":True})
    assert result.status_code==200,result.text
    assert "from_world=1" in result.json()["url"]
    assert not calls, "Return navigation must not call a provider"
    with factory() as db:
        messages=db.query(Message).filter_by(room_id=result.json()["room"]["id"],sender_type="character",character_id="selene").all()
        assert any("Moonfall" in m.text for m in messages)
        rel=db.query(Relationship).filter_by(user_id="alice",character_id="selene",other_character_id=None).one()
        before=(rel.trust,rel.affinity,rel.familiarity)
        assert all(value>0 for value in before)
        assert db.query(RelationshipEvent).filter_by(event_type="world_chapter_completed").count()==1
        assert not db.query(RelationshipEvent).filter_by(user_id="bob").count()
    assert client.post(endpoint,json={"sync_memory":True}).status_code==200
    with factory() as db:
        rel=db.query(Relationship).filter_by(user_id="alice",character_id="selene",other_character_id=None).one()
        assert (rel.trust,rel.affinity,rel.familiarity)==before
        assert db.query(RelationshipEvent).filter_by(event_type="world_chapter_completed").count()==1

def test_preview_award_is_noop(moonfall):
    _,factory,_=moonfall
    from character_chat.adventure.return_chat import award
    s=first_complete();s["admin_preview"]=True
    with factory() as db:
        assert award(db,"alice",s,{"id":"unused"})=={}
        assert not db.query(RelationshipEvent).filter_by(event_type="world_chapter_completed").count()


def test_relationship_reward_respects_cms_cap(moonfall):
    _,factory,_=moonfall
    from character_chat.adventure.return_chat import award
    s=first_complete();s["config"]["relationship_delta_cap"]=.003
    with factory() as db:
        result=award(db,"alice",s,{"id":"unused"})
        assert result and all(0<=v<=.003 for v in result.values())
        db.rollback()
