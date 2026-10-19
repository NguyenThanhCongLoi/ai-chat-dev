"""Social progression uses saved shared replies, never private cross-character context."""
import json
import pytest
from sqlalchemy import create_engine, text, inspect
from character_chat import character_social as social, engine, main
from character_chat.models import (Character, Room, RoomMember, Message, Memory,
    CharacterSocialState as Edge, CharacterSharedInteraction as Event,
    CharacterSocialKnowledge as Fact, CharacterSocialCanon as Canon)
from character_chat.schemas import CharacterSpec
from test_worlds import world_client
from test_roleplay_continuity import chat_tools

BASE="/v1/roleplay/characters/selene/connections"
def connect(client, **extra):
    r=client.post(BASE,json={"other_character_id":"ren",**extra})
    assert r.status_code==200,r.text
    return r.json()
def path(connection):return "/v1/roleplay/character-connections/"+connection["id"]

def shared_turn(db,index,first="Ren Quickshade, I trust you.",second="I will examine the path.",status="complete"):
    source="social-turn-"+str(index)
    db.add(Message(id=source,room_id="chat",sender_type="user",text="Everyone, work together."))
    for actor,words in (("selene",first),("ren",second)):
        db.add(Message(id=source+"-"+actor,room_id="chat",sender_type="character",
            character_id=actor,text=words,reply_to_message_id=source,finish_status=status))
    db.flush()
    return source

def test_unknown_is_absent_and_private_data_never_becomes_social_context(chat_tools):
    client,factory,_=chat_tools
    assert client.get(BASE).json()==[]
    with factory() as db:
        assert social.prompt_context(db,"alice","selene")["connections"]==[]
        peer=db.get(Character,"ren")
        card=json.loads(peer.spec);card.update(system_prompt="REN_PROMPT_SECRET",description="REN_DESCRIPTION_SECRET",
            scenario="REN_SCENARIO_SECRET",persona_knowledge=["REN_KNOWLEDGE_SECRET"])
        card["identity"]["role"]="treasure hunter";peer.spec=json.dumps(card)
        db.add(Memory(id="ren-private",user_id="alice",character_id="ren",visibility="CHARACTER_PRIVATE",content="REN_MEMORY_SECRET",pinned=1))
        db.add(Room(id="ren-private-room",user_id="alice",name="Private"))
        db.add(Message(id="ren-private-message",room_id="ren-private-room",sender_type="user",text="REN_PRIVATE_CHAT"))
        db.commit()
    connection=connect(client)
    assert connection["state"]=="AWARE" and connection["interaction_count"]==0
    assert connection["reverse"]["state"]=="AWARE"
    assert "trust" not in connection
    assert client.get(path(connection)).json()["id"]==connection["id"]
    with factory() as db:
        # Private cards/biography/memory are absent even in an existing shared room.
        prompt,_=engine.assemble(db,"alice","chat",CharacterSpec(id="selene",name="Selene"),"What do you know of Ren?")
        text_value=json.dumps(prompt)
        assert "treasure hunter" in text_value and "AWARE" in text_value
        for marker in ("REN_PROMPT_SECRET","REN_DESCRIPTION_SECRET","REN_SCENARIO_SECRET","REN_KNOWLEDGE_SECRET","REN_MEMORY_SECRET","REN_PRIVATE_CHAT","BOB_SECRET"):
            assert marker not in text_value
        # Known identity is a learned snapshot; mutable card updates are not silently learned.
        card=json.loads(db.get(Character,"ren").spec);card["identity"]["role"]="UNSHARED_CHANGED_ROLE"
        db.get(Character,"ren").spec=json.dumps(card);db.flush()
        assert "UNSHARED_CHANGED_ROLE" not in json.dumps(social.prompt_context(db,"alice","selene"))

