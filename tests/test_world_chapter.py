"""Chapter invariants: useful guidance, private reports and old-save compatibility."""
from copy import deepcopy
import pytest
from character_chat import world_engine as engine, world_chapter as chapter


def state(language="en", size=3):
    return engine.fresh(engine.seed(),[{"id":str(i),"name":f"Actor {i}","origin":"private"} for i in range(size)],language,"fresh",[])


@pytest.mark.parametrize("language",["vi","en"])
@pytest.mark.parametrize("size",[1,2,3])
def test_guidance_completes_linked_requests_for_any_party(language,size):
    s=state(language,size)
    for _ in range(45):
        if chapter.projection(s)["completed"]==3:break
        step=chapter.guidance(s)
        assert step["action"]
        s,_=engine.advance(s,step["action"],step["value"],speaker="0",roll=lambda:20)
    assert chapter.projection(s)["completed"]==3
    assert len(s["clues"])==4
    assert sum(s["trust"].values())==6
    s,_=engine.advance(s,"go","observatory")
    before=deepcopy(s)
    for ending in ("protect","reveal","seal"):
        ended,_=engine.advance(s,"resolve",ending)
        assert ended["ending"]["id"]==ending
    assert s==before


def test_report_does_not_tell_uninvolved_character_or_repeat_rewards():
    s=state()
    with pytest.raises(ValueError):engine.advance(s,"accept","mirror")
    s,_=engine.advance(s,"accept","witness")
    with pytest.raises(ValueError):engine.advance(s,"report","witness")
    s,_=engine.advance(s,"visit","1")
    s,_=engine.advance(s,"search",speaker="1")
    assert not engine.knowledge(s,"0")[1]
    assert not engine.knowledge(s,"2")[1]
    s,_=engine.advance(s,"return")
    assert s["location"]=="square"
    s,_=engine.advance(s,"report","witness")
    assert engine.knowledge(s,"0")[1]
    assert not engine.knowledge(s,"2")[1]
    assert s["clues"][0]["scope"]=="witnessed"
    before=deepcopy(s)
    with pytest.raises(ValueError):engine.advance(s,"report","witness")
    assert s==before and s["trust"]["0"]==2


def test_shortcuts_are_connected_and_return_restores_encounter():
    s=state()
    s,_=engine.advance(s,"visit","1")
    s,_=engine.advance(s,"visit","2")
    assert s["location"]=="tower" and s["encounter"]=="2"
    s,_=engine.advance(s,"return")
    assert s["location"]=="tavern" and s["encounter"]=="1"
    path=chapter.route(s,"tower",engine.LOCATIONS)
    graph={p[0]:p[6] for p in engine.LOCATIONS}
    assert all(b in graph[a] for a,b in zip(path,path[1:]))
    with pytest.raises(ValueError):engine.advance(s,"visit","someone-else")
    with pytest.raises(ValueError):engine.advance(s,"go","unknown")


def test_hints_and_smalltalk_do_not_award_clues_or_trust():
    s=state()
    for i in range(3):
        s,_=engine.advance(s,"hint")
        assert s["turn"]==0 and s["hint_level"]==i+1
    assert "secret" not in {e["id"] for e in engine.knowledge(s)[0]}
    s,_=engine.advance(s,"talk","personal",speaker="1")
    assert not s["clues"] and sum(s["trust"].values())==0
    s,_=engine.advance(s,"talk","evidence",speaker="2")
    assert "lamplighter" not in s["history"][-1]["text"]


def test_legacy_checkpoint_projects_and_plays_without_chapter_fields():
    s=state()
    for key in ("quests","encounter","return_trail","hint_level"):
        s.pop(key,None)
    assert chapter.projection(s)["completed"]==0
    new,_=engine.advance(s,"accept","witness")
    assert new["quests"]=={"witness":"active"}
    assert "quests" not in s


def test_interview_gives_attributed_evidence_without_duplicate_rewards():
    s=state()
    s,event=engine.advance(s,"interview",speaker="0")
    assert event["speaker"]=="Actor 0" and len(s["clues"])==1
    s,_=engine.advance(s,"visit","1")
    s,event=engine.advance(s,"interview",speaker="1")
    assert event["speaker"]=="Actor 1" and len(s["clues"])==2
    private=next(c for c in s["clues"] if c["location"]=="tavern")
    assert private["scope"]=="witnessed" and private["witnesses"]==["user","1"]
    assert not any(c["id"]==private["id"] for c in engine.knowledge(s,"0")[1])
    again,_=engine.advance(s,"interview",speaker="1")
    assert len(again["clues"])==2 and again["trust"]==s["trust"]


def test_interview_requires_a_real_encounter_and_can_complete_a_request():
    s=state()
    with pytest.raises(ValueError):engine.advance(s,"interview",speaker="1")
    s,_=engine.advance(s,"accept","witness")
    s,_=engine.advance(s,"visit","1")
    s,_=engine.advance(s,"interview",speaker="1")
    s,_=engine.advance(s,"return")
    s,_=engine.advance(s,"report","witness")
    assert s["quests"]["witness"]=="done"
