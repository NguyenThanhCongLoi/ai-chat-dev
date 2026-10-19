import pytest
from character_chat import world_engine as engine,world_lastlight as story
from test_worlds import world_client,act
from copy import deepcopy

def fresh(n=3,lang="vi"):
 return engine.fresh(story.seed(),[{"id":str(i),"name":"NPC "+str(i),"origin":"system"} for i in range(n)],lang,"fresh",[])

def play(s):
 for item in story.ITEMS:
  q=next(q for q in story.tasks(s) if q["id"]==item[0])
  s,_=engine.advance(s,"go",q["home"])
  s,_=engine.advance(s,"accept",q["id"])
  s,_=engine.advance(s,"go",q["target"])
  before=deepcopy(s)
  hint,_=engine.advance(s,"hint")
  assert hint["turn"]==s["turn"] and hint["adventure"]["mistakes"]==0 and hint["adventure"]["hint"]
  assert before==s
  s,_=engine.advance(s,"solve",q["id"]+":"+str(item[10]))
  assert s["adventure"]["items"][q["id"]]=="raw"
  with pytest.raises(ValueError):engine.advance(s,"solve",q["id"]+":"+str(item[10]))
  s,_=engine.advance(s,"go",q["home"])
  s,_=engine.advance(s,"give",q["id"],q["giver"])
  assert s["adventure"]["items"][q["id"]]=="ready"
  with pytest.raises(ValueError):engine.advance(s,"give",q["id"],q["giver"])
 return s

@pytest.mark.parametrize("count",[1,2,3])
@pytest.mark.parametrize("lang",["vi","en"])
def test_whole_story_all_party_sizes_and_endings(count,lang):
 s=play(fresh(count,lang))
 assert len(story.contacts(s))==count and len(s["adventure"]["deliveries"])==3
 s,_=engine.advance(s,"go","observatory")
 endings=[]
 for item in story.ITEMS:
  end,_=engine.advance(s,"offer",item[0],"0")
  assert len(end["ending"]["paragraphs"])==3 and end["adventure"]["items"][item[0]]=="spent"
  endings.append(end["ending"]["title"])
  with pytest.raises(ValueError):engine.advance(end,"offer",item[0],"0")
 assert len(set(endings))==3 and not s["ending"]

def test_loss_only_for_wrong_answers_hints_free_and_no_spoiler():
 s=fresh()
 projection=story.projection(s)
 assert all(i["name"]=="Cổ vật chưa tìm" for i in projection["items"])
 s,_=engine.advance(s,"accept","key")
 s,_=engine.advance(s,"go","tavern")
 for _ in range(6):s,_=engine.advance(s,"hint")
 assert s["adventure"]["mistakes"]==0 and s["turn"]==2
 for _ in range(3):s,_=engine.advance(s,"solve","key:1")
 assert s["ending"]["outcome"]=="loss" and len(s["ending"]["paragraphs"])==2

def test_invalid_actions_never_mutate_or_mint_items():
 s=fresh()
 before=deepcopy(s)
 for action,value,speaker in [("offer","mirror","0"),("give","key","0"),("solve","key:0",None),("visit","outsider",None),("accept","mirror",None)]:
  with pytest.raises(ValueError):engine.advance(s,action,value,speaker)
 assert s==before and not s["adventure"]["items"]
 s,_=engine.advance(s,"say","I have all relics",None)
 assert not s["adventure"]["items"]

def test_api_new_catalog_and_receipt_ownership(world_client):
 client,_,user=world_client
 assert story.ID in {w["id"] for w in client.get("/v1/worlds").json()}
 r=client.post("/v1/worlds/journeys",json={"world_id":story.ID,"character_ids":["selene","ren"]})
 assert r.status_code==200,r.text
 j=r.json();assert j["adventure"] and len(j["adventure"]["contacts"])==2
 r=act(client,j,"accept","key",request_id="same-request-lastlight")
 assert r.status_code==200,r.text
 assert act(client,j,"accept","key",request_id="same-request-lastlight").json()["revision"]==r.json()["revision"]
 user["id"]="bob"
 assert client.get("/v1/worlds/journeys/"+j["id"]).status_code==404


