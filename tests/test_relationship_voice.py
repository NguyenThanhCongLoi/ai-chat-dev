from types import SimpleNamespace as NS
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from character_chat.models import Base, AppSetting, User, UserAccount
from character_chat.schemas import CharacterSpec
from character_chat import relationship_voice as voice

@pytest.fixture
def db():
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()

def relation(**kw):
    return NS(id="rel",familiarity=0,trust=0,affinity=0,**kw) if not kw else NS(**({"id":"rel","familiarity":0,"trust":0,"affinity":0}|kw))
def turn(n):return [NS(id=str(n),sender_type="user",text="A real conversation")]
def selene():return CharacterSpec(id="selene",name="Selene Moonbrook")

def test_stage_requires_trust_and_three_distinct_turns_and_never_flaps(db):
    row=relation(); card=selene()
    assert voice.resolve(db,"alice",card,row,turn(0))["vietnamese_default"]==["ta","ngươi"]
    row.familiarity=.2;row.trust=.05
    assert voice.resolve(db,"alice",card,row,turn(1))["stage"]=="reserved"
    row.trust=.1
    for _ in range(6):
        assert voice.resolve(db,"alice",card,row,turn(2))["stage"]=="reserved"
    assert voice.resolve(db,"alice",card,row,turn(3))["stage"]=="reserved"
    assert voice.resolve(db,"alice",card,row,turn(4))["vietnamese_default"]==["tôi","cậu"]
    row.trust=0;row.affinity=0
    assert voice.resolve(db,"alice",card,row,turn(5))["stage"]=="familiar"

def test_profiles_cover_exact_backup_roster_without_replacing_personality():
    assert len(voice.PROFILES)==11
    assert len({p["preset_type"] for p in voice.PROFILES})==11
    for p in voice.PROFILES:
        renamed=CharacterSpec(name="CMS renamed",preset_type=p["preset_type"])
        assert voice.profile_for(renamed)["voice"]==p["voice"]
    merr=voice.profile_for(CharacterSpec(name="Merr"))
    assert "sulking" in merr["voice"] and "without guilt" in merr["voice"]
    assert voice.profile_for(CharacterSpec(name="Unknown original character")) is None

def test_names_are_scoped_and_other_languages_do_not_literalize_pronouns(db):
    db.add_all([User(id="alice"),User(id="bob"),
        UserAccount(user_id="alice",username="a",display_name="Minh",password_hash="test"),
        UserAccount(user_id="bob",username="b",display_name="Lan",password_hash="test")])
    db.flush()
    row=relation(familiarity=.8,trust=.8,affinity=.8)
    a=voice.resolve(db,"alice",selene(),row,turn(1))
    b=voice.resolve(db,"bob",selene(),relation(id="bob-rel"),turn(1))
    assert a["stage"]=="bonded" and a["user_display_name"]=="Minh"
    assert b["stage"]=="reserved" and b["user_display_name"]=="Lan"
    assert "Minh" not in voice.instruction(b,"vi")
    assert "never translate Vietnamese pronouns literally" in voice.instruction(a,"ja")
    assert "latest explicit address or name preference" in voice.instruction(a,"vi")

def test_reset_erases_only_owners_address_state(db):
    from character_chat.conversation_reset import reset_character_experience
    row=relation(familiarity=.8,trust=.8,affinity=.8)
    voice.resolve(db,"alice",selene(),row,turn(1))
    voice.resolve(db,"bob",selene(),row,turn(1))
    db.flush()
    reset_character_experience(db,"alice",["selene"]);db.flush()
    assert db.get(AppSetting,voice.key("alice","selene")) is None
    assert db.get(AppSetting,voice.key("bob","selene")) is not None
    assert voice.resolve(db,"alice",selene(),relation(id="fresh"),turn(2))["stage"]=="reserved"

def test_prompt_integration_uses_the_same_speakers_relationship(db,monkeypatch):
    from character_chat import engine
    from character_chat.models import Character,Room,Message,Relationship,PromptTrace
    monkeypatch.setattr(engine,"detect_user_affect",lambda q:"neutral")
    card=selene()
    db.add_all([User(id="alice"),Character(id=card.id,user_id="alice",name=card.name,spec=card.model_dump_json()),
       Room(id="room",user_id="alice",name="Chat"),
       Message(id="q",room_id="room",sender_type="user",text="How are you?"),
       Relationship(id="r",user_id="alice",character_id=card.id,familiarity=.6,trust=.4,affinity=.3)])
    db.flush()
    messages,_=engine.assemble(db,"alice","room",card,"How are you?")
    lock=messages[-2]["content"]
    assert "EARNED SPEAKING STYLE" in lock and '"stage": "close"' in lock
    assert "OUTPUT LANGUAGE FOR THIS TURN: English" in lock
    assert "earned_speaking_style" in db.query(PromptTrace).one().layers
