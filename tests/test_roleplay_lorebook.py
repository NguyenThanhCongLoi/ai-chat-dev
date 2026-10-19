"""CMS lore must reach ordinary prompts, preserve room lore and obey identity ACL."""
import json
import pytest
from character_chat import main, engine, roleplay_continuity as continuity
from character_chat.models import Character, AppSetting
from character_chat.schemas import CharacterSpec
from test_worlds import world_client
from test_roleplay_continuity import chat_tools, endpoint, entry

API="/v1/admin/roleplay-lorebook"

@pytest.fixture
def admin_tools(chat_tools,monkeypatch):
 client,factory,user=chat_tools
 monkeypatch.setenv("JEV_ENABLED","false")
 main.app.dependency_overrides[main.docs_auth]=lambda:None
 return client,factory,user

def lore(**extra):
 return dict(title="Moonstone origin",text="CMS_MOONSTONE_CANON",targets=["character:selene"],knowers=[],
  scope="public",keywords=["nguyệt thạch"],always=False,canon=True,enabled=True,priority=5,**extra)

def add(client,data=None):
 r=client.post(API,json=data or lore())
 assert r.status_code==200,r.text
 return r.json()

def test_admin_routes_are_not_available_to_logged_in_user(chat_tools):
 client,_,_=chat_tools
 assert client.get(API).status_code==401
 assert client.post(API,json=lore()).status_code==401
 assert client.get("/roleplay/lorebook/admin").status_code==401

def test_saved_lore_reaches_next_prompt_without_modifying_room_lore(admin_tools):
 client,factory,_=admin_tools
 cfg=client.get(endpoint()).json();cfg["lore"]=[entry("ROOM_ONLY")]
 assert client.put(endpoint(),json=cfg).status_code==200
 saved=add(client)
 with factory() as db:
  for ident in ("selene","ren"):
   prompt,_=engine.assemble(db,"alice","chat",CharacterSpec(id=ident,name=ident),"nguyet thach")
   text=json.dumps(prompt)
   assert ("CMS_MOONSTONE_CANON" in text)==(ident=="selene")
   assert "ROOM_ONLY_CONTENT" in text
  _,selected,meta=continuity.context(db,"alice","chat","selene","nguyet thach",[])
  assert "cms:"+saved["id"] in meta["cms_lore_ids"]
  assert selected[0].get("source") in ("cms",None)
 assert client.get(endpoint()).json()=={**cfg,"revision":1}

def test_update_disable_delete_and_stale_revision(admin_tools):
 client,factory,_=admin_tools
 saved=add(client)
 def seen():
  with factory() as db:return str(continuity.context(db,"alice","chat","selene","nguyet thach",[])[1])
 changed={**saved,"text":"UPDATED_CMS_CONTENT"}
 r=client.put(API+"/"+saved["id"],json=changed)
 assert r.status_code==200,r.text
 assert "UPDATED_CMS_CONTENT" in seen() and "CMS_MOONSTONE_CANON" not in seen()
 assert client.put(API+"/"+saved["id"],json=changed).status_code==409
 saved=r.json()
 r=client.put(API+"/"+saved["id"],json={**saved,"enabled":False})
 assert r.status_code==200 and "UPDATED_CMS_CONTENT" not in seen()
 assert client.delete(API+"/"+saved["id"]+"?revision=1").status_code==409
 assert client.delete(API+"/"+saved["id"]+"?revision="+str(r.json()["revision"])).status_code==200
 assert not client.get(API).json()["entries"]

def test_private_scope_before_relevance_and_disabling_does_not_affect_room(admin_tools):
 client,factory,_=admin_tools
 data=lore();data.update(targets=["character:selene","character:ren"],scope="private",knowers=["character:selene"],always=True,priority=10)
 add(client,data)
 with factory() as db:
  assert "CMS_MOONSTONE_CANON" in str(continuity.context(db,"alice","chat","selene","unrelated",[])[1])
  assert "CMS_MOONSTONE_CANON" not in str(continuity.context(db,"alice","chat","ren","nguyet thach",[])[1])
 # Foreign room ownership is checked before any CMS lore is retrieved.
 with factory() as db:
  assert continuity.context(db,"bob","chat","selene","nguyet thach",[])[1]==[]

