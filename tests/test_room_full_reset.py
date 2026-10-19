"""Room reset deletes only the requesting owner's experience and preserves authoring."""
import json
import pytest
from character_chat import main,moonfall_store as storage
from character_chat.models import (AppSetting,Character,Memory,AIRequestLog,Message,MessageSpeech,
 CharacterSocialState,CharacterSocialKnowledge,CharacterSocialCanon,CharacterSharedInteraction,
 VoiceEvent,Room,RoomMember,CharacterReaction,CharacterRating,CharacterUsage)
from test_worlds import world_client
from test_moonfall import moonfall,start,complete

def test_room_delete_resets_world_memories_social_and_archive_for_owner_only(moonfall):
    client,factory,user=moonfall
    s=complete(client,start(client))
    returned=client.post("/v1/moonfall/"+s["id"]+"/return-to-chat",json={"sync_memory":True}).json()
    room=returned["room"]["id"]
    with factory() as db:
        original_card=db.get(Character,"selene").spec
        original_config=db.get(AppSetting,storage.CONFIG_KEY).value
        db.add(AppSetting(key="roleplay_lorebook:protected-cms",value='{"canon":"preserve"}'))
        db.add(AppSetting(key="project_prompt:response",value="PRESERVE_SHARED_PROMPT"))
        db.add(AppSetting(key=storage.run_key("bob","bob-run"),value=json.dumps({"owner":"bob","character_id":"selene","completed":True})))
        # More than the visible run-list limit; deletion must inspect all owner runs.
        for i in range(12):
            db.add(AppSetting(key=storage.run_key("alice","extra-"+str(i)),value=json.dumps({"owner":"alice","character_id":"selene"})))
        for key,value in [
            ("ai_world:alice-old",{"owner":"alice","members":["selene"]}),
            ("world_campaign:alice-old",{"owner":"alice","state":{"cast":[{"id":"selene"}]},"checkpoints":[{"secret":"old"}]}),
            ("world_campaign:bob-old",{"owner":"bob","state":{"cast":[{"id":"selene"}]}}),
            ("world_template:protected",{"owner":"alice","lore":"AUTHORED"})]:
            db.add(AppSetting(key=key,value=json.dumps(value)))
        db.add(Room(id="other-room",user_id="alice",name="Other chat"))
        db.add(RoomMember(id="other-member",room_id="other-room",character_id="ren"))
        db.add(Message(id="keep-message",room_id="other-room",sender_type="user",text="KEEP_OTHER_ROOM"))
        for owner,actor,ident in [("alice","selene","erase-memory"),("bob","selene","bob-memory2"),("alice","ren","keep-memory")]:
            db.add(Memory(id=ident,user_id=owner,character_id=actor,visibility="CHARACTER_PRIVATE",content=ident))
        db.add(Message(id="erase-message",room_id=room,sender_type="character",character_id="selene",text="ERASE_TRANSCRIPT"))
        db.add(MessageSpeech(message_id="erase-message",signature="x",mime_type="audio/mpeg",content=b"audio"))
        db.add(AIRequestLog(id="archive",user_id="alice",room_id=room,product="roleplay",output_text="ERASE_TRANSCRIPT",conversation_snapshot="ERASE_SNAPSHOT"))
        db.add(AIRequestLog(id="other-log",user_id="alice",room_id="other-room",product="roleplay",output_text="KEEP"))
        for owner,prefix in [("alice","erase"),("bob","keep")]:
            db.add(CharacterSocialState(id=prefix+"-edge",user_id=owner,character_a_id="selene",character_b_id="ren"))
            db.add(CharacterSocialKnowledge(id=prefix+"-known",user_id=owner,character_id="ren",subject_character_id="selene",fact_key="identity",fact_value="{}",source="chat"))
            db.add(CharacterSocialCanon(id=prefix+"-canon",user_id=owner,character_a_id="selene",character_b_id="ren",text="old pair"))
            db.add(CharacterSharedInteraction(id=prefix+"-shared",user_id=owner,character_a_id="selene",character_b_id="ren",conversation_id=room,source_message_id="erase-message",interaction_type="GROUP_CHAT",summary="[]",source_ids="[]",source_fingerprint="x",deltas="{}"))
            db.add(VoiceEvent(id=prefix+"-voice",user_id=owner,character_id="selene",message_id="erase-message",event_type="listen",status="success"))
            db.add(CharacterReaction(id=prefix+"-reaction",user_id=owner,character_id="selene",reaction="heart"))
            db.add(CharacterRating(id=prefix+"-rating",user_id=owner,character_id="selene",rating=5))
            db.add(CharacterUsage(id=prefix+"-usage",user_id=owner,character_id="selene"))
        db.commit()
    user["id"]="bob"
    assert client.delete("/v1/rooms/"+room).status_code==404
    user["id"]="alice"
    assert client.delete("/v1/rooms/"+room).status_code==200
    assert client.get("/v1/moonfall/"+s["id"]).status_code==404
    assert client.post("/v1/moonfall/"+s["id"]+"/act",json={"revision":s["revision"],"request_id":"late","action":"hint","value":""}).status_code==404
    with factory() as db:
        assert db.get(Room,room) is None
        assert db.get(Message,"erase-message") is None
        assert db.get(MessageSpeech,"erase-message") is None
        assert db.get(AIRequestLog,"archive") is None
        assert db.get(AIRequestLog,"other-log") is not None
        assert db.get(Message,"keep-message").text=="KEEP_OTHER_ROOM"
        assert db.get(Memory,"erase-memory") is None
        assert db.query(Memory).filter_by(user_id="alice",type="world_shared").count()==0
        assert db.get(Memory,"bob-memory2") is not None and db.get(Memory,"keep-memory") is not None
        assert not storage.user_runs(db,"alice")
        assert db.get(AppSetting,storage.run_key("bob","bob-run")) is not None
        for key in ("ai_world:alice-old","world_campaign:alice-old"):assert db.get(AppSetting,key) is None
        for key in ("world_campaign:bob-old","world_template:protected","roleplay_lorebook:protected-cms","project_prompt:response"):assert db.get(AppSetting,key) is not None
        for model in (CharacterSocialState,CharacterSocialKnowledge,CharacterSocialCanon,CharacterSharedInteraction,VoiceEvent,CharacterReaction,CharacterRating,CharacterUsage):
            assert db.query(model).filter_by(user_id="alice").count()==0,model
            assert db.query(model).filter_by(user_id="bob").count()==1,model
        assert db.get(Character,"selene").spec==original_card
        assert db.get(AppSetting,storage.CONFIG_KEY).value==original_config
    new=start(client)
    assert new["id"]!=s["id"] and not new["completed"]
    assert new["journal"]==[] and new["memories"]==[] and not new["intro_seen"]


