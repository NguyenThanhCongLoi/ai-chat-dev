from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from character_chat.models import Base,User,UserProfile,Room,Character,Message,PromptTrace
from character_chat.schemas import CharacterSpec
from character_chat.engine import turn_language_instruction,assemble

@pytest.mark.parametrize("text,code",[
    ("What should I do next?","en"),("Tôi nên làm gì tiếp theo?","vi"),
    ("接下来我应该做什么？","zh"),("次は何をすればいい？","ja"),
    ("다음에는 무엇을 해야 할까요?","ko"),("မင်္ဂလာပါ","my"),("តើខ្ញុំគួរធ្វើអ្វីបន្ទាប់?","km")])
def test_latest_user_language_overrides_history_and_preference(text,code):
    history=[SimpleNamespace(sender_type="user",text="Xin chào"),SimpleNamespace(sender_type="character",text="Hello!")]
    detected,instruction=turn_language_instruction(text,history,"vi")
    assert detected==code
    assert "OUTPUT LANGUAGE FOR THIS TURN:" in instruction
    assert "action beats, narration" in instruction

def test_short_ambiguous_turn_uses_user_history_not_character_voice():
    history=[SimpleNamespace(sender_type="user",text="What should I do next?"),SimpleNamespace(sender_type="character",text="Xin chào bạn")]
    assert turn_language_instruction("🙂",history,"vi")[0]=="en"
    assert turn_language_instruction("🙂",[],"my")[0]=="my"

def test_assemble_applies_lock_before_model_call_and_records_it():
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        card=CharacterSpec(id="character",name="Mia",system_prompt="Always speak Vietnamese.")
        db.add_all([User(id="user"),UserProfile(user_id="user",language="vi"),Room(id="room",user_id="user",name="Room"),
          Character(id=card.id,user_id="user",name=card.name,spec=card.model_dump_json()),
          Message(id="old",room_id="room",sender_type="character",character_id=card.id,text="Xin chào bạn.")])
        db.commit()
        prompt,_=assemble(db,"user","room",card,"What should I do next?")
        assert "OUTPUT LANGUAGE FOR THIS TURN: English (en)." in prompt[0]["content"]
        assert "OUTPUT LANGUAGE FOR THIS TURN: English (en)." in prompt[-2]["content"]
        assert prompt[-1]=={"role":"user","content":"What should I do next?"}
        trace=db.query(PromptTrace).one()
        assert '"turn_language": "en"' in trace.state
        assert "turn_language_lock" in trace.layers
    engine.dispose()


def test_audio_markers_do_not_override_latest_vietnamese_user_language():
    from character_chat.speech_language import roleplay_output_prompt, LANGUAGE_INSTRUCTION
    prompt=roleplay_output_prompt([
        {"role":"system","content":"Prefer Indonesian in this character's examples."},
        {"role":"assistant","content":"Kamu mau cerita apa?"},
        {"role":"user","content":"Em muốn anh giải thích thế nào về chuyện này?"},
    ])
    assert prompt[-2]["content"]==LANGUAGE_INSTRUCTION
    assert "OUTPUT LANGUAGE FOR THIS TURN: Vietnamese (vi)." in prompt[-1]["content"]
    assert "action beats" in prompt[-1]["content"]
    assert "[[lang:vi]]" in prompt[-1]["content"]
    assert "never authorize switching languages" in prompt[-1]["content"]


def test_short_ambiguous_message_preserves_assembled_language_lock():
    from character_chat.speech_language import roleplay_output_prompt
    prompt=roleplay_output_prompt([
        {"role":"system","content":"OUTPUT LANGUAGE FOR THIS TURN: English (en)."},
        {"role":"assistant","content":"Xin chào!"},
        {"role":"user","content":"..."},
    ])
    assert "OUTPUT LANGUAGE FOR THIS TURN: English (en)." in prompt[-1]["content"]