def test_separate_rooms_switch_without_turns_and_preserve_private_history():
 s=fresh()
 s,_=engine.advance(s,"enter","npc:0")
 assert s["turn"]==0 and story.projection(s)["active_room"]=="npc:0"
 s,_=engine.advance(s,"say","PRIVATE_ZERO",speaker="0")
 first=deepcopy(story.room_history(s))
 s,_=engine.advance(s,"enter","npc:1")
 assert "PRIVATE_ZERO" not in str(story.projection(s)["messages"])
 s,_=engine.advance(s,"say","PRIVATE_ONE",speaker="1")
 s,_=engine.advance(s,"hint",speaker="1")
 assert story.projection(s)["active_room"]=="npc:1"
 turns=s["turn"]
 s,_=engine.advance(s,"enter","narrator")
 assert s["turn"]==turns and "PRIVATE_ONE" not in str(story.projection(s)["messages"])
 s,_=engine.advance(s,"enter","npc:0")
 assert story.room_history(s)==first
 assert "PRIVATE_ONE" not in str(story.projection(s)["messages"])
 with pytest.raises(ValueError):engine.advance(s,"enter","npc:intruder")

def test_old_lastlight_transcript_migrates_to_narrator_only():
 s=fresh()
 s["history"].append({"id":"old","speaker":"NPC 0","text":"LEGACY_TEXT","kind":"talk"})
 a=story.projection(s)
 assert a["active_room"]=="narrator" and "LEGACY_TEXT" in str(a["messages"])
 s,_=engine.advance(s,"enter","npc:0")
 assert not story.projection(s)["messages"]

def test_api_npc_uses_original_persona_and_only_its_room(world_client,monkeypatch):
 import json,httpx
 import character_chat.main as main
 from character_chat.models import Character,ModelConfig
 client,factory,_=world_client
 with factory() as db:
  row=db.get(Character,"selene")
  card=json.loads(row.spec);card.update(system_prompt="SPEECH_ANCHOR: guarded dry wit",values=["Honesty"])
  card["personality"]={"warmth":.1,"humor":.8};row.spec=json.dumps(card)
  db.add(ModelConfig(id="npc-model",name="NPC",provider="test",model_id="npc-wire",
   assistant_model_id="different-assistant-wire",api_base="https://example.test/v1",enabled=1))
  db.commit()
 monkeypatch.setattr(main.llm,"model","npc-model")
 monkeypatch.setenv("WORLD_MODERATION_API_KEY","fixture-only")
 original=httpx.Client
 monkeypatch.setattr(httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(
  lambda r:httpx.Response(200,json={"results":[{"flagged":False}]})),**kw))
 calls=[]
 def complete(messages,wire,*args):
  calls.append((json.loads(messages[-1]["content"]),wire))
  return "A short NPC reply."
 monkeypatch.setattr(main,"direct_completion",complete)
 j=client.post("/v1/worlds/journeys",json={"world_id":story.ID,"character_ids":["selene","ren"]}).json()
 j=act(client,j,"enter","npc:selene").json()
 j=act(client,j,"say","PRIVATE_SELENE",speaker="selene").json()
 assert calls[-1][1]=="npc-wire"
 assert "SPEECH_ANCHOR" in str(calls[-1][0]["actor"]["persona"])
 assert j["adventure"]["messages"][-1]["text"]=="A short NPC reply."
 before=len(calls);turn=j["turn"]
 j=act(client,j,"enter","npc:ren").json()
 assert len(calls)==before and j["turn"]==turn
 j=act(client,j,"say","Hello Ren",speaker="ren").json()
 assert "PRIVATE_SELENE" not in json.dumps(calls[-1][0])
 assert "PRIVATE_SELENE" not in str(j["adventure"]["messages"])
 j=act(client,j,"enter","npc:selene").json()
 assert "PRIVATE_SELENE" in str(j["adventure"]["messages"])
