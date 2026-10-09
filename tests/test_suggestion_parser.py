import pytest
from character_chat.engine import parse_suggestions, finalize_suggestions


@pytest.mark.parametrize("raw", [
    "@@Nói tiếp đi|Nói tiếp đi|Nói tiếp đi",
    "@@Nói tiếp đi|\nNói tiếp đi|\nNói tiếp đi",
    '["Nói tiếp đi","Nói tiếp đi","Nói tiếp đi"]',
    '{"suggestions":["Nói tiếp đi","Nói tiếp đi","Nói tiếp đi"]}',
    "1. Nói tiếp đi\n2. Nói tiếp đi\n3. Nói tiếp đi",
    "Nói tiếp đi\nNói tiếp đi\nNói tiếp đi",
    "\x60\x60\x60text\n@@Nói tiếp đi|Nói tiếp đi|Nói tiếp đi\n\x60\x60\x60",
])
def test_duplicate_options_and_common_formats(raw):
    parsed=parse_suggestions(raw)
    assert parsed==["Nói tiếp đi"]*3
    final,meta=finalize_suggestions(parsed,"Nói tiếp đi","vi",{"actual_model":"configured","fallback_used":False})
    assert final==parsed
    assert not meta["fallback_used"]
    assert meta["actual_model"]=="configured"


def test_valid_options_are_kept_when_one_is_placeholder():
    parsed=parse_suggestions("@@Mình muốn kể thêm|question 2|Mình muốn kể thêm")
    assert parsed==["Mình muốn kể thêm"]*2
    final,meta=finalize_suggestions(parsed,"Mình muốn kể thêm","vi",{"actual_model":"configured"})
    assert final[:2]==parsed
    assert len(final)==3
    assert meta["actual_model"]=="configured"
    assert "2 usable suggestions" in meta["fallback_reason"]


def test_long_options_and_user_questions_are_not_rejected():
    text="Mình muốn bạn giải thích kỹ hơn phần này và cho mình một ví dụ cụ thể để có thể hiểu cách áp dụng trong thực tế."
    parsed=parse_suggestions(f"@@{text}|Bạn có muốn nghe mình kể tiếp không?|Bạn đang nghĩ gì?")
    assert parsed==[text,"Bạn có muốn nghe mình kể tiếp không?","Bạn đang nghĩ gì?"]


def test_placeholders_and_arbitrary_prose_are_not_options():
    assert parse_suggestions("@@question 1|question 2|question 3")==[]
    assert parse_suggestions("An explanation instead of suggestions")==[]
    assert parse_suggestions('{"suggestions":[null,1,{}]}')==[]

def test_character_service_offers_are_replaced_but_user_questions_preserved():
    final,meta=finalize_suggestions(
        ["How can I help you?", "What are you thinking?", "Tell me more about yourself."],
        "I want to talk with you", "en", {"actual_model":"configured"})
    assert final[:2]==["What are you thinking?", "Tell me more about yourself."]
    assert "How can I help you?" not in final
    assert len(final)==3
    assert meta["fallback_used"]
    final,_=finalize_suggestions(["Bạn muốn tôi giúp gì?", "Bạn đang nghĩ gì?", "Kể mình nghe tiếp nhé"],
        "Mình muốn nói chuyện", "vi", {})
    assert "Bạn muốn tôi giúp gì?" not in final
    assert "Bạn đang nghĩ gì?" in final


def test_user_speaker_lock_survives_custom_suggestion_prompt(monkeypatch):
    from character_chat import engine
    from character_chat.presets import presets
    monkeypatch.setattr(engine,"ADMIN_SUGGESTION_INSTRUCTION","Custom suggestion prompt")
    prompt=engine.suggestion_prompt([],presets()[0],"Hello")
    assert prompt[0]["content"]=="Custom suggestion prompt"
    assert "REQUIRED SPEAKER: the human USER" in prompt[1]["content"]
    assert presets()[0].name in prompt[1]["content"]

