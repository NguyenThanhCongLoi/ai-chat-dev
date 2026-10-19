"""Ordinary chat continuity must affect prompts while enforcing room ownership."""
import json
import pytest
from test_worlds import world_client
from character_chat import main, engine
from character_chat.models import Room,RoomMember,Message,AppSetting,Memory,PromptTrace,RelationshipEvent
from character_chat.schemas import CharacterSpec
from character_chat import roleplay_continuity as continuity


@pytest.fixture
def chat_tools(world_client):
    client,factory,user=world_client
    with factory() as db:
        db.add_all([Room(id="chat",user_id="alice",name="Chat"),Room(id="bob-chat",user_id="bob",name="Other")])
        db.add_all([RoomMember(id="s",room_id="chat",character_id="selene"),RoomMember(id="r",room_id="chat",character_id="ren")])
        db.add(Message(id="source",room_id="chat",sender_type="user",text="I promised to keep the moonstone safe."))
        db.add(Message(id="bob-source",room_id="bob-chat",sender_type="user",text="BOB_SOURCE_SECRET"))
        db.commit()
    return client,factory,user


def endpoint(suffix="continuity"):
    return "/v1/roleplay/rooms/chat/"+suffix


def entry(ident,scope="public",knowers=None,**extra):
    return {"id":ident,"title":ident,"text":ident+"_CONTENT","scope":scope,"knowers":knowers or [],
            "keywords":["moonstone"],"canon":True,"always":True,"priority":5,"unlocked":False,**extra}


def test_scene_and_private_lore_reach_only_correct_character_prompt(chat_tools):
    client,factory,_=chat_tools
    config=client.get(endpoint()).json()
    config.update(scene={"location":"Moon Tower","time":"Midnight","objective":"Keep the promise"},
                  lore=[entry("PUBLIC"),entry("PRIVATE",scope="private",knowers=["selene"]),entry("LOCKED",scope="discovered")])
    assert client.put(endpoint(),json=config).status_code==200
    with factory() as db:
        for ident in ("selene","ren"):
            messages,_=engine.assemble(db,"alice","chat",CharacterSpec(id=ident,name=ident),"What happens now?")
            prompt=json.dumps(messages)
            assert "Moon Tower" in prompt and "PUBLIC_CONTENT" in prompt
            assert ("PRIVATE_CONTENT" in prompt)==(ident=="selene")
            assert "LOCKED_CONTENT" not in prompt
        db.commit()
        trace=db.query(PromptTrace).filter_by(character_id="ren").first()
        assert "scoped_lorebook" in json.loads(trace.layers)
        assert json.loads(trace.state)["continuity"]["lore_ids"]==["PUBLIC"]


def test_revision_and_ownership_are_enforced(chat_tools):
    client,_,user=chat_tools
    config=client.get(endpoint()).json()
    assert client.put(endpoint(),json=config).status_code==200
    assert client.put(endpoint(),json=config).status_code==409
    user["id"]="bob"
    for suffix in ("continuity","inspect?character_id=selene","timeline?character_id=selene","recap"):
        assert client.get(endpoint(suffix)).status_code==404
    assert client.put(endpoint(),json={"revision":1}).status_code==404


@pytest.mark.parametrize("lore",[
    [entry("bad",scope="private",knowers=["bob-private"])],
    [entry("bad",scope="private",knowers=["selene","ren"])],
    [entry("bad",scope="rumor")],
    [entry("bad",keywords=[],always=False)],
    [entry("bad"),entry("bad")],
])
def test_invalid_lore_is_rejected(chat_tools,lore):
    client,_,_=chat_tools
    assert client.put(endpoint(),json={"revision":0,"lore":lore}).status_code==422


def test_lore_activation_aliases_and_budget_after_scope_filter(chat_tools):
    client,factory,_=chat_tools
    cfg=client.get(endpoint()).json()
    cfg["lore"]=[entry("SECRET",scope="private",knowers=["selene"],priority=10),
                 entry("MATCH",keywords=["nguYỆt thạch"],always=False),
                 entry("UNMATCHED",keywords=["ocean"],always=False)]
    assert client.put(endpoint(),json=cfg).status_code==200
    with factory() as db:
        _,selected,meta=continuity.context(db,"alice","chat","ren","nguyet thach",[])
        assert [x["id"] for x in selected]==["MATCH"]
        assert meta["lore_characters"]<=meta["lore_budget"]


