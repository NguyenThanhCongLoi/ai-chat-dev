"""AI World: state transitions, ACL, replay/concurrency and provider boundaries."""
import json
import time
from copy import deepcopy
import pytest
from character_chat import academy
from character_chat.models import AppSetting, ModelConfig
from test_worlds import world_client
import character_chat.main as main

def state(lang="vi"):
 return academy.fresh("alice",["a","b","c","d"],lang)

@pytest.mark.parametrize("lang",["vi","en"])
@pytest.mark.parametrize("ending",["remember","protect"])
def test_complete_story_and_persisted_consequences(lang,ending):
 s=state(lang);before=deepcopy(s)
 with pytest.raises(ValueError):academy.advance(s,"visit","tower")
 assert s==before
 s=academy.advance(s,"choice","investigate")
 s=academy.advance(s,"choice","reconcile")
 assert s["relationships"][academy.pair("a","b")]["trust"]==38
 s=academy.advance(s,"visit","garden")
 s=academy.advance(s,"choice","restore")
 assert "tower" in s["unlocked"] and "lens" in s["inventory"]
 assert len(academy.secrets(s,"c"))>=1
 s=academy.advance(s,"visit","tower")
 s=academy.advance(s,"choice",ending)
 assert s["ending_text"] and s["ending"]==ending and len(s["completed"])==3 and "ticket" in s["inventory"]
 with pytest.raises(ValueError):academy.advance(s,"choice",ending)
 assert len(s["timeline"])>=5

def test_memory_visibility_and_locked_secret_never_in_context():
 s=state()
 assert academy.context(s,"a")["secrets"]==[]
 academy.line(s,"user","LIBRARY_PRIVATE")
 academy.observe(s,"private","LIBRARY_SECRET",["a","b"])
 assert "LIBRARY_SECRET" not in json.dumps(academy.context(s,"c"))
 assert "LIBRARY_PRIVATE" not in json.dumps(academy.context(s,"c"))
 s=academy.advance(s,"choice","investigate")
 assert not academy.secrets(s,"a")
 s=academy.advance(s,"gift","tea","a")
 assert academy.secrets(s,"a") and not academy.secrets(s,"b")

def test_router_selects_present_mentions_and_never_whole_cast():
 s=state();names=dict(a="Ruby",b="Selene",c="Kael",d="Mira")
 assert academy.choose_speakers(s,"Ruby and Selene",names)==["a","b"]
 assert len(academy.choose_speakers(s,"Everyone speak",names))==1
 assert "c" not in academy.choose_speakers(s,"Kael",names)

def create(client):
 r=client.post("/v1/ai-world",json={"character_ids":["selene","ren","shared"],"language":"en"})
 assert r.status_code==200,r.text
 return r.json()

def act(client,s,action,value="",**extra):
 return client.post("/v1/ai-world/"+s["id"]+"/act",json={
  "revision":s["revision"],"request_id":"request-"+str(s["revision"]),"action":action,"value":value,**extra})

def test_api_owner_revision_replay_and_restart_read(world_client):
 client,factory,user=world_client
 s=create(client)
 assert client.get("/v1/ai-world/"+s["id"]).json()["id"]==s["id"]
 r=act(client,s,"choice","investigate");assert r.status_code==200,r.text
 assert act(client,s,"choice","investigate").json()["revision"]==r.json()["revision"]
 assert act(client,s,"hint",request_id="different-id").status_code==409
 with factory() as db:
  stored=json.loads(db.get(AppSetting,"ai_world:"+s["id"]).value)
  assert stored["completed"]==["letter"]
 user["id"]="bob"
 assert client.get("/v1/ai-world/"+s["id"]).status_code==404
 assert not client.get("/v1/ai-world").json()
 assert act(client,r.json(),"hint").status_code==404

def test_unavailable_actor_and_no_free_chat_without_model(world_client):
 client,_,_=world_client
 assert client.post("/v1/ai-world",json={"character_ids":["selene","bob-private"]}).status_code==422
 s=create(client)
 # Existing strict moderation blocks unconfigured input rather than bypassing it.
 r=act(client,s,"say","Tell me your secret")
 assert r.status_code==503
 assert client.get("/v1/ai-world/"+s["id"]).json()["revision"]==0

def test_cast_join_does_not_inherit_unwitnessed_observations(world_client):
 client,factory,_=world_client
 s=create(client);s=act(client,s,"choice","investigate").json()
 r=client.put("/v1/ai-world/"+s["id"]+"/characters",json={"revision":s["revision"],"character_ids":["selene","ren"]})
 assert r.status_code==200
 with factory() as db:
  data=json.loads(db.get(AppSetting,"ai_world:"+s["id"]).value)
  assert "shared" not in data["members"]
  assert len(data["completed"])==1

def test_lazy_scheduler_only_once_per_day(world_client):
 client,factory,_=world_client;s=create(client)
 with factory() as db:
  row=db.get(AppSetting,"ai_world:"+s["id"]);data=json.loads(row.value)
  data["last_seen"]=int(time.time())-90000;row.value=json.dumps(data,ensure_ascii=False);db.commit()
 a=client.get("/v1/ai-world/"+s["id"]).json()
 b=client.get("/v1/ai-world/"+s["id"]).json()
 assert a["day"]==b["day"]==2 and a["revision"]==b["revision"]

