import json
import random
from types import SimpleNamespace
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from character_chat.divination import DECK, draw_cards, prepare_tarot, bootstrap_tuvi_models
from character_chat.models import Base, User, Room, ModelConfig, AppSetting
from character_chat.assistant_prompts import ASSISTANT_PROMPTS

def test_full_deck_and_packaged_images():
    assert len(DECK) == len({c["id"] for c in DECK}) == 78
    for card in DECK:
        assert Path("image", card["image"].removeprefix("/character-images/")).is_file()

def test_shuffle_without_replacement_and_both_orientations():
    draws = [draw_cards(10, random.Random(seed)) for seed in range(30)]
    assert all(len({c["id"] for c in cards}) == 10 for cards in draws)
    assert {c["reversed"] for cards in draws for c in cards} == {False, True}
    assert len({tuple(c["id"] for c in cards) for cards in draws}) == 30
    with pytest.raises(ValueError):
        draw_cards(79)

def test_followup_reuses_saved_reading_but_explicit_redraw_changes_it():
    _, first = prepare_tarot("assistant_tarot", "Rút 3 lá", [])
    history = [SimpleNamespace(sender_type="character", sources=json.dumps([first]))]
    prompt, followup = prepare_tarot("assistant_tarot", "Giải thích rõ lá thứ hai", history)
    assert followup == first and first["cards"][1]["name"] in prompt
    assert prepare_tarot("assistant_tarot", "Giải thích trải bài vừa rút", history)[1] == first
    _, next_draw = prepare_tarot("assistant_tarot", "Rút lại 1 lá", history)
    assert next_draw["reading_id"] != first["reading_id"]
    assert len(next_draw["cards"]) == 1
    assert prepare_tarot("assistant_tuvi", "Rút bài", history) == ("", None)
    assert prepare_tarot("assistant_tarot", "Tarot là gì?", [])[1] is None

def test_prompts_keep_distinct_tasks_and_uncertainty():
    assert "TAROT MODE ONLY" in ASSISTANT_PROMPTS["assistant_tarot"]
    assert "TỬ VI / BÁT TỰ MODE ONLY" in ASSISTANT_PROMPTS["assistant_tuvi"]

def test_model_assignment_bootstrap_does_not_overwrite_cms_edits():
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(engine)() as db:
        db.add(ModelConfig(id="m",name="Model",provider="api",model_id="wire",api_base="https://test.invalid"))
        db.add(AppSetting(key="model_profile:m",value=json.dumps({"purposes":["assistant_tarot","assistant_tarot_fallback"]})))
        db.commit()
        getter=lambda db,m:json.loads(db.get(AppSetting,"model_profile:"+m.id).value)
        bootstrap_tuvi_models(db,getter)
        assert "assistant_tuvi" in getter(db,db.get(ModelConfig,"m"))["purposes"]
        db.get(AppSetting,"model_profile:m").value=json.dumps({"purposes":["assistant_tarot"]});db.commit()
        bootstrap_tuvi_models(db,getter)
        assert getter(db,db.get(ModelConfig,"m"))["purposes"] == ["assistant_tarot"]
    engine.dispose()

