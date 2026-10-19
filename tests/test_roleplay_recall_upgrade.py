"""Behavior regressions for the research-informed ordinary chat upgrades."""
import json
import pytest
from character_chat import engine, group_routing, jev, roleplay_continuity
from character_chat.models import Memory
from character_chat.retrieval import retrieve_memories, store_memory
from character_chat.roleplay_recall import phrase_match, rank_scores
from character_chat.schemas import CharacterSpec
from test_worlds import world_client
from test_roleplay_continuity import chat_tools, entry, endpoint


@pytest.mark.parametrize("query,content", [
    ("ca phe", "Tôi thích cà phê vào buổi sáng."),
    ("coffee", "Tôi thích cà phê vào buổi sáng."),
    ("sinh nhat", "My birthday is in November."),
    ("約束", "I promised to keep your letter."),
    ("咖啡", "I prefer coffee in the morning."),
    ("커피", "Tôi thích cà phê."),
])
def test_multilingual_lexical_aliases(query, content):
    assert rank_scores(query, [content, "The mountain was covered in snow."]) == [1.0, 0.0]


def test_long_negated_statement_is_never_fuzzy_merged(chat_tools):
    _,factory,_=chat_tools
    base="I like drinking warm jasmine tea beside the quiet library every evening"
    with factory() as db:
        args=dict(user_id="alice",character_id="selene",room_id=None,visibility="CHARACTER_PRIVATE")
        yes=store_memory(db,**args,content=base)
        no=store_memory(db,**args,content=base.replace("I like","I do not like"))
        assert yes.id!=no.id
        assert store_memory(db,**args,content="  "+base.upper()+"  ").id==yes.id


def test_recall_acl_relevance_pins_and_confidence(chat_tools):
    _,factory,_=chat_tools
    with factory() as db:
        common=dict(user_id="alice",character_id="selene",visibility="CHARACTER_PRIVATE",importance=.8,created_at="2026-01-01T00:00:00+00:00")
        db.add_all([
            Memory(id="relevant",content="Tôi uống cà phê mỗi sáng",confidence=.9,**common),
            Memory(id="uncertain",content="Tôi uống cà phê mỗi sáng",confidence=.2,**common),
            Memory(id="unrelated",content="The sky over the mountain is blue",**common),
            Memory(id="foreign",user_id="bob",character_id="selene",visibility="CHARACTER_PRIVATE",content="coffee SECRET_BOB"),
            Memory(id="other-actor",user_id="alice",character_id="ren",visibility="CHARACTER_PRIVATE",content="coffee SECRET_REN"),
            Memory(id="other-room",user_id="alice",room_id="elsewhere",visibility="ROOM_SHARED",content="coffee SECRET_ROOM"),
        ]);db.commit()
        recalled=retrieve_memories(db,"alice","selene","chat","coffee",limit=12)
        ids=[m.id for m in recalled]
        assert "alice-memory" in ids  # Explicit user pins remain included.
        assert ids.index("relevant")<ids.index("uncertain")
        assert not {"foreign","other-actor","other-room","unrelated"} & set(ids)
        prompt,_=engine.assemble(db,"alice","chat",CharacterSpec(id="selene",name="Selene"),"coffee")
        text=json.dumps(prompt,ensure_ascii=False)
        assert "cà phê" in text and "source_message_id" in text
        assert not any(secret in text for secret in ("SECRET_BOB","SECRET_REN","SECRET_ROOM"))


def test_lore_whole_words_aliases_and_acl_reach_next_prompt(chat_tools):
    client,factory,_=chat_tools
    cfg=client.get(endpoint()).json()
    cfg["lore"]=[entry("ART",keywords=["art"],always=False),
                 entry("PRIVATE",scope="private",knowers=["selene"],keywords=["art"],always=False)]
    assert client.put(endpoint(),json=cfg).status_code==200
    with factory() as db:
        assert roleplay_continuity.context(db,"alice","chat","ren","heart",[])[1]==[]
        _,selected,_=roleplay_continuity.context(db,"alice","chat","ren","ART",[])
        assert [x["id"] for x in selected]==["ART"]
        prompt,_=engine.assemble(db,"alice","chat",CharacterSpec(id="ren",name="Ren"),"Art")
        assert "ART_CONTENT" in str(prompt) and "PRIVATE_CONTENT" not in str(prompt)
    assert phrase_match("nguyệt thạch","NGUYET THACH") and not phrase_match("art","cart")


def cast():
    return [CharacterSpec(id=str(i),name=name) for i,name in enumerate(
        ["Selene Moonbrook","Ren Quickshade","Mira Sunpetal","Lyra Ashveil","Aurelion Voss"])]