def test_provider_gets_original_persona_bounded_speakers_and_no_locked_secrets(world_client,monkeypatch):
 import httpx
 from character_chat.models import Character
 client,factory,_=world_client
 with factory() as db:
  row=db.get(Character,"selene");card=json.loads(row.spec)
  card["system_prompt"]="PERSONA_ANCHOR: guarded dry wit";row.spec=json.dumps(card)
  db.add(ModelConfig(id="world-model",name="World",provider="test",model_id="roleplay-wire",assistant_model_id="not-this-wire",api_base="https://example.test/v1",enabled=1))
  db.commit()
 monkeypatch.setattr(main.llm,"model","world-model")
 monkeypatch.setenv("WORLD_MODERATION_API_KEY","fixture-not-real")
 original=httpx.Client
 monkeypatch.setattr(httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={"results":[{"flagged":False}]})),**kw))
 calls=[]
 def completion(messages,wire,*args):
  calls.append((json.loads(messages[-1]["content"]),wire))
  return "I will listen before drawing conclusions."
 monkeypatch.setattr(main,"direct_completion",completion)
 s=create(client);r=act(client,s,"say","Selene Moonbrook and Ren Quickshade, what do you think?")
 assert r.status_code==200,r.text
 assert len(calls)==2 and all(c[1]=="roleplay-wire" for c in calls)
 assert "PERSONA_ANCHOR" in str(calls[0][0]["character"])
 assert all(not c[0]["secrets"] for c in calls)
 assert len([m for m in r.json()["messages"] if m["mode"]=="ai"])==2
 before=r.json()
 monkeypatch.setattr(main,"direct_completion",lambda *args:(_ for _ in ()).throw(RuntimeError("provider failure")))
 failure=act(client,before,"say","Hello again")
 assert failure.status_code==503
 assert client.get("/v1/ai-world/"+s["id"]).json()["revision"]==before["revision"]

def test_colon_containing_character_ids_keep_pair_visibility():
 s=academy.fresh("alice",["preset:selene","preset:ruby","own-id","preset:kael"])
 assert len(academy.context(s,"preset:selene")["relationships"])==4
 projection=academy.projection(s,[])
 assert any("preset:selene" in r["people"] for r in projection["relationship_pairs"])

def test_world_cms_and_gameplay_cannot_mutate_ordinary_chat(world_client,monkeypatch):
 import httpx
 from sqlalchemy import select
 from character_chat.models import Base,Room,Message
 client,factory,_=world_client
 with factory() as db:
  db.add(Room(id="ordinary-room",user_id="alice",name="Ordinary chat"))
  db.flush()
  db.add(Message(id="ordinary-message",room_id="ordinary-room",sender_type="user",text="Ordinary private conversation"))
  db.add(AppSetting(key="ordinary_chat_test_prompt",value="ORDINARY_PROMPT_UNCHANGED"))
  for ident,wire in [("ordinary-model","ordinary-wire"),("world-only-model","world-wire")]:
   db.add(ModelConfig(id=ident,name=ident,provider="test",model_id=wire,api_base="https://example.test/v1",enabled=1))
  db.commit()
 def snapshot():
  with factory() as db:
   result={}
   for table in Base.metadata.sorted_tables:
    rows=[dict(r) for r in db.execute(select(table)).mappings()]
    if table.name=="app_settings":
     rows=[r for r in rows if not str(r["key"]).startswith("ai_world:") and r["key"]!="ai_world_config"]
    result[table.name]=sorted(json.dumps(r,sort_keys=True,default=str) for r in rows)
   return result
 before=snapshot()
 monkeypatch.setattr(main.llm,"model","ordinary-model")
 monkeypatch.setattr(main.character_engine,"ADMIN_RESPONSE_INSTRUCTION","ORDINARY_GLOBAL_PROMPT")
 main.app.dependency_overrides[main.docs_auth]=lambda:None
 monkeypatch.setenv("WORLD_MODERATION_API_KEY","fixture-not-real")
 original=httpx.Client
 monkeypatch.setattr(httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={"results":[{"flagged":False}]})),**kw))
 cfg={"revision":0,"model_id":"world-only-model","tts_model_id":"","instruction":"WORLD_ONLY_DIRECTION","public_lore":"WORLD_PUBLIC_CANON"}
 r=client.put("/v1/admin/ai-world",json=cfg)
 assert r.status_code==200,r.text
 assert client.put("/v1/admin/ai-world",json=cfg).status_code==409
 assert client.get("/v1/admin/ai-world").json()["config"]["instruction"]=="WORLD_ONLY_DIRECTION"
 calls=[]
 def complete(messages,wire,*args):
  calls.append((messages,wire))
  return "A calm response from the academy."
 monkeypatch.setattr(main,"direct_completion",complete)
 s=create(client)
 s=act(client,s,"choice","investigate").json()
 s=act(client,s,"gift","tea",actor="selene").json()
 r=act(client,s,"say","Selene Moonbrook, hello")
 assert r.status_code==200,r.text
 messages,wire=calls[-1]
 assert wire=="world-wire" and "WORLD_ONLY_DIRECTION" in messages[0]["content"]
 assert "ORDINARY_GLOBAL_PROMPT" not in messages[0]["content"]
 assert "WORLD_PUBLIC_CANON" in messages[-1]["content"]
 assert "Ordinary private conversation" not in str(messages)
 assert "A promise from an old chat" not in str(messages)
 assert main.llm.model=="ordinary-model"
 assert main.character_engine.ADMIN_RESPONSE_INSTRUCTION=="ORDINARY_GLOBAL_PROMPT"
 assert client.delete("/v1/ai-world/"+s["id"]).status_code==200
 assert snapshot()==before

def test_world_cms_requires_separate_admin_auth(world_client):
 client,_,_=world_client
 assert client.get("/v1/admin/ai-world").status_code==401
 assert client.put("/v1/admin/ai-world",json={"revision":0}).status_code==401