def test_tarot_response_is_persisted_and_tuvi_never_draws(monkeypatch):
    import character_chat.main as main
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session=sessionmaker(engine,expire_on_commit=False)
    with Session() as db:
        db.add(User(id="u"))
        db.add(Room(id="tarot-room",user_id="u",name=main.ASSISTANT_ROOM_PREFIX+"assistant_tarot:Tarot"))
        db.add(Room(id="tuvi-room",user_id="u",name=main.ASSISTANT_ROOM_PREFIX+"assistant_tuvi:Tử vi"))
        db.add(ModelConfig(id="m",name="Model",provider="api",model_id="wire",api_base="https://test.invalid"))
        db.add(AppSetting(key="model_profile:m",value=json.dumps({"purposes":["assistant_tarot","assistant_tuvi","assistant_suggestion"]})))
        db.commit()
    def dependency():
        with Session() as db:
            yield db
    calls=[]
    def chat(*args,**kwargs):
        calls.append(args)
        return ("@@Bạn thấy sao?|Điều đó có nghĩa gì?|Mình nên làm gì?" if args[2]=="assistant_suggestion" else "Diễn giải để chiêm nghiệm.", {"actual_model":"test","latency_ms":1})
    monkeypatch.setattr(main,"run_assistant_model_chain",chat)
    monkeypatch.setattr(main,"ensure_safe_content",lambda *args,**kwargs:None)
    main.app.dependency_overrides[main.db_session]=dependency
    main.app.dependency_overrides[main.current_user]=lambda:"u"
    try:
        client=TestClient(main.app)
        # CMS presentation is read fresh and never exposes private profile fields.
        with Session() as db:
            db.add(AppSetting(key="assistant_profile:assistant_tarot", value=json.dumps(
                {"title": "CMS Tarot", "greeting": "Saved greeting", "starters": ["Saved starter"],
                 "private_field": "must-not-leak"})))
            db.commit()
        public = client.get("/v1/assistant/profiles")
        assert public.status_code == 200
        profile = public.json()["items"]["assistant_tarot"]
        assert profile["title"] == "CMS Tarot" and profile["greeting"] == "Saved greeting"
        assert "private_field" not in profile
        with Session() as db:
            db.get(AppSetting, "assistant_profile:assistant_tarot").value = json.dumps({"title": "Changed"})
            db.commit()
        assert client.get("/v1/assistant/profiles").json()["items"]["assistant_tarot"]["title"] == "Changed"
        # Explicit new conversations do not reuse the existing specialised room.
        for mode in ("assistant_tarot", "assistant_tuvi"):
            created = client.post("/v1/assistant/chats", json={"mode": mode, "new_session": True})
            assert created.status_code == 200, created.text
            assert created.json()["is_new"] is True
            assert created.json()["id"] not in ("tarot-room", "tuvi-room")
        response=client.post("/v1/assistant/chats/tarot-room/messages",json={"message":"Rút 3 lá"})
        assert response.status_code==200,response.text
        spread=next(s for s in response.json()["sources"] if s.get("kind")=="tarot")
        history=client.get("/v1/assistant/chats/tarot-room/messages").json()
        assert history[-1]["sources"][-1] == spread
        assert "authoritative draws" in calls[0][5]
        assert client.get("/v1/assistant/chats/tarot-room/tarot").json()["remaining"] == 75
        followup = client.post("/v1/assistant/chats/tarot-room/messages",json={"message":"Giải thích rõ lá thứ hai"})
        assert followup.json()["sources"][-1]["reading_id"] == spread["reading_id"]
        assert client.get("/v1/assistant/chats/tarot-room/tarot").json()["remaining"] == 75
        next_response = client.post("/v1/assistant/chats/tarot-room/messages",json={"message":"Rút tiếp 3 lá"})
        next_spread = next_response.json()["sources"][-1]
        assert not {c["id"] for c in spread["cards"]} & {c["id"] for c in next_spread["cards"]}
        assert next_spread["session_id"] == spread["session_id"]
        monkeypatch.setattr(main,"Session",Session)
        monkeypatch.setattr(main,"credential_for_model",lambda *args:"test-key")
        monkeypatch.setattr(main,"model_circuit_remaining",lambda *args:0)
        monkeypatch.setattr(main,"chat_stream",lambda *args:iter(["Diễn giải bài.",{"_stream_status":"complete"}]))
        streamed = client.post("/v1/assistant/chats/tarot-room/messages/stream",json={"message":"Rút tiếp 1 lá"})
        assert streamed.status_code == 200,streamed.text
        assert streamed.text.index("event: tarot") < streamed.text.index("event: delta")
        stream_cards = json.loads(streamed.text.split("event: tarot",1)[1].splitlines()[1].removeprefix("data: "))
        assert stream_cards["remaining"] == 71
        history = client.get("/v1/assistant/chats/tarot-room/messages").json()
        assert history[-1]["sources"][-1]["reading_id"] == stream_cards["reading_id"]
        reset = client.post("/v1/assistant/chats/tarot-room/tarot/reset")
        assert reset.status_code == 200 and reset.json()["remaining"] == 78
        assert client.get("/v1/assistant/chats/tarot-room/messages").json() == []
        assert reset.json()["session_id"] != spread["session_id"]
        assert client.post("/v1/assistant/chats/tuvi-room/tarot/reset").status_code == 400
        main.app.dependency_overrides[main.current_user]=lambda:"another-user"
        assert client.post("/v1/assistant/chats/tarot-room/tarot/reset").status_code == 404
        main.app.dependency_overrides[main.current_user]=lambda:"u"
        response=client.post("/v1/assistant/chats/tuvi-room/messages",json={"message":"Cần ngày giờ sinh gì?"})
        assert response.status_code==200,response.text
        assert not any(s.get("kind")=="tarot" for s in response.json()["sources"])
    finally:
        main.app.dependency_overrides.clear();engine.dispose()

def test_deck_exhaustion_persistence_and_reset():
    from fastapi import HTTPException
    from character_chat.divination import draw_from_session, reset_session
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session=sessionmaker(engine)
    picked=[]
    with Session() as db:
        for _ in range(7):
            result=draw_from_session(db,"room",10)
            picked += [card["id"] for card in result["cards"]]
        last=draw_from_session(db,"room",8)
        picked += [card["id"] for card in last["cards"]]
        assert last["remaining"] == 0 and len(set(picked)) == 78
    with Session() as db:
        with pytest.raises(HTTPException) as error:
            draw_from_session(db,"room",1)
        assert error.value.status_code == 409
        state=reset_session(db,"room");db.commit()
        first=draw_from_session(db,"room",1)
        assert first["remaining"] == 77 and first["session_id"] == state["session_id"]
    engine.dispose()
