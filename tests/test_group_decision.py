import httpx
import pytest
from character_chat import group_decision,group_routing
from character_chat.schemas import CharacterSpec,Identity

def cast():
    return [CharacterSpec(id=str(i),name=name,description=role,identity=Identity(role=role))
            for i,(name,role) in enumerate([("Morgan","career advisor"),("Luna","artist"),("Mira","doctor")])]

@pytest.fixture
def decision_env(monkeypatch):
    monkeypatch.setenv("GROUP_ROUTER_MODE","decision")
    monkeypatch.setenv("GROUP_ROUTER_TRANSPORT","http")
    monkeypatch.setenv("GROUP_ROUTER_API_BASE","http://fixture")
    monkeypatch.setenv("GROUP_ROUTER_MIN_PROBABILITY",".65")

def mock_service(monkeypatch,probabilities):
    actual=httpx.Client
    calls=[]
    def respond(request):
        calls.append(request)
        answers={f"speaker_{i}":{"choice":"A" if p>.5 else "B","probabilities":{"A":p,"B":1-p}}
                 for i,p in enumerate(probabilities)}
        return httpx.Response(200,json={"answers":answers})
    monkeypatch.setattr(group_decision.httpx,"Client",lambda **kw:actual(transport=httpx.MockTransport(respond),**kw))
    return calls

@pytest.mark.parametrize("probabilities,count",[
    ([.9,.1,.1],1),([.9,.8,.1],2),([.9,.8,.75],3),
])
def test_decision_selects_one_through_all(monkeypatch,decision_env,probabilities,count):
    calls=mock_service(monkeypatch,probabilities)
    plan=group_routing.plan_selected_group("What do you think of my plans?",cast())
    assert len(plan.speakers)==count
    assert plan.router=="jev_compatible"
    assert len(calls)==1 and len(__import__("json").loads(calls[0].content)["questions"])==3
    assert plan.metadata()["decision_scores"]["0"]==.9

@pytest.mark.parametrize("message",["@Luna answer please","Everyone, what do you think?","Both of you compare career and art"])
def test_explicit_selection_does_not_wait_for_model(monkeypatch,decision_env,message):
    monkeypatch.setattr(group_decision,"select_speakers",lambda *a,**kw:pytest.fail("Explicit requests must skip model"))
    assert group_routing.plan_selected_group(message,cast()).router=="local_rules_topics_v1"

def test_no_confident_speaker_falls_back(monkeypatch,decision_env):
    mock_service(monkeypatch,[.4,.5,.6])
    plan=group_routing.plan_selected_group("Hello there",cast())
    assert len(plan.speakers)>=1 and plan.router=="local_rules_topics_v1"
    assert plan.decision["decision_fallback"]=="no_confident_speaker"

@pytest.mark.parametrize("error",[httpx.ReadTimeout("timeout"),httpx.ConnectError("down")])
def test_timeout_or_connection_failure_falls_back(monkeypatch,decision_env,error):
    actual=httpx.Client
    def fail(request):raise error
    monkeypatch.setattr(group_decision.httpx,"Client",lambda **kw:actual(transport=httpx.MockTransport(fail),**kw))
    plan=group_routing.plan_selected_group("Hello there",cast())
    assert plan.router=="local_rules_topics_v1" and plan.decision["decision_fallback"]

def test_missing_answers_never_select(monkeypatch,decision_env):
    mock_service(monkeypatch,[.9])
    plan=group_routing.plan_selected_group("Hello there",cast())
    assert plan.router=="local_rules_topics_v1"
    assert plan.decision["decision_fallback"]=="invalid_or_unavailable_response"

def test_default_local_mode_never_calls_service(monkeypatch):
    monkeypatch.delenv("GROUP_ROUTER_MODE",raising=False)
    monkeypatch.setattr(group_decision,"select_speakers",lambda *a,**kw:pytest.fail("Local mode must skip service"))
    assert group_routing.plan_selected_group("Hello",cast()).router=="local_rules_topics_v1"

def test_short_context_and_topic_are_sent_as_data():
    payload=group_decision.build_request("x"*5000,cast(),[
        {"sender_type":"user","text":"old","character_id":None}]*20,"Shared topic","Group title")
    assert len(payload["state"]["latest_user_message"])==1200
    assert len(payload["state"]["recent_dialogue"])==4
    assert payload["state"]["topic"]=="Shared topic"
    assert all(question["type"]=="choice" for question in payload["questions"].values())


def test_uniform_scores_fall_back_instead_of_selecting_everyone(monkeypatch,decision_env):
    mock_service(monkeypatch,[.9,.91,.89])
    plan=group_routing.plan_selected_group("I need health advice",cast())
    assert plan.router=="local_rules_topics_v1"
    assert plan.decision["decision_fallback"]=="indistinguishable_decisions"


def test_modal_transport_uses_private_worker_without_http(monkeypatch,decision_env):
    import sys
    from types import SimpleNamespace
    monkeypatch.setenv("GROUP_ROUTER_TRANSPORT","modal")
    monkeypatch.delenv("GROUP_ROUTER_API_BASE")
    captured={}
    class Call:
        def get(self,timeout):
            captured["timeout"]=timeout
            return {"answers":{f"speaker_{i}":{"probabilities":{"A":p,"B":1-p}} for i,p in enumerate([.9,.8,.1])}}
    class Method:
        def spawn(self,payload):
            captured["payload"]=payload
            return Call()
    def from_name(app,name):
        captured["app"]=app;captured["class"]=name
        return lambda:SimpleNamespace(decide=Method())
    monkeypatch.setitem(sys.modules,"modal",SimpleNamespace(Cls=SimpleNamespace(from_name=from_name)))
    selected,meta,error=group_decision.select_speakers("What do you think?",cast())
    assert not error and len(selected)==2
    assert captured["app"]=="character-chat-group-router"
    assert captured["class"]=="GroupRouter"
    assert captured["timeout"]<=5