def test_unique_short_mentions_bypass_remote_and_ambiguous_names_do_not(monkeypatch):
    monkeypatch.setattr(jev,"enabled",lambda task:True)
    monkeypatch.setattr(jev,"select_speakers",lambda *a,**kw:pytest.fail("Direct mention must not call provider"))
    assert group_routing.plan_selected_group("@Selene, tell me more",cast()).speakers[0].id=="0"
    assert group_routing.plan_selected_group("Ren, your thoughts?",cast()).speakers[0].id=="1"
    ambiguous=[CharacterSpec(id="a",name="Alex Moon"),CharacterSpec(id="b",name="Alex River")]
    assert not group_routing.mentioned_characters("Alex, hello",ambiguous)
    assert group_routing.mentioned_characters("@Alex Moon",ambiguous)[0].id=="a"
    assert not group_routing.mentioned_characters("Serenity",cast())
    assert [c.id for c in group_routing.mentioned_characters("@Selene Moonbrook and @Ren",cast(),True)]==["0","1"]


def test_automatic_remote_cap_and_explicit_everyone(monkeypatch):
    actors=cast()
    monkeypatch.setattr(jev,"enabled",lambda task:True)
    calls=[]
    def decide(*args):
        calls.append(True)
        return actors,{"decision_scores":{c.id:.7+i*.01 for i,c in enumerate(actors)}},""
    monkeypatch.setattr(jev,"select_speakers",decide)
    plan=group_routing.plan_selected_group("Any thoughts on the journey?",actors)
    assert [c.id for c in plan.speakers]==["4","3"]
    assert plan.metadata()["suppressed_speakers"]==3
    before=len(calls)
    assert len(group_routing.plan_selected_group("Everyone, introduce yourself",actors).speakers)==5
    assert len(calls)==before


def test_followup_keeps_previous_speaker_and_group_is_usually_single():
    actors=cast()
    history=[{"sender_type":"user","text":"Hello"},{"sender_type":"character","character_id":"2","text":"Welcome."}]
    assert group_routing.plan_group("Tell me more",actors,history=history).speakers[0].id=="2"
    assert len(group_routing.plan_group("Hello there",actors).speakers)==1


def test_single_chat_api_uses_cms_lore_memory_scene_and_saved_updates(chat_tools,monkeypatch):
    from character_chat import main
    from character_chat.models import RoomMember, Message, PromptTrace
    client,factory,_=chat_tools
    monkeypatch.setenv("JEV_ENABLED","false")
    monkeypatch.setattr(main,"analyze_turn",lambda *a:None)
    monkeypatch.setattr(main,"message_speech_info",lambda *a,**kw:{})
    captures=[]
    def complete(messages,*args,**kwargs):
        captures.append(json.dumps(messages,ensure_ascii=False))
        return "I remember our quiet conversation.",{"actual_model":"mock","primary_model":"mock"}
    monkeypatch.setattr(main.llm,"chat_with_meta",complete)
    with factory() as db:
        db.query(RoomMember).filter_by(room_id="chat",character_id="ren").delete()
        db.add(Memory(id="solo-memory",user_id="alice",character_id="selene",
            visibility="CHARACTER_PRIVATE",content="Tôi thích cà phê",pinned=1))
        db.commit()
    cfg=client.get(endpoint()).json()
    cfg["scene"]={"location":"Moon Tower","time":"Night","objective":"Discuss the map"}
    assert client.put(endpoint(),json=cfg).status_code==200
    main.app.dependency_overrides[main.docs_auth]=lambda:None
    saved=client.post("/v1/admin/roleplay-lorebook",json={
        "title":"Tower map","text":"SOLO_CMS_LORE_V1",
        "targets":["character:selene"],"knowers":[],"scope":"public",
        "keywords":["map"],"always":False,"canon":True,"enabled":True,"priority":5})
    assert saved.status_code==200,saved.text
    row=saved.json()
    for version in ("V1","V2"):
        if version=="V2":
            changed=client.put("/v1/admin/roleplay-lorebook/"+row["id"],
                json={**row,"text":"SOLO_CMS_LORE_V2"})
            assert changed.status_code==200,changed.text
        before=len(captures)
        response=client.post("/v1/rooms/chat/messages",json={"message":"Tell me about the map."})
        assert response.status_code==200,response.text
        assert len(response.json()["responses"])==1
        assert response.json()["responses"][0]["character_id"]=="selene"
        prompt=" ".join(captures[before:])
        assert "SOLO_CMS_LORE_"+version in prompt and "Moon Tower" in prompt and "cà phê" in prompt
        if version=="V2":
            assert "SOLO_CMS_LORE_V1" not in prompt
    with factory() as db:
        assert db.query(Message).filter_by(room_id="chat",sender_type="character").count()==2
        traces=db.query(PromptTrace).filter_by(room_id="chat",character_id="selene").all()
        assert len(traces)==2
        assert all("scoped_lorebook" in json.loads(t.layers) and "solo-memory" in json.loads(t.memory_ids) for t in traces)