def test_directional_introduction_scope_and_payload_guards(chat_tools):
    client,factory,user=chat_tools
    c=connect(client,mutual=False)
    assert c["reverse"] is None
    for forbidden in ({"state":"MET"},{"trust":100},{"deltas":{"trust":2}}):
        assert client.post(BASE,json={"other_character_id":"ren",**forbidden}).status_code==422
    assert client.post(BASE,json={"other_character_id":"bob-private"}).status_code==404
    with factory() as db:
        assert social.prompt_context(db,"alice","ren")["connections"]==[]
        assert not social.prompt_context(db,"alice","selene",scope="world:other")["connections"]
    user["id"]="bob"
    assert client.get(BASE).status_code==404
    for method,suffix,body in (("get","",None),("delete","",None),("post","/introduce",None),("post","/shared-interaction",{"room_id":"chat","source_message_id":"source"})):
        assert getattr(client,method)(path(c)+suffix,**({"json":body} if body else {})).status_code==404

def test_saved_interactions_progress_and_replays_cannot_change_state(chat_tools):
    client,factory,_=chat_tools;c=connect(client)
    with factory() as db:
        # Greetings and unfinished generations are not a verified meeting.
        db.add(Message(id="greeting",room_id="chat",character_id="selene",sender_type="character",text="Hello."))
        source=shared_turn(db,0,status="partial")
        assert social.record_turn(db,"alice","chat",source)==[]
        db.commit()
    assert client.get(path(c)).json()["state"]=="AWARE"
    for i in range(1,4):
        with factory() as db:
            source=shared_turn(db,i)
            assert len(social.record_turn(db,"alice","chat",source))==1
            assert social.record_turn(db,"alice","chat",source)==[]
            db.commit()
        result=client.get(path(c)).json()
        assert result["state"]==("RELATIONSHIP" if i==3 else "MET")
        assert result["interaction_count"]==i
        assert result["first_met_at"]
        assert client.post(path(c)+"/shared-interaction",json={"room_id":"chat","source_message_id":source}).json()["interaction_count"]==i
    with factory() as db:
        a=social.edge(db,"alice","selene","ren");b=social.edge(db,"alice","ren","selene")
        assert (a.trust,a.affinity,a.respect)==(6,3,3)
        assert (b.trust,b.affinity,b.respect)==(0,0,0)
        context=social.prompt_context(db,"alice","selene")
        assert context["connections"][0]["dynamic_signals"]["trust"]==6
        assert len(context["connections"][0]["shared_history"])==3
        assert db.query(Event).count()==3

def test_forged_receipt_and_missing_participant_cannot_fake_meeting(chat_tools):
    client,factory,_=chat_tools;c=connect(client)
    assert client.post(path(c)+"/shared-interaction",json={"room_id":"bob-chat","source_message_id":"bob-source"}).status_code==404
    assert client.post(path(c)+"/shared-interaction",json={"room_id":"chat","source_message_id":"source","summary":"We met","state":"MET"}).status_code==422
    assert client.post(path(c)+"/shared-interaction",json={"room_id":"chat","source_message_id":"bob-source"}).json()["state"]=="AWARE"
    with factory() as db:
        db.add(Message(id="only-one",room_id="chat",sender_type="character",character_id="selene",reply_to_message_id="source",text="Hello Ren"))
        assert not social.record_turn(db,"alice","chat","source")
        db.commit()
    assert client.get(path(c)).json()["state"]=="AWARE"

def test_canon_is_independent_from_directional_dynamic_history(chat_tools):
    client,factory,_=chat_tools;c=connect(client)
    assert client.put(path(c)+"/canon",json={"text":"They must be partners","revision":0}).status_code in (404,405)
    # Only trusted server/admin-authored canon; no user write endpoint.
    with factory() as db:
        db.add(Canon(id=social.pair_id("alice","selene","ren"),user_id="alice",character_a_id="ren",
            character_b_id="selene",text="Selene and Ren are siblings."))
        db.commit()
    saved=client.get(path(c)).json()
    assert saved["origin"]=="AUTHORED_CANON" and saved["state"]=="RELATIONSHIP"
    assert saved["first_met_at"] is None and saved["interaction_count"]==0
    with factory() as db:
        for i in range(9):
            source=shared_turn(db,i,first="Ren Quickshade, I do not trust you.")
            social.record_turn(db,"alice","chat",source)
        db.commit()
        row=social.edge(db,"alice","selene","ren")
        assert social.label(row)=="rival"
        assert social.label(social.edge(db,"alice","ren","selene"))=="acquaintance"
    current=client.get(path(c)).json()
    assert current["canon"]["text"]=="Selene and Ren are siblings."
    assert current["label"]=="rival"
    assert "siblings" in str(current["reverse"]["canon"])

