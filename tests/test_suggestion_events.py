import asyncio
import concurrent.futures
import json
import threading
import time

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from character_chat.suggestion_stream import merge_suggestion_stream


def test_suggestion_event_can_arrive_before_first_answer_chunk():
    release = threading.Event()
    future = concurrent.futures.Future()
    future.set_result((["one", "two", "three"], {}, 10))
    def answer():
        assert release.wait(2)
        yield "answer"
    iterator = merge_suggestion_stream(answer(), future, {})
    try:
        assert next(iterator) == {"_suggestions_ready": True}
        release.set()
        assert next(iterator) == "answer"
        assert list(iterator) == []
    finally:
        release.set()
        iterator.close()


@pytest.fixture
def local_db(monkeypatch, tmp_path):
    import character_chat.main as main
    from character_chat.db import Base, User, Room, ModelConfig, AppSetting
    engine = create_engine("sqlite:///" + (tmp_path / "events.sqlite").as_posix(), connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Local = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(main, "Session", Local)
    monkeypatch.setattr(main, "ensure_safe_content", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "credential_for_model", lambda *args: "test")
    monkeypatch.setattr(main, "model_circuit_remaining", lambda _: 0)
    monkeypatch.setattr(main, "record_model_success", lambda _: None)
    monkeypatch.setattr(main, "write_audit_event", lambda **kwargs: None)
    monkeypatch.setenv("SUGGESTION_BUDGET_SECONDS", "2")
    with Local() as db:
        db.add_all([User(id="event-user"), Room(id="event-room", user_id="event-user", name="assistant:assistant_general:Test"),
                    ModelConfig(id="event-model", name="Test", provider="test", model_id="wire", api_base="https://invalid", assistant_enabled=1),
                    AppSetting(key="model_profile:event-model", value=json.dumps({"purposes": ["assistant_general"]}))])
        db.commit()
        yield main, db, Local
    engine.dispose()


def request():
    value = Request({"type": "http", "method": "POST", "path": "/test", "headers": []})
    value.state.received_at = time.monotonic()
    return value


def parse(block):
    lines = block.splitlines()
    event = next(line[7:] for line in lines if line.startswith("event: "))
    data = json.loads(next(line[6:] for line in lines if line.startswith("data: ")))
    return event, data


@pytest.mark.parametrize("early", [True, False])
def test_assistant_suggestions_are_independent_and_saved(local_db, monkeypatch, early):
    from character_chat.db import Message, AIRequestLog
    main, db, Local = local_db
    release = threading.Event()
    def suggestions(*args, **kwargs):
        if not early:
            assert release.wait(4)
        return "@@Nói tiếp nhé|Cho mình ví dụ|Giải thích thêm nhé", {"actual_model": "wire"},  # chain returns raw, meta
    monkeypatch.setattr(main, "run_assistant_model_chain", suggestions)
    def answer(*args):
        if early:
            assert release.wait(4)
        yield "A complete answer"
        yield {"_stream_status": "complete"}
    monkeypatch.setattr(main, "chat_stream", answer)
    response = main.stream_assistant_message("event-room", {"message": "Nói tiếp nhé"}, request(), user="event-user", db=db)
    seen = []
    async def consume():
        async for block in response.body_iterator:
            name, payload = parse(block)
            seen.append((name, payload))
            if early and name == "suggestions":
                release.set()
            if not early and name == "answer_done":
                with Local() as check:
                    assert check.get(Message, payload["id"]).text == "A complete answer"
                    assert check.query(AIRequestLog).filter_by(task="assistant_general").count() == 1
                    assert check.query(AIRequestLog).filter_by(task="suggestion").count() == 0
                release.set()
    try:
        asyncio.run(consume())
    finally:
        release.set()
    names = [name for name, _ in seen]
    assert names.count("suggestions") == 1
    assert names.count("answer_done") == 1
    assert names[-1] == "done"
    assert (names.index("suggestions") < names.index("delta")) is early
    done = next(payload for name, payload in seen if name == "answer_done")
    options = next(payload for name, payload in seen if name == "suggestions")
    assert options["message_id"] == done["id"]
    with Local() as check:
        assert check.query(AIRequestLog).filter_by(task="suggestion").count() == 1
        assert main.suggestion_values(check, done["id"]) == options["suggestions"]


@pytest.mark.parametrize("speaker_mode,user_text", [
    ("everyone","Xin chào"),
    ("auto","Everyone, what do you think?"),
    ("auto","@Character 0 and @Character 1, discuss this"),
])
def test_roleplay_group_answers_do_not_wait_for_suggestions(local_db, monkeypatch,speaker_mode,user_text):
    from character_chat.db import Character, RoomMember, Message, AIRequestLog
    from character_chat.schemas import CharacterSpec, MessageIn
    main, db, Local = local_db
    room = db.get(main.Room, "event-room")
    room.name = "Roleplay group"
    for index in range(2):
        character = CharacterSpec(id=f"event-char-{index}", name=f"Character {index}")
        db.add(Character(id=character.id, user_id="event-user", name=character.name, spec=character.model_dump_json()))
        db.add(RoomMember(id=f"event-member-{index}", room_id=room.id, character_id=character.id))
    db.commit()
    release = threading.Event()
    monkeypatch.setattr(main, "assemble", lambda *args: ([], []))
    monkeypatch.setattr(main, "extract_memory", lambda *args: None)
    def answer(*args):
        yield "delta", "Hello"
        yield "complete", {"actual_model": "wire", "finish_status": "complete"}
    monkeypatch.setattr(main, "stream_roleplay_answer", answer)
    def suggestions(*args):
        assert release.wait(4)
        return ["Nói tiếp nhé", "Cho mình ví dụ", "Giải thích thêm nhé"], {"actual_model": "wire"}, 55
    monkeypatch.setattr(main, "generate_roleplay_suggestions", suggestions)
    response = main.stream_message("event-room", MessageIn(message=user_text, speaker_mode=speaker_mode),
                                   BackgroundTasks(), request(), db=db, user="event-user")
    seen = []
    async def consume():
        async for block in response.body_iterator:
            name, payload = parse(block)
            seen.append((name, payload))
            if name == "answer_done":
                assert sum(name == "character_message" for name, _ in seen) == 2
                with Local() as check:
                    assert check.query(Message).filter_by(sender_type="character").count() == 2
                    assert check.query(AIRequestLog).filter_by(task="response").count() == 2
                    assert check.query(AIRequestLog).filter_by(task="suggestion").count() == 0
                release.set()
    try:
        asyncio.run(consume())
    finally:
        release.set()
    replies = {payload["id"] for name, payload in seen if name == "character_message"}
    options = [payload for name, payload in seen if name == "suggestions"]
    assert len(options) == 1
    last_reply=[payload for name,payload in seen if name=="character_message"][-1]
    assert options[0]["message_id"] == last_reply["id"]
    assert len(options[0]["suggestions"]) == 3
    assert [payload for name,payload in seen if name=="character_message"][0]["suggestions"] == []
    assert seen[-1][0] == "done"
    with Local() as check:
        assert [log.latency_ms for log in check.query(AIRequestLog).filter_by(task="suggestion")] == [55]
        logs=check.query(AIRequestLog).filter_by(task="response").all()
        plans=[json.loads(log.conversation_snapshot)["group_routing"] for log in logs]
        assert all(len(plan["speaker_ids"])==2 for plan in plans)
        assert all(plan["router"]=="local_rules_topics_v1" for plan in plans)
        if "discuss" in user_text:
            assert all(plan["interaction"]=="exchange" for plan in plans)


def test_assistant_suggestion_deadline_does_not_delay_answer_done(local_db, monkeypatch):
    main, db, Local = local_db
    monkeypatch.setattr(main,"post_stream_suggestion_wait",lambda:.05)
    release = threading.Event()
    def slow(*args, **kwargs):
        release.wait(3)
        return "@@Nói tiếp nhé|Cho mình ví dụ|Giải thích thêm nhé", {}
    monkeypatch.setattr(main, "run_assistant_model_chain", slow)
    monkeypatch.setattr(main, "chat_stream", lambda *args: iter(["Answer", {"_stream_status": "complete"}]))
    response = main.stream_assistant_message("event-room", {"message": "Nói tiếp nhé"}, request(), user="event-user", db=db)
    seen = []
    async def consume():
        async for block in response.body_iterator:
            event, payload = parse(block)
            seen.append((event, payload))
            if event == "answer_done":
                assert not release.is_set()
    try:
        asyncio.run(consume())
    finally:
        release.set()
    names = [event for event, _ in seen]
    assert names.index("answer_done") < names.index("suggestions")
    assert names[-1] == "done"
    with Local() as check:
        log = check.query(main.AIRequestLog).filter_by(task="suggestion").one()
        assert log.fallback_used
        assert "TimeoutError" in log.error

def test_group_prompt_keeps_speaker_identity_and_skips_empty_draft(local_db,monkeypatch):
    from types import SimpleNamespace
    from character_chat import engine
    from character_chat.schemas import CharacterSpec
    main,db,_=local_db
    a=CharacterSpec(id="group-a",name="Doctor",description="A careful physician")
    b=CharacterSpec(id="group-b",name="Artist",description="A playful painter")
    for c in (a,b):
        db.add(main.Character(id=c.id,user_id="event-user",name=c.name,spec=c.model_dump_json()))
        db.add(main.RoomMember(id="member-"+c.id,room_id="event-room",character_id=c.id))
    db.add(main.Message(id="other-line",room_id="event-room",sender_type="character",character_id=a.id,text="I recommend a medical check."))
    db.add(main.Message(id="empty-draft",room_id="event-room",sender_type="character",character_id=b.id,text=""))
    db.commit()
    monkeypatch.setattr(engine,"evaluate_state",lambda *args:SimpleNamespace(emotion="neutral",energy=.5,mood=.5,intensity=0))
    messages,_=engine.assemble(db,"event-user","event-room",b,"What do you think?")
    system=messages[0]["content"]
    assert "GROUP SPEAKER LOCK: You are only Artist (character_id=group-b)" in system
    assert "do not repeat their answer or inherit their personality" in system
    assert "Doctor" in system
    assert not any(item["role"]=="assistant" and item["content"]=="I recommend a medical check." for item in messages)
    assert not any(not item["content"].strip() for item in messages)

def test_group_error_log_preserves_actual_speaker_and_shared_user_turn(local_db):
    main,db,_=local_db
    from character_chat.schemas import CharacterSpec
    for index in range(2):
        c=CharacterSpec(id=f"log-char-{index}",name=f"Speaker {index}")
        db.add(main.Character(id=c.id,user_id="event-user",name=c.name,spec=c.model_dump_json()))
        db.add(main.RoomMember(id=f"log-member-{index}",room_id="event-room",character_id=c.id))
    question=main.Message(id="shared-user-turn",room_id="event-room",sender_type="user",text="Hello everyone")
    db.add(question);db.commit()
    main.save_ai_request_log(db,"event-user","event-room",question.id,None,"roleplay","response",{},12,error="failed",character_id="log-char-1")
    db.commit()
    log=db.query(main.AIRequestLog).one();snapshot=json.loads(log.conversation_snapshot)
    assert snapshot["character_id"]=="log-char-1"
    assert snapshot["character_name"]=="Speaker 1"
    assert snapshot["room_type"]=="group"
    assert snapshot["user_message_id"]==question.id
    assert {item["id"] for item in snapshot["room_characters"]}=={"log-char-0","log-char-1"}

def test_post_stream_suggestion_wait_is_two_and_half_seconds():
    from character_chat.suggestion_stream import post_stream_suggestion_wait
    assert post_stream_suggestion_wait()==2.5

def test_suggestion_deadline_starts_after_answer_not_job_start(local_db,monkeypatch):
    main,db,_=local_db
    from character_chat.schemas import CharacterSpec,MessageIn
    c=CharacterSpec(id="wait-speaker",name="Speaker")
    db.get(main.Room,"event-room").name="Roleplay"
    db.add(main.Character(id=c.id,user_id="event-user",name=c.name,spec=c.model_dump_json()))
    db.add(main.RoomMember(id="wait-member",room_id="event-room",character_id=c.id));db.commit()
    release=threading.Event()
    monkeypatch.setattr(main,"assemble",lambda *args:([],[]))
    monkeypatch.setattr(main,"extract_memory",lambda *args:None)
    monkeypatch.setattr(main,"suggestion_budget",lambda:.01)
    monkeypatch.setattr(main,"post_stream_suggestion_wait",lambda:.3)
    def answer(*args):
        time.sleep(.05)
        yield "delta","Complete reply"
        yield "complete",{"actual_model":"response","finish_status":"complete"}
    def suggest(*args):
        assert release.wait(2)
        return ["Bạn nghĩ sao?","Mình nên làm gì?","Có cách khác không?"],{"actual_model":"suggest-model"},75
    monkeypatch.setattr(main,"stream_roleplay_answer",answer)
    monkeypatch.setattr(main,"generate_roleplay_suggestions",suggest)
    response=main.stream_message("event-room",MessageIn(message="Xin chào"),BackgroundTasks(),request(),db=db,user="event-user")
    seen=[]
    async def consume():
        async for block in response.body_iterator:
            event,payload=parse(block);seen.append((event,payload))
            if event=="answer_done":threading.Timer(.03,release.set).start()
    try:asyncio.run(consume())
    finally:release.set()
    options=[payload for event,payload in seen if event=="suggestions"]
    assert len(options)==1 and options[0]["suggestions"][0]=="Bạn nghĩ sao?"
    log=db.query(main.AIRequestLog).filter_by(task="suggestion").one()
    assert log.actual_model=="suggest-model"
    assert not log.fallback_used