def test_suggestion_history_attributes_character_and_user_and_locks_language():
    import json
    from character_chat.engine import suggestion_prompt
    from character_chat.schemas import CharacterSpec
    prompt=suggestion_prompt([{"role":"assistant","content":"Anh có thể giúp em gì?"},
        {"role":"user","content":"Em muốn nghe ý kiến của anh."}],CharacterSpec(name="Ruby"),"Em nên làm gì tiếp?")
    assert "Vietnamese (vi)" in prompt[1]["content"]
    assert "never reverse anh/em" in prompt[1]["content"]
    context=json.loads(prompt[-1]["content"])
    assert context["suggestion_sender"]=="HUMAN_USER"
    assert context["suggestion_recipient"]=="Ruby"
    assert context["recent_dialogue"][0]["speaker"]=="CHARACTER"
    assert context["recent_dialogue"][1]["speaker"]=="HUMAN_USER"
    assert "role" not in context["recent_dialogue"][0]

def test_suggestion_language_uses_latest_user_even_when_history_is_vietnamese():
    from character_chat.engine import suggestion_prompt
    from character_chat.schemas import CharacterSpec
    prompt=suggestion_prompt([{"role":"assistant","content":"Chào bạn!"}],
        CharacterSpec(name="Ruby"),"What should I do next?")
    assert "English (en)" in prompt[1]["content"]

def test_partial_suggestions_do_not_keep_wrong_language_fields():
    final,meta=finalize_suggestions(["What do you think?","Anh đang nghĩ gì?"],
        "Em muốn hỏi anh chuyện này.","vi",{})
    assert "What do you think?" not in final
    assert "Anh đang nghĩ gì?" in final
    assert len(final)==3
    assert "language mismatch" in meta["fallback_reason"]

def test_roleplay_suggestions_lock_ownership_of_character_emotions():
    from character_chat.engine import suggestion_prompt
    from character_chat.schemas import CharacterSpec
    prompt=suggestion_prompt([{"role":"assistant","content":"Tôi đang khó chịu."}],
        CharacterSpec(name="Ruby"),"Cậu đang giận tôi à?")
    assert "never transfer the character's anger or concern to the user" in prompt[1]["content"]
    assert "Do not answer latest_user_message" in prompt[-1]["content"]
    assert "Wrong CHARACTER follow-ups" in prompt[1]["content"]


def test_suggestion_context_is_bounded_for_long_single_chat():
    import json
    from character_chat.engine import suggestion_prompt
    from character_chat.presets import presets
    history=[{"role":"user" if index%2==0 else "assistant","content":f"turn-{index} "+("x"*3000)} for index in range(30)]
    history.append({"role":"system","content":"Large hidden persona "*1000})
    prompt=suggestion_prompt(history,presets()[0],"Em "+("x"*3000)+" anh?",["q"*500]*8)
    context=json.loads(prompt[-1]["content"])
    assert len(context["recent_dialogue"])==4
    assert context["recent_dialogue"][0]["text"].startswith("turn-26")
    assert all(len(item["text"])<=243 for item in context["recent_dialogue"])
    assert len(context["latest_user_message"])<=603
    assert context["latest_user_message"].startswith("Em ") and context["latest_user_message"].endswith(" anh?")
    assert all(len(item)<=120 for item in context["previous_suggestions"])
    assert len(context["character_description"])<=240
    assert "Large hidden persona" not in prompt[-1]["content"]
    assert context["suggestion_sender"]=="HUMAN_USER"


def test_suggestion_lock_covers_user_anh_character_em():
    import json
    from character_chat.engine import suggestion_prompt
    from character_chat.schemas import CharacterSpec
    prompt=suggestion_prompt([
        {"role":"user","content":"Anh muốn kể cho em nghe chuyện hôm nay."},
        {"role":"assistant","content":"Em muốn nghe anh kể."},
    ],CharacterSpec(name="Ruby"),"Anh kể cho em nghe nhé?")
    lock=prompt[1]["content"]
    assert "HUMAN_USER calls themselves anh and addresses CHARACTER as em" in lock
    assert "Em thích nghe anh kể chuyện gì nhất mỗi ngày?" in lock
    assert "without personal pronouns rather than guessing anh/em" in lock
    context=json.loads(prompt[-1]["content"])
    assert context["recent_dialogue"][0]["speaker"]=="HUMAN_USER"
    assert context["recent_dialogue"][1]["speaker"]=="CHARACTER"
