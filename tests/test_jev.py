"""JEV contract and integration tests: no real provider calls or credentials."""
import json
import pytest
import httpx
from character_chat import jev, moderation, group_routing, engine
from character_chat.schemas import CharacterSpec
from test_worlds import world_client

@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "fixture-only")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    for name in jev.ENV_NAMES:
        if name not in {"JEV_API_KEY", "TYPESAFE_API_KEY"}:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(jev, "_cms_key", "")
    jev._cache.clear();jev._language_cache.clear()
    yield
    jev._cache.clear();jev._language_cache.clear()

def fake(monkeypatch, overrides=None, confidence=.99):
    calls=[]
    overrides=overrides or {}
    def handle(request):
        payload=json.loads(request.content)
        assert request.url==httpx.URL("https://api.typesafe.ai/v1/systemone")
        assert payload["model"]=="jev-latest"
        calls.append(payload)
        answers={}
        for name,q in payload["questions"].items():
            label=overrides.get(name, "unknown" if name=="language" else "neutral" if name=="emotion" else "none" if name=="relationship" else "allow")
            if name.startswith("speaker_"):label=overrides.get(name,"B")
            probs={k:(confidence if k==label else (1-confidence)/(len(q["criteria"])-1)) for k in q["criteria"]}
            answers[name]={"type":"choice","choice":label,"confidence":confidence,"probabilities":probs}
        return httpx.Response(200,json={"answers":answers})
    original=httpx.Client
    monkeypatch.setattr(jev.httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    return calls

def test_moderation_emotion_assistant_share_one_decision(monkeypatch):
    calls=fake(monkeypatch,{"emotion":"sad"})
    moderation.ensure_safe_content("Hôm nay tôi rất buồn.")
    assert engine.detect_user_affect("Hôm nay tôi rất buồn.")=="sad"
    assert "sad" in jev.affect_hint("Hôm nay tôi rất buồn.")
    assert len(calls)==1
    assert "fixture-only" not in json.dumps(calls)

@pytest.mark.parametrize("category", list(jev.POLICY))
def test_policy_applies_without_keyword_prefilter(monkeypatch,category):
    fake(monkeypatch,{category:"block"})
    with pytest.raises(ValueError,match=category):
        moderation.ensure_safe_content("Một câu không chứa keyword cũ.")

def test_uncertain_or_unavailable_never_allows(monkeypatch):
    fake(monkeypatch,confidence=.5)
    with pytest.raises(ValueError):moderation.ensure_safe_content("hello")
    jev._cache.clear();jev._language_cache.clear()
    monkeypatch.setattr(jev,"decide",lambda *a: (_ for _ in ()).throw(jev.JevUnavailable("timeout")))
    with pytest.raises(ValueError,match="chưa khả dụng"):moderation.ensure_safe_content("hello")
    assert engine.detect_user_affect("I am sad")=="sad"

def test_real_router_and_explicit_choice(monkeypatch):
    calls=fake(monkeypatch,{"speaker_0":"B","speaker_1":"A"})
    cast=[CharacterSpec(id="a",name="Aster"),CharacterSpec(id="b",name="Beryl")]
    plan=group_routing.plan_selected_group("Can someone help me think?",cast)
    assert plan.router=="typesafe_jev" and [c.id for c in plan.speakers]==["b"]
    before=len(calls)
    assert group_routing.plan_selected_group("@Aster help",cast).speakers[0].id=="a"
    assert len(calls)==before

def test_router_failure_uses_local_not_modal(monkeypatch):
    monkeypatch.setattr(jev,"decide",lambda *a: (_ for _ in ()).throw(jev.JevUnavailable("timeout")))
    cast=[CharacterSpec(id="a",name="Aster"),CharacterSpec(id="b",name="Beryl")]
    plan=group_routing.plan_selected_group("Hello",cast)
    assert plan.router=="local_rules_topics_v1" and plan.decision["decision_fallback"]=="jev_unavailable"

def test_no_key_preserves_old_behavior_and_disabled_bypasses(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY","")
    monkeypatch.setattr(jev,"decide",lambda *a:pytest.fail("No remote call"))
    moderation.ensure_safe_content("hello")
    monkeypatch.setenv("JEV_API_KEY","fixture-only")
    monkeypatch.setenv("JEV_ENABLED","false")
    moderation.ensure_safe_content("hello")

def test_all_chunks_checked_and_bad_wire_rejected(monkeypatch):
    calls=fake(monkeypatch)
    jev.require_safe("a"*6500)
    assert len(calls)==2 and sum(len(c["state"]["text"]) for c in calls)>6500
    jev._cache.clear();jev._language_cache.clear()
    original=httpx.Client
    # Replace the prior mocked constructor with an independent real class.
    from httpx import _client
    monkeypatch.setattr(jev.httpx,"Client",lambda **kw:_client.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={"answers":{}})),**kw))
    with pytest.raises(jev.JevUnavailable):jev.inspect_text("x")