def test_room_full_reset_is_atomic_on_failure(moonfall,monkeypatch):
    client,factory,_=moonfall
    s=complete(client,start(client))
    room=client.post("/v1/moonfall/"+s["id"]+"/return-to-chat",json={"sync_memory":True}).json()["room"]["id"]
    def fail(*args):raise RuntimeError("fixture deletion failure")
    monkeypatch.setattr(main,"purge_message_dependents",fail)
    with pytest.raises(RuntimeError,match="fixture deletion failure"):client.delete("/v1/rooms/"+room)
    with factory() as db:
        assert db.get(Room,room) is not None
        assert db.get(AppSetting,storage.run_key("alice",s["id"])) is not None
        assert db.query(Memory).filter_by(user_id="alice",type="world_shared").count()==1

def test_reset_does_not_reunlock_world_from_old_messages_in_other_rooms(moonfall):
    client,factory,_=moonfall
    with factory() as db:
        cfg=storage.config(db);cfg["entry_gate"]["min_meaningful_turns"]=2
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg)
        for ident in ("reset-room","retained-room"):
            db.add(Room(id=ident,user_id="alice",name=ident))
            db.add(RoomMember(id=ident+"-member",room_id=ident,character_id="selene"))
        texts=["I hope we can talk about the strange dreams I had last night.",
               "Would you walk with me through the old library and tell me what you find interesting?"]
        for i,text in enumerate(texts):
            db.add(Message(id="old-input-"+str(i),room_id="retained-room",sender_type="user",text=text))
            db.add(Message(id="old-reply-"+str(i),room_id="retained-room",sender_type="character",character_id="selene",reply_to_message_id="old-input-"+str(i),text="Yes.",finish_status="complete"))
        db.commit()
    assert client.get("/v1/moonfall/chapters?character_id=selene").json()["chapters"][0]["available"]
    assert client.delete("/v1/rooms/reset-room").status_code==200
    result=client.get("/v1/moonfall/chapters?character_id=selene").json()["chapters"][0]
    assert not result["available"] and result["lock_reason"]=="continue_chat"
    with factory() as db:
        assert db.get(Message,"old-input-0") is not None
        for i,text in enumerate(texts):
            db.add(Message(id="fresh-input-"+str(i),room_id="retained-room",sender_type="user",text=text))
            db.add(Message(id="fresh-reply-"+str(i),room_id="retained-room",sender_type="character",character_id="selene",reply_to_message_id="fresh-input-"+str(i),text="Yes.",finish_status="complete"))
        db.commit()
    assert client.get("/v1/moonfall/chapters?character_id=selene").json()["chapters"][0]["available"]
