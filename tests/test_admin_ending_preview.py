"""Admin ending previews bypass progress only inside authenticated preview runs."""
import json
import pytest
from copy import deepcopy
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat.models import AppSetting, UserAccount
from character_chat import moonfall_store as storage

@pytest.mark.parametrize("ending",["remember_me","let_me_forget","new_keeper","between_memory_and_moonlight"])
def test_preview_all_endings_from_fresh_run_without_rewards(ending):
    old=engine.fresh("alice","selene","",seed(),"en",.5)
    old["admin_preview"]=True
    before=deepcopy(old)
    s=engine.advance(old,"preview_ending",ending)
    assert old==before
    assert s["admin_preview"] and s["debug_only"] and s["phase"]=="memory"
    assert s["pending_ending"]==ending
    out=view(s,{"name":"Selene"})
    assert len(out["preview_endings"])==4 and out["memory_video"]
    done=engine.advance(s,"finish_memory_cinematic")
    assert done["ending"]==ending and done["phase"]=="arc_complete"
    assert not done.get("ending_collection")
    # Preview can immediately replay even the same hidden ending.
    again=engine.advance(done,"preview_ending",ending)
    assert again["phase"]=="memory" and again["ending_is_new"]
    assert view(again,{"name":"Selene"})["memory_video"]["key"]!=out["memory_video"]["key"]

def test_normal_run_cannot_call_preview_action():
    s=engine.fresh("alice","selene","",seed(),"en",.5)
    with pytest.raises(ValueError):engine.advance(s,"preview_ending","between_memory_and_moonlight")
    assert not view(s,{"name":"Selene"})["preview_endings"]

def test_http_preview_requires_admin_and_is_owner_scoped(moonfall,monkeypatch):
    client,factory,user=moonfall
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    s=engine.fresh("alice","selene","",seed(),"en",.5)
    s["admin_preview"]=True
    with factory() as db:
        db.add(AppSetting(key=storage.run_key("alice",s["id"]),value=json.dumps(s)))
        db.commit()
    url="/v1/moonfall/"+s["id"]
    payload={"revision":0,"request_id":"preview-hidden","action":"preview_ending","value":"between_memory_and_moonlight"}
    assert client.post(url+"/act",json=payload).status_code==403
    with factory() as db:
        # Account fields use the same constructor as ordinary authentication.
        account=UserAccount(user_id="alice",username="preview-admin",display_name="Preview Admin",password_hash="fixture",is_admin=1,status="active")
        db.add(account);db.commit()
    result=client.post(url+"/act",json=payload)
    assert result.status_code==200,result.text
    assert result.json()["phase"]=="memory"
    duplicate=client.post(url+"/act",json=payload)
    assert duplicate.status_code==200 and duplicate.json()["revision"]==result.json()["revision"]
    user["id"]="bob"
    assert client.post(url+"/act",json=payload).status_code==404


def test_hidden_ending_review_keeps_three_distinct_physical_maps():
    s=engine.fresh("alice","selene","",seed(),"en",.5)
    s["admin_preview"]=True
    s=engine.advance(s,"preview_ending","between_memory_and_moonlight")
    s=engine.advance(s,"finish_memory_cinematic")
    s=engine.advance(s,"review")
    backgrounds={}
    for place in ("memory_space","pendant_echo","final_chamber"):
        s=engine.advance(s,"go",place)
        out=view(s,{"name":"Selene"})
        backgrounds[place]=out["embedded_scene"]["background"]
    assert len(set(backgrounds.values()))==3,backgrounds
    assert backgrounds["final_chamber"]=="official_bg_ch08_final_chamber_secret"
    assert backgrounds["memory_space"]=="replacement_ch08_memory_space"
    assert backgrounds["pendant_echo"]=="replacement_ch02_rooftop"
    assert len(out["locations"])==3
