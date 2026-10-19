"""Temporary system-only catalog: private creation remains, publication cannot bypass."""
import json
import pytest
from test_worlds import world_client
from character_chat import main
from character_chat.models import Character, AppSetting
from character_chat.schemas import CharacterSpec

@pytest.fixture
def system_only(world_client,monkeypatch):
 monkeypatch.delenv("WORLD_SYSTEM_CHARACTERS_ONLY",raising=False)
 monkeypatch.delenv("COMMUNITY_CHARACTER_PUBLICATION_ENABLED",raising=False)
 return world_client

def test_world_picker_only_unique_system_sources_even_after_adding_copies(system_only):
 client,factory,_=system_only
 before=client.get("/v1/worlds/characters").json()
 assert before and all(c["origin"]=="system" for c in before)
 key=before[0]["id"].removeprefix("preset:")
 with factory() as db:
  for ident in ("copy-one","copy-two"):
   spec=CharacterSpec(id=ident,name="Same system",creation_type="preset",preset_type=key)
   db.add(Character(id=ident,user_id="alice",name=spec.name,spec=spec.model_dump_json()))
  db.commit()
 after=client.get("/v1/worlds/characters").json()
 assert len(after)==len(before) and len({c["id"] for c in after})==len(after)
 assert all(c["origin"]=="system" for c in after)
 assert client.post("/v1/ai-world",json={"character_ids":["selene","ren"]}).status_code==422
 ids=[c["id"] for c in after[:4]]
 r=client.post("/v1/ai-world",json={"character_ids":ids})
 assert r.status_code==200,r.text
 assert len(r.json()["characters"])==len(set(ids))
 assert client.put("/v1/ai-world/"+r.json()["id"]+"/characters",json={"revision":0,"character_ids":["selene","ren"]}).status_code==422

def test_public_user_catalog_and_registration_temporarily_disabled(system_only):
 client,factory,_=system_only
 assert client.get("/v1/public/characters").json()==[]
 assert client.post("/v1/public/characters/shared/clone").status_code==403
 assert client.patch("/v1/characters/selene/publication",json={"is_public":True}).status_code==403
 # Existing private character and owned chat remain accessible; no data removal.
 with factory() as db:assert db.get(Character,"selene") and db.get(Character,"shared")

def test_when_explicitly_enabled_user_still_cannot_self_publish(world_client,monkeypatch):
 client,_,_=world_client
 monkeypatch.setattr(main,"enforce_character_policy",lambda *a,**k:None)
 r=client.patch("/v1/characters/selene/publication",json={"is_public":True})
 assert r.status_code==200,r.text
 assert r.json()["is_public"] is False and r.json()["publication_status"]=="pending"
 assert "selene" not in {c["id"] for c in client.get("/v1/public/characters").json()}
 main.app.dependency_overrides[main.docs_auth]=lambda:None
 r=client.put("/v1/admin/character-submissions/selene",json={"revision":1,"decision":"approved"})
 assert r.status_code==200,r.text
 assert "selene" in {c["id"] for c in client.get("/v1/public/characters").json()}
 # Any character content change withdraws approval, requiring a new submission.
 r=client.patch("/v1/characters/selene",json={"description":"Changed after review"})
 assert r.status_code==200,r.text
 assert "selene" not in {c["id"] for c in client.get("/v1/public/characters").json()}

def test_user_cannot_access_review_admin(system_only):
 client,_,_=system_only
 assert client.get("/v1/admin/character-submissions").status_code==401
 assert client.put("/v1/admin/character-submissions/selene",json={"revision":0,"decision":"approved"}).status_code==401

def test_world_map_each_character_has_exactly_one_location(system_only):
 from character_chat import academy
 for count in (2,3,4):
  s=academy.fresh("alice",[str(i) for i in range(count)])
  def check():
   shown=[a for p in academy.PLACES for a in academy.present(s,p[0])]
   assert sorted(shown)==sorted(s["members"]) and len(shown)==len(set(shown))
  check()
  s=academy.advance(s,"choice","investigate")
  s=academy.advance(s,"visit","garden");check()
  s=academy.advance(s,"choice","restore")
  s=academy.advance(s,"visit","tower");check()
  assert academy.present(s)==s["members"]
