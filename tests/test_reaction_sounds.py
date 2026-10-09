import io
import wave
import pytest
from fastapi import FastAPI, HTTPException, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from character_chat.models import Base, User, Character, CharacterVoiceSample, CharacterReactionAsset, AppSetting
from character_chat.schemas import CharacterSpec
from character_chat.reaction_sounds import build_reaction_router, EMOTIONS, valid_clip

def wav(seconds=.3):
    output=io.BytesIO()
    with wave.open(output,"wb") as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(24000)
        audio.writeframes(b"\x01\x00"*int(seconds*24000))
    return output.getvalue()

@pytest.fixture
def system():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session=sessionmaker(engine,expire_on_commit=False)
    preset=CharacterSpec(id="p",name="Preset",creation_type="preset",preset_type="test",tts_voice_id="preset-voice")
    with Session() as db:
        db.add_all([User(id="u"),User(id="other")])
        item=CharacterSpec(id="c",name="Character",tts_voice_id="clone")
        inherited=preset.model_copy(update={"id":"copy"})
        db.add_all([Character(id="c",user_id="u",name="Character",spec=item.model_dump_json()),
                    Character(id="copy",user_id="u",name="Preset",spec=inherited.model_dump_json())])
        db.add_all([CharacterVoiceSample(character_id="c",target="shared",voice_id="clone",filename="ref.wav",
                    mime_type="audio/wav",content=wav(6),sample_language="vi",ref_text=""),
                    CharacterVoiceSample(character_id="preset:test",target="shared",voice_id="preset-voice",filename="ref.wav",
                    mime_type="audio/wav",content=wav(6),sample_language="en",ref_text="")])
        db.commit()
    def database():
        with Session() as db:yield db
    def admin(x_admin:str=Header("")):
        if x_admin!="yes":raise HTTPException(401)
    def user(x_user:str=Header("u")):return x_user
    def spec_for(db,id):
        if id=="preset:test":return preset
        row=db.get(Character,id)
        if not row:raise HTTPException(404)
        return CharacterSpec.model_validate_json(row.spec)
    calls=[]
    def generate(reference,filename,slots=None):
        calls.append((reference,filename,slots))
        if calls[0]=="fail": raise RuntimeError("upstream private-key must not be exposed")
        return [{"emotion":emotion,"variant":variant,"audio":wav()} for emotion in EMOTIONS for variant in range(2) if slots is None or (emotion,variant) in {tuple(slot) for slot in slots}]
    router,queue=build_reaction_router(user,database,admin,Session,spec_for,lambda db:[preset],generate)
    app=FastAPI();app.include_router(router)
    with TestClient(app) as client:yield client,Session,calls
    engine.dispose()

def test_generation_auth_saved_reuse_volume_and_voice_change(system):
    client,Session,calls=system;url="/v1/admin/characters/c/reactions"
    assert client.post(url+"/generate").status_code==401
    assert client.post(url+"/generate",headers={"X-Admin":"yes"}).status_code==200
    result=client.get(url,headers={"X-Admin":"yes"}).json()
    assert result["status"]=="ready" and len(result["clips"])==12 and len(calls)==1
    clips=client.get("/v1/characters/c/reactions").json()["clips"]
    assert len(clips)==12 and client.get(clips[0]["url"]).content==wav()
    assert client.get(clips[0]["url"],headers={"X-User":"other"}).status_code==404
    assert len(calls)==1
    assert client.patch(url,json={"volume":.4},headers={"X-Admin":"yes"}).status_code==200
    assert client.get("/v1/characters/c/reactions").json()["clips"][0]["volume"]==.4
    assert client.patch(url,json={"volume":2},headers={"X-Admin":"yes"}).status_code==400
    with Session() as db:
        row=db.get(Character,"c");item=CharacterSpec.model_validate_json(row.spec)
        item.tts_voice_id="new-clone";row.spec=item.model_dump_json();db.commit()
    assert client.get("/v1/characters/c/reactions").json()["clips"]==[]
    assert client.get(clips[0]["url"]).status_code==404
    assert client.get(url,headers={"X-Admin":"yes"}).json()["status"]=="no_sample"

def test_preset_inheritance_backfill_and_delete(system):
    client,Session,calls=system;auth={"X-Admin":"yes"}
    result=client.post("/v1/admin/system-characters/reactions/backfill",headers=auth)
    assert result.status_code==200 and result.json()["missing_samples"]==[]
    clips=client.get("/v1/characters/copy/reactions").json()["clips"]
    assert len(clips)==12 and client.get(clips[0]["url"]).status_code==200
    client.post("/v1/admin/system-characters/reactions/backfill",headers=auth)
    assert len(calls)==1
    assert client.delete("/v1/admin/characters/preset:test/reactions",headers=auth).status_code==200
    assert client.get("/v1/characters/copy/reactions").json()["clips"]==[]

def test_changed_sample_rejects_old_and_separate_target_is_empty(system):
    client,Session,calls=system;auth={"X-Admin":"yes"};url="/v1/admin/characters/c/reactions"
    client.post(url+"/generate",headers=auth)
    old=client.get("/v1/characters/c/reactions").json()["clips"][0]["url"]
    with Session() as db:
        db.get(CharacterVoiceSample,("c","shared")).content=wav(7);db.commit()
    assert client.get(old).status_code==404
    assert client.get(url+"?target=en",headers=auth).json()["status"]=="no_sample"
    assert client.post(url+"/generate?target=en",headers=auth).status_code==400
    assert client.get(url+"?target=bad",headers=auth).status_code==400