def test_never_send_key_to_other_host(monkeypatch):
    monkeypatch.setenv("JEV_API_BASE","https://not-typesafe.example")
    with pytest.raises(jev.JevUnavailable,match="invalid_endpoint"):jev.inspect_text("hello")

def test_crisis_context_and_no_diagnosis(monkeypatch):
    calls=fake(monkeypatch,{"emotion":"sad"})
    moderation.ensure_safe_content("I need help",allow_crisis_support=True)
    assert "diagnose" in jev.affect_hint("I need help",True)
    assert len(calls)==1 and calls[0]["state"]["help_seeking_allowed"] is True

def test_cms_key_is_encrypted_auth_required_and_removable(world_client,monkeypatch):
    client,factory,_=world_client
    from character_chat import main
    from character_chat.models import AppSetting
    monkeypatch.setenv("JEV_API_KEY","")
    monkeypatch.setenv("DOCS_PASSWORD","test-encryption-only")
    path="/v1/admin/credentials/bases"
    body={"api_base":"https://api.typesafe.ai","api_key":"cms-fixture-not-real"}
    assert client.put(path,json=body).status_code==401
    main.app.dependency_overrides[main.docs_auth]=lambda:None
    r=client.put(path,json=body)
    assert r.status_code==200,r.text
    assert jev.enabled() and jev.api_key()==body["api_key"]
    assert body["api_key"] not in client.get("/v1/admin/credentials").text
    with factory() as db:
        row=db.get(AppSetting,"credential:base:"+r.json()["id"])
        assert row.value!=body["api_key"] and main.decrypt_admin_secret(row.value)==body["api_key"]
        jev.set_cms_key("")
        main.apply_model_registry(db)
        assert jev.api_key()==body["api_key"]
    assert client.delete(path+"/"+r.json()["id"]).status_code==200
    assert not jev.enabled()

def test_language_reused_from_moderation_and_timeout_fallback(monkeypatch):
    calls=fake(monkeypatch,{"language":"my"})
    text="test Burmese language signal"
    moderation.ensure_safe_content(text)
    suggestions,meta=engine.finalize_suggestions([],text,"en",{"fallback_reason":"suggestion timeout"})
    assert len(calls)==1 and len(suggestions)==3
    assert all(engine.detect_message_language(s,"unknown",use_jev=False)=="my" for s in suggestions)
    assert meta["actual_model"]=="local_static" and "timeout" in meta["fallback_reason"]

@pytest.mark.parametrize("language",["vi","en","zh","ja","ko","my","km"])
def test_language_static_fallback_each_ui_language(monkeypatch,language):
    calls=fake(monkeypatch,{"language":language})
    suggestions,_=engine.finalize_suggestions([],"fixture input",language,{})
    assert len(suggestions)==3
    assert all(engine.detect_message_language(s,language,use_jev=False)==language for s in suggestions)
    assert len(calls)==1

def test_language_failure_cached_and_keeps_local_default(monkeypatch):
    calls=[]
    def unavailable(*a):
        calls.append(1)
        raise jev.JevUnavailable("timeout")
    monkeypatch.setattr(jev,"decide",unavailable)
    assert engine.detect_message_language("xin chào","en")=="vi"
    assert engine.detect_message_language("xin chào","en")=="vi"
    assert len(calls)==1


def test_output_speech_metadata_never_calls_jev_while_streaming(monkeypatch):
    from character_chat.speech_language import speech_info,detect_speech_language,LanguageStream
    from character_chat.schemas import CharacterSpec
    calls=[]
    def remote(*a,**kw):
        calls.append(1)
        raise AssertionError("Output chunks must not call JEV")
    monkeypatch.setattr(jev,"detect_language",remote)
    card=CharacterSpec(name="Test")
    text=""
    for part in ("Hello",", I"," am"," here",". How"," are"," you"," today?"):
        text+=part
        speech_info(text,[{"text":text,"language":"en"}],card)
        detect_speech_language(text,"en")
    assert calls==[]
