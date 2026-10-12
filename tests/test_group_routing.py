import pytest
from character_chat.group_routing import plan_group
from character_chat.schemas import CharacterSpec,Identity

def cast():
    return [
        CharacterSpec(id="work",name="Morgan",description="Business career and job advice",identity=Identity(role="practical career advisor")),
        CharacterSpec(id="art",name="Luna",description="Creative artist who loves music and art",identity=Identity(role="artist")),
        CharacterSpec(id="health",name="Mira",description="Doctor and health specialist",identity=Identity(role="doctor")),
        CharacterSpec(id="study",name="Leo",description="School teacher helping with study",identity=Identity(role="teacher")),
    ]

def history(ids):
    items=[]
    for i,id in enumerate(ids):
        items.extend([{"sender_type":"user","text":f"Earlier topic {i}","character_id":None},
                      {"sender_type":"character","text":"Previous response","character_id":id}])
    return items

def test_routing_never_calls_llm(monkeypatch):
    from character_chat.engine import llm,route
    monkeypatch.setattr(llm,"json",lambda *a,**k:pytest.fail("Routing must not call LLM"))
    assert len(route("Hello",cast()))==1

@pytest.mark.parametrize("message,target",[
    ("@Luna tell me a story","art"),
    ("Mira, what do you think?","health"),
    ("Tôi muốn hỏi về công việc","work"),
    ("I need career advice","work"),
    ("我的工作怎么办","work"),
    ("学校で勉強したい","study"),
    ("건강 상담","health"),
    ("សុខភាព","health"),
    ("အလုပ်","work"),
])
def test_selects_addressed_or_relevant_character(message,target):
    assert plan_group(message,cast()).speakers[0].id==target

def test_name_substrings_do_not_count_as_mentions():
    chars=cast()
    chars[0].name="Ann"
    assert plan_group("Cannot finish my homework",chars).speakers[0].id=="study"

def test_followup_stays_with_last_speaker():
    plan=plan_group("Tại sao?",cast(),history=history(["art","health"]))
    assert plan.speakers[0].id=="health"
    assert plan.reason=="followup"

def test_neutral_turns_rotate_without_forcing_off_topic_speakers():
    first=plan_group("Hello there",cast())
    second=plan_group("Hello there",cast(),history=history([first.speakers[0].id]))
    assert first.speakers[0].id!=second.speakers[0].id
    assert plan_group("Please advise me on my career",cast(),history=history(["work"])).speakers[0].id=="work"

def test_explicit_pair_and_exchange_instructions():
    plan=plan_group("@Morgan and @Luna, discuss my career",cast())
    assert [c.id for c in plan.speakers]==["work","art"]
    assert plan.interaction=="exchange"
    assert "ask Luna one concrete question" in plan.instruction("work")
    assert "preceding participant" in plan.instruction("art")

@pytest.mark.parametrize("message",["Mọi người cho tôi ý kiến nhé","Everyone, what do you think?","大家说说看","みんな、どう思う？"])
def test_everyone_is_explicit_exception(message):
    assert len(plan_group(message,cast()).speakers)==4

def test_mention_overrides_everyone_mode_for_compatibility():
    assert [c.id for c in plan_group("@Luna tell me more",cast(),"everyone").speakers]==["art"]

def test_spontaneous_pair_needs_context_and_obeys_cooldown():
    query="Should I choose a career in business or music and art?"
    assert len(plan_group(query,cast()).speakers)==1
    plan=plan_group(query,cast(),history=history(["work","study","health"]))
    assert len(plan.speakers)==2
    assert set(c.id for c in plan.speakers)=={"work","art"}
    recent=history(["work","study","health"])
    recent.append({"sender_type":"character","text":"A second perspective","character_id":"art"})
    assert len(plan_group(query,cast(),history=recent).speakers)==1

def test_requested_pair_can_override_cooldown():
    plan=plan_group("Both of you, compare career and art",cast(),history=history(["art"]))
    assert len(plan.speakers)==2

def test_invalid_selected_character_is_rejected():
    with pytest.raises(ValueError):plan_group("hello",cast(),"character:missing")


def test_spontaneous_exchange_can_start_after_two_turns():
    query="Should I choose a career in business or music and art?"
    plan=plan_group(query,cast(),history=history(["study","health"]))
    assert len(plan.speakers)==2 and plan.interaction=="exchange"
    assert "one concrete question" in plan.instruction(plan.speakers[0].id)