def test_disconnect_reconnect_and_source_deletion_preserve_history(chat_tools):
    client,factory,_=chat_tools;c=connect(client)
    with factory() as db:
        source=shared_turn(db,1);social.record_turn(db,"alice","chat",source);db.commit()
    disconnected=client.delete(path(c))
    assert disconnected.status_code==200 and not disconnected.json()["active"]
    assert disconnected.json()["interaction_count"]==1 and disconnected.json()["known_facts"]
    assert client.post(path(c)+"/meet").status_code in (404,405)
    assert client.post(path(c)+"/introduce").json()["interaction_count"]==1
    with factory() as db:
        assert db.get(Character,"selene") and db.get(Character,"ren")
        db.delete(db.get(Message,source+"-selene"));db.commit()
        context=social.prompt_context(db,"alice","selene")["connections"][0]
        assert context["interaction_count"]==1 and context["shared_history"]==[]
        social.purge_actor(db,"alice","ren");db.commit()
        assert db.query(Edge).count()==db.query(Fact).count()==db.query(Event).count()==0
        assert db.get(Character,"selene")

def test_ambiguous_mentions_require_explicit_confirmation(chat_tools):
    client,factory,_=chat_tools
    with factory() as db:
        db.query(RoomMember).filter_by(room_id="chat",character_id="ren").delete()
        db.get(Message,"source").text="My friend Ren is here."
        db.commit()
    url="/v1/roleplay/characters/selene/connection-suggestion?room_id=chat&message_id=source"
    assert client.get(url).json()["candidate"]["id"]=="ren"
    assert client.get(BASE).json()==[]  # Suggestion is never an introduction.
    with factory() as db:
        card=CharacterSpec(id="other-ren",name="Ren River")
        db.add(Character(id=card.id,user_id="alice",name=card.name,spec=card.model_dump_json()));db.commit()
    assert client.get(url).json()["candidate"] is None
    with factory() as db:
        db.get(Message,"source").text="@Ren Quickshade, hello";db.commit()
    assert client.get(url).json()["candidate"]["id"]=="ren"
    connect(client)
    assert client.get(url).json()["candidate"] is None

@pytest.mark.parametrize("words",[
    'Ren Quickshade, "I trust you."',
    "Ren Quickshade, I trust you?",
    "I think Ren Quickshade trusts you.",
    "Ren Quickshade, if I trust you, will you help?",
    "Ren Quickshade, I am not saying I trust you.",
    "Ren Quickshade, thank you for betraying me.",
    "Ren Quickshade, I trust you only if you return my money.",
])
def test_uncertain_statements_do_not_change_emotion(words):
    assert social.evaluate("Selene","Ren Quickshade",words)[0]=={}

def test_only_explicit_user_group_creation_can_start_a_meeting(chat_tools,monkeypatch):
    client,factory,_=chat_tools;c=connect(client)
    monkeypatch.setattr(main,"message_speech_info",lambda *a,**k:{})
    assert client.post(path(c)+"/meet").status_code in (404,405)
    with factory() as db:assert db.query(Room).filter_by(user_id="alice").count()==1
    response=client.post("/v1/rooms",json={"character_ids":["selene","ren"]})
    assert response.status_code==200,response.text
    room=response.json()
    assert set(room["character_ids"])=={"selene","ren"} and room["id"]!="chat"
    with factory() as db:
        assert social.edge(db,"alice","selene","ren").interaction_count==0
        assert social.edge(db,"alice","ren","selene").interaction_count==0
        assert social.prompt_context(db,"alice","ren")["connections"][0]["known_facts"]
        assert db.query(Message).filter_by(room_id=room["id"],sender_type="user").count()==0

