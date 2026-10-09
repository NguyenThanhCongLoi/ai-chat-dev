import os
os.environ.setdefault("DATABASE_URL", "sqlite://")
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest
from character_chat.db import Base, User, UserProfile, AppSetting, Room, Message, Character
from character_chat.schemas import CharacterSpec
import character_chat.main as main


@pytest.fixture
def greeting_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id="greeting-user"))
        db.add(UserProfile(user_id="greeting-user", language="vi"))
        db.commit()
        yield db
    engine.dispose()


def set_language(db, code):
    db.get(UserProfile, "greeting-user").language = code
    db.flush()


@pytest.mark.parametrize("language", ["en", "zh", "ja", "ko", "my", "fr"])
def test_non_vietnamese_greeting_is_english_and_shared(greeting_db, monkeypatch, language):
    db = greeting_db
    calls = []
    def translate(messages, **kwargs):
        calls.append(messages)
        return "*smiles* Welcome, my friend."
    monkeypatch.setattr(main.llm, "chat", translate)
    card = CharacterSpec(id="greeting-card", name="Ruby", initial_greeting="*mỉm cười* Chào bạn.")
    original = card.model_dump()
    set_language(db, language)
    assert main.localized_greeting(db, "greeting-user", card) == "*smiles* Welcome, my friend."
    set_language(db, "ko" if language != "ko" else "zh")
    assert main.localized_greeting(db, "greeting-user", card) == "*smiles* Welcome, my friend."
    assert len(calls) == 1
    assert "English" in calls[0][0]["content"]
    assert card.model_dump() == original
    set_language(db, "vi")
    assert main.localized_greeting(db, "greeting-user", card) == card.initial_greeting
    assert len(calls) == 1


def test_greeting_edit_invalidates_translation(greeting_db, monkeypatch):
    db = greeting_db
    calls = []
    monkeypatch.setattr(main.llm, "chat", lambda messages, **kw: calls.append(messages[-1]["content"]) or "English " + str(len(calls)))
    set_language(db, "ja")
    card = CharacterSpec(id="greeting-card", name="Ruby", initial_greeting="Chào bạn.")
    assert main.localized_greeting(db, "greeting-user", card) == "English 1"
    card.initial_greeting = "Lại gặp nhau rồi."
    assert main.localized_greeting(db, "greeting-user", card) == "English 2"
    assert calls == ["Chào bạn.", "Lại gặp nhau rồi."]


def test_translation_failure_is_not_cached(greeting_db, monkeypatch):
    db = greeting_db
    set_language(db, "zh")
    card = CharacterSpec(id="greeting-card", name="Ruby", initial_greeting="Chào bạn.")
    def fail(*args, **kwargs):
        raise RuntimeError("unavailable")
    monkeypatch.setattr(main.llm, "chat", fail)
    assert main.localized_greeting(db, "greeting-user", card) == "Hello, I'm Ruby. It's nice to meet you."
    assert db.query(AppSetting).count() == 0
    monkeypatch.setattr(main.llm, "chat", lambda *args, **kwargs: "Welcome back.")
    assert main.localized_greeting(db, "greeting-user", card) == "Welcome back."


def test_speech_matches_localized_greeting_without_changing_history(greeting_db, monkeypatch):
    db = greeting_db
    set_language(db, "my")
    card = CharacterSpec(id="greeting-card", name="Ruby", initial_greeting="Chào bạn.")
    character = Character(id=card.id, user_id="greeting-user", name=card.name, spec=card.model_dump_json())
    db.add(character)
    db.add(Room(id="greeting-room", user_id="greeting-user", name="Ruby"))
    message = Message(id="greeting-message", room_id="greeting-room", sender_type="character", character_id=card.id, text=card.initial_greeting)
    db.add(message)
    db.commit()
    monkeypatch.setattr(main.llm, "chat", lambda *args, **kwargs: "Welcome back.")
    assert main.speech_message_text(db, message, character) == "Welcome back."
    assert message.text == "Chào bạn."
    db.add(Message(id="greeting-user-message", room_id="greeting-room", sender_type="user", text="Hi"))
    db.flush()
    reply = Message(id="later-reply", room_id="greeting-room", sender_type="character", character_id=card.id, text="A later reply.")
    db.add(reply)
    db.flush()
    assert main.speech_message_text(db, reply, character) == "A later reply."