@pytest.mark.parametrize("patch",[
 {"targets":[]},{"targets":["character:missing"]},{"scope":"private","knowers":[]},
 {"scope":"private","knowers":["character:ren"]},{"scope":"rumor","canon":True},
 {"keywords":[]},{"priority":True},{"enabled":"true"},{"scope":"discovered"}
])
def test_invalid_entries_rejected(admin_tools,patch):
 client,_,_=admin_tools
 data=lore();data.update(patch)
 assert client.post(API,json=data).status_code==422

def test_preset_copy_matches_system_identity_but_custom_cannot_spoof_it(admin_tools):
 client,factory,_=admin_tools
 catalog=client.get(API).json()["characters"]
 preset=next(c["id"] for c in catalog if c["source"]=="system")
 key=preset.removeprefix("preset:")
 with factory() as db:
  for ident,kind in [("preset-copy","preset"),("spoof","custom")]:
   spec=CharacterSpec(id=ident,name=ident,creation_type=kind,preset_type=key)
   db.add(Character(id=ident,user_id="alice",name=ident,spec=spec.model_dump_json()))
  db.commit()
 data=lore();data.update(targets=[preset],always=True)
 add(client,data)
 from character_chat.roleplay_lorebook import entries_for
 with factory() as db:
  assert entries_for(db,"preset-copy")
  assert not entries_for(db,"spoof")

def test_public_source_clone_inherits_only_while_source_is_public(admin_tools):
 client,factory,_=admin_tools
 with factory() as db:
  spec=CharacterSpec(id="public-copy",name="Copy")
  db.add(Character(id=spec.id,user_id="alice",name=spec.name,spec=spec.model_dump_json()))
  db.add(AppSetting(key="character_clone_source:"+spec.id,value="shared"));db.commit()
 data=lore();data.update(targets=["character:shared"],always=True)
 add(client,data)
 from character_chat.roleplay_lorebook import entries_for
 from character_chat.models import CharacterPublication
 with factory() as db:
  assert entries_for(db,"public-copy")
  db.get(CharacterPublication,"shared").is_public=0;db.commit()
  assert not entries_for(db,"public-copy")

def test_cms_and_room_lore_share_existing_context_budget(admin_tools):
 client,factory,_=admin_tools
 for i in range(6):
  data=lore();data.update(title=str(i),text=str(i)*1400,always=True)
  add(client,data)
 with factory() as db:
  _,selected,meta=continuity.context(db,"alice","chat","selene","nguyet thach",[])
  assert 0<len(selected)<6 and meta["lore_characters"]<=4500

def test_world_context_never_imports_cms_ordinary_lore(admin_tools):
 client,_,_=admin_tools
 add(client)
 from character_chat import academy
 s=academy.fresh("alice",["selene","ren"])
 assert "CMS_MOONSTONE_CANON" not in str(academy.context(s,"selene"))

def test_moderation_rejection_preserves_saved_entry(admin_tools,monkeypatch):
 client,_,_=admin_tools
 saved=add(client)
 monkeypatch.setattr(main,"ensure_safe_content",lambda text:(_ for _ in ()).throw(ValueError("blocked")))
 assert client.put(API+"/"+saved["id"],json={**saved,"text":"REJECTED_CHANGE"}).status_code==422
 assert client.get(API).json()["entries"][0]["text"]=="CMS_MOONSTONE_CANON"

def test_ordinary_lorebook_works_with_worlds_disabled(admin_tools,monkeypatch):
 client,factory,_=admin_tools
 monkeypatch.setenv("WORLD_DEMO_ENABLED","false")
 add(client)
 with factory() as db:
  assert "CMS_MOONSTONE_CANON" in str(continuity.context(db,"alice","chat","selene","nguyet thach",[])[1])