def test_normal_generation_records_actual_two_speakers_automatically(chat_tools,monkeypatch):
    client,factory,_=chat_tools
    monkeypatch.setenv("JEV_ENABLED","false")
    monkeypatch.setattr(main,"analyze_turn",lambda *a:None)
    monkeypatch.setattr(main,"message_speech_info",lambda *a,**kw:{})
    monkeypatch.setattr(main.llm,"chat_with_meta",lambda *a,**k:("I will help.",{"actual_model":"mock","primary_model":"mock"}))
    response=client.post("/v1/rooms/chat/messages",json={"message":"Everyone, please introduce yourselves."})
    assert response.status_code==200,response.text
    assert len(response.json()["responses"])==2
    with factory() as db:
        a=social.edge(db,"alice","selene","ren");assert social.state(a)=="MET" and a.interaction_count==1
        replies=db.query(Message).filter_by(room_id="chat",sender_type="character").all()
        assert len({m.reply_to_message_id for m in replies})==1 and replies[0].reply_to_message_id
        assert db.query(Event).count()==1

def test_additive_migration_preserves_legacy_messages(tmp_path,monkeypatch):
    from character_chat import db as database
    target=create_engine("sqlite:///"+str(tmp_path/"legacy.sqlite"))
    with target.begin() as connection:
        connection.execute(text("CREATE TABLE messages (id VARCHAR PRIMARY KEY,room_id VARCHAR NOT NULL,sender_type VARCHAR NOT NULL,character_id VARCHAR,text TEXT NOT NULL,sources TEXT NOT NULL,created_at VARCHAR NOT NULL)"))
        connection.execute(text("INSERT INTO messages VALUES ('old','old-room','user',NULL,'original','[]','2020')"))
    monkeypatch.setattr(database,"engine",target)
    database.init_db();database.init_db()
    assert "reply_to_message_id" in {c["name"] for c in inspect(target).get_columns("messages")}
    with target.connect() as connection:
        assert connection.execute(text("SELECT text,reply_to_message_id FROM messages WHERE id='old'")).one()==("original",None)
    target.dispose()

@pytest.mark.parametrize("partial",[False,True])
def test_stream_progress_requires_two_completed_saved_replies(chat_tools,monkeypatch,partial):
    client,factory,_=chat_tools
    monkeypatch.setenv("JEV_ENABLED","false")
    monkeypatch.setattr(main,"analyze_turn",lambda *a:None)
    monkeypatch.setattr(main,"message_speech_info",lambda *a,**kw:{})
    def generate(*a,**kw):
        yield "delta","I can help with the path."
        yield "complete",{"actual_model":"mock","finish_status":"partial" if partial else "complete"}
    monkeypatch.setattr(main,"stream_roleplay_answer",generate)
    with client.stream("POST","/v1/rooms/chat/messages/stream",json={"message":"Everyone, say hello.","speaker_mode":"everyone"}) as response:
        body="".join(response.iter_text())
    assert response.status_code==200 and body.count("event: character_message")==2,body
    with factory() as db:
        row=social.edge(db,"alice","selene","ren")
        if partial:assert row is None and db.query(Event).count()==0
        else:assert row.first_met_at and row.interaction_count==1 and db.query(Event).count()==1

def test_clamps_and_reciprocal_private_prompt_boundary(chat_tools):
    client,factory,_=chat_tools;connect(client)
    with factory() as db:
        row=social.edge(db,"alice","selene","ren")
        row.trust=99;row.affinity=99;row.respect=99
        source=shared_turn(db,"clamp");social.record_turn(db,"alice","chat",source);db.commit()
        assert (row.trust,row.affinity,row.respect)==(100,100,100)
        prompt,_=engine.assemble(db,"alice","chat",CharacterSpec(id="ren",name="Ren"),"What do you know of Selene?")
        assert "A promise from an old chat" not in str(prompt)
        assert "BOB_SECRET" not in str(prompt)