def test_clip_validation():
    valid_clip(wav())
    for value in [b"invalid",wav(.1),wav(5)]:
        with pytest.raises((ValueError,wave.Error,EOFError)):valid_clip(value)

def test_failed_generation_remains_failed_and_retry_succeeds(system):
    client,Session,calls=system
    calls.append("fail")
    auth={"X-Admin":"yes"};url="/v1/admin/characters/c/reactions"
    assert client.post(url+"/generate",headers=auth).status_code==200
    state=client.get(url,headers=auth).json()
    assert state["status"]=="failed" and state["clips"]==[]
    assert "character-reactions" in state["error"]
    assert "private-key" not in state["error"]
    calls.clear()
    assert client.post(url+"/generate",headers=auth).status_code==200
    assert client.get(url,headers=auth).json()["status"]=="ready"

def test_legacy_failed_state_is_not_hidden_as_missing(system):
    client,Session,calls=system
    with Session() as db:
        db.add(AppSetting(key="reaction_status:c:shared",value='{"status":"failed","error":"Generation failed."}'))
        db.commit()
    state=client.get("/v1/admin/characters/c/reactions",headers={"X-Admin":"yes"}).json()
    assert state["status"]=="failed" and state["error"]=="Generation failed."

def test_separate_reference_preserves_speech_sample_and_invalidation(system):
    client,Session,calls=system;auth={"X-Admin":"yes"}
    url="/v1/admin/characters/c/reactions"
    original=wav(6);separate=wav(9)
    assert client.post(url+"/reference",files={"audio":("effect.wav",separate)}).status_code==401
    response=client.post(url+"/reference",files={"audio":("effect.wav",separate)},headers=auth)
    assert response.status_code==200
    info=client.get(url+"/reference",headers=auth).json()
    assert info["source"]=="separate" and info["filename"]=="effect.wav"
    assert client.get(info["url"],headers=auth).content==separate
    with Session() as db:assert db.get(CharacterVoiceSample,("c","shared")).content==original
    client.post(url+"/generate?repeat_short=true",headers=auth)
    assert calls[0][0]==separate
    old=client.get("/v1/characters/c/reactions").json()["clips"][0]["url"]
    client.post(url+"/reference",files={"audio":("new.wav",wav(10))},headers=auth)
    assert client.get(old).status_code==404
    assert client.delete(url+"/reference",headers=auth).status_code==200
    assert client.get(url+"/reference",headers=auth).json()["source"]=="clone"
    with Session() as db:assert db.get(CharacterVoiceSample,("c","shared")).content==original

def test_reference_upload_validation_and_slots(system):
    client,Session,calls=system;auth={"X-Admin":"yes"};url="/v1/admin/characters/c/reactions/reference"
    assert client.post(url,files={"audio":("bad.txt",b"bad")},headers=auth).status_code==400
    assert client.post(url,files={"audio":("bad.wav",b"bad")},headers=auth).status_code==400
    assert client.post(url+"?target=en",files={"audio":("good.wav",wav(8))},headers=auth).status_code==400
    # A short WAV may be uploaded and repeated later during generation.
    assert client.post(url,files={"audio":("short.wav",wav(3))},headers=auth).status_code==200

def test_reference_repeat_counts():
    from character_chat.reaction_reference import reference_repeat_count
    assert reference_repeat_count(6*24000,24000)==1
    assert reference_repeat_count(3*24000,24000)==2
    assert reference_repeat_count(2*24000,24000)==3
    with pytest.raises(ValueError):reference_repeat_count(24000,24000)
    with pytest.raises(ValueError):reference_repeat_count(0,24000)

def test_delete_individual_and_fill_only_missing_preserves_existing(system):
    client,Session,calls=system;auth={"X-Admin":"yes"};url="/v1/admin/characters/c/reactions"
    client.post(url+"/generate",headers=auth)
    original=client.get(url,headers=auth).json()["clips"]
    deleted=original[0];survivors={clip["id"] for clip in original[1:]}
    assert client.delete(url+"/"+deleted["id"]).status_code==401
    assert client.delete("/v1/admin/characters/copy/reactions/"+deleted["id"],headers=auth).status_code==404
    assert client.delete(url+"/"+deleted["id"],headers=auth).status_code==200
    state=client.get(url,headers=auth).json()
    assert state["status"]=="partial" and state["missing_count"]==1
    assert client.post(url+"/generate?missing_only=true",headers=auth).status_code==200
    assert calls[-1][2]==[(deleted["emotion"],deleted["variant"])]
    current=client.get(url,headers=auth).json()
    assert current["status"]=="ready" and current["missing_count"]==0
    assert survivors.issubset({clip["id"] for clip in current["clips"]})
    assert deleted["id"] not in {clip["id"] for clip in current["clips"]}
    count=len(calls)
    client.post(url+"/generate?missing_only=true",headers=auth)
    assert len(calls)==count