def test_memory_controls_apply_to_prompt_and_both_extraction_paths(chat_tools):
    client,factory,_=chat_tools
    with factory() as db:
        db.add(Memory(id="scoped",user_id="alice",character_id="selene",content="UNIQUE_MEMORY",visibility="CHARACTER_PRIVATE",pinned=1))
        db.commit()
    cfg=client.get(endpoint()).json();cfg.update(use_memory=False,auto_memory=False)
    assert client.put(endpoint(),json=cfg).status_code==200
    with factory() as db:
        prompt,_=engine.assemble(db,"alice","chat",CharacterSpec(id="selene",name="Selene"),"Hello")
        assert "UNIQUE_MEMORY" not in json.dumps(prompt)
        count=db.query(Memory).count()
        main.extract_memory(db,"alice","chat","source","I remember my favourite tea every morning",["selene"])
        assert db.query(Memory).count()==count
        assert not continuity.auto_memory_enabled(db,"alice","chat")
        assert db.get(Memory,"scoped") is not None
    inspect=client.get(endpoint("inspect?character_id=selene")).json()
    assert inspect["estimated_characters"]==0 and not any(m["selected"] for m in inspect["memories"])


def test_inspector_sources_and_timeline_do_not_leak_foreign_data(chat_tools):
    client,factory,_=chat_tools
    with factory() as db:
        db.add_all([Memory(id="good",user_id="alice",character_id="selene",content="Known memory",visibility="CHARACTER_PRIVATE",source_message_id="source"),
                    Memory(id="bad-ref",user_id="alice",character_id="selene",content="Other reference",visibility="CHARACTER_PRIVATE",source_message_id="bob-source"),
                    RelationshipEvent(id="milestone",user_id="alice",character_id="selene",room_id="chat",source_message_id="source",event_type="repair",confidence=.8)])
        db.commit()
    result=client.get(endpoint("inspect?character_id=selene"))
    assert result.status_code==200 and "BOB_SOURCE_SECRET" not in result.text and "BOB_SECRET" not in result.text
    items={x["id"]:x for x in result.json()["memories"]}
    assert items["good"]["source_text"] and not items["bad-ref"]["source_text"]
    assert client.get(endpoint("inspect?character_id=bob-private")).status_code==404
    events=client.get(endpoint("timeline?character_id=selene")).json()
    assert events[0]["type"]=="repair" and events[0]["source_text"]
    assert "BOB_SOURCE_SECRET" not in client.get(endpoint("recap")).text


def test_deleting_room_also_removes_scene_and_lore(chat_tools):
    client,factory,_=chat_tools
    assert client.put(endpoint(),json={"revision":0,"lore":[entry("PUBLIC")]}).status_code==200
    with factory() as db:
        main.purge_room_record(db,db.get(Room,"chat"));db.commit()
        assert db.get(AppSetting,continuity.PREFIX+"chat") is None


def test_deleting_character_prunes_knowledge_recipients(chat_tools):
    client,factory,_=chat_tools
    cfg=client.get(endpoint()).json()
    cfg["lore"]=[entry("KEEP"),entry("DROP",scope="private",knowers=["selene"]),
                 entry("SHRINK",scope="witnessed",knowers=["selene","ren"])]
    assert client.put(endpoint(),json=cfg).status_code==200
    with factory() as db:
        continuity.remove_character(db,"chat","selene")
        db.commit()
    remaining=client.get(endpoint()).json()
    assert remaining["revision"]==2
    assert [x["id"] for x in remaining["lore"]]==["KEEP","SHRINK"]
    assert remaining["lore"][1]["knowers"]==["ren"]


def test_one_click_pin_is_attributed_deduplicated_and_private_to_owner(chat_tools):
    client,factory,user=chat_tools
    result=client.post(endpoint("remember"),json={"message_id":"source"})
    assert result.status_code==200
    assert client.post(endpoint("remember"),json={"message_id":"source"}).json()["id"]==result.json()["id"]
    assert client.get(endpoint("pins")).json()["message_ids"]==["source"]
    with factory() as db:
        m=db.get(Memory,result.json()["id"])
        assert m.pinned and m.type=="pinned_message" and m.source_message_id=="source"
        assert m.visibility=="ROOM_SHARED" and m.content.startswith("User:")
    assert client.post(endpoint("remember"),json={"message_id":"bob-source"}).status_code==404
    assert client.post(endpoint("remember"),json={"message_id":"source","character_id":"bob-private"}).status_code==422
    assert client.post(endpoint("remember"),json={"message_id":"source","pinned":False}).json()["pinned"] is False
    assert client.get(endpoint("pins")).json()["message_ids"]==[]
    user["id"]="bob"
    assert client.get(endpoint("pins")).status_code==404
    assert client.post(endpoint("remember"),json={"message_id":"source"}).status_code==404
