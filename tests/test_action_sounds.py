import pytest
from fastapi import FastAPI,Header,HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from character_chat.models import Base
from character_chat import action_sounds

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(action_sounds,"ROOT",tmp_path)
    (tmp_path/"crow.ogg").write_bytes(b"OggSsound")
    (tmp_path/"private.zip").write_bytes(b"private")
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions=sessionmaker(engine)
    def db():
        with sessions() as session:yield session
    def admin(x_admin:str=Header("")):
        if x_admin!="yes":raise HTTPException(401)
    app=FastAPI()
    app.include_router(action_sounds.build_action_sound_router(lambda:"user",db,admin))
    with TestClient(app) as c:yield c
    engine.dispose()

def test_default_rules_auth_and_audio(client):
    assert client.get("/v1/admin/action-sounds").status_code==401
    public=client.get("/v1/roleplay/action-sounds").json()
    assert len(public["sounds"])==1
    sound=public["sounds"][0]
    assert "quạ+kêu" in sound["triggers"]
    assert client.get(sound["url"]).content==b"OggSsound"
    assert client.get("/v1/roleplay/action-sounds/../private.zip").status_code==404

def test_save_validation_and_disabled_catalog(client):
    headers={"x-admin":"yes"}
    data=client.get("/v1/admin/action-sounds",headers=headers).json()
    data["volume"]=.2;data["sounds"][0]["volume"]=.6;data["sounds"][0]["enabled"]=False
    assert client.put("/v1/admin/action-sounds",headers=headers,json=data).status_code==200
    assert client.get("/v1/roleplay/action-sounds").json()=={"volume":.2,"sounds":[]}
    data["volume"]=2
    assert client.put("/v1/admin/action-sounds",headers=headers,json=data).status_code==400
    data["volume"]=.3;data["sounds"][0]["triggers"]=["x"*161]
    assert client.put("/v1/admin/action-sounds",headers=headers,json=data).status_code==400

def test_upload_persist_enable_delete(client):
    headers={"x-admin":"yes"}
    url="/v1/admin/action-sounds/upload"
    assert client.post(url,files={"file":("x.ogg",b"OggSsample")}).status_code==401
    assert client.post(url,headers=headers,files={"file":("x.mp3",b"bad")}).status_code==400
    key=client.post(url,headers=headers,files={"file":("pen.mp3",b"ID3sample")}).json()["id"]
    data=client.get("/v1/admin/action-sounds",headers=headers).json()
    uploaded=next(row for row in data["sounds"] if row["id"]==key)
    assert not uploaded["enabled"]
    uploaded.update(enabled=True,triggers=["đặt+bút+xuống"])
    assert client.put("/v1/admin/action-sounds",headers=headers,json=data).status_code==200
    assert any(row["id"]==key for row in client.get("/v1/roleplay/action-sounds").json()["sounds"])
    assert client.get(uploaded["url"]).content==b"ID3sample"
    assert client.delete("/v1/admin/action-sounds/"+key,headers=headers).status_code==200
    assert client.get(uploaded["url"]).status_code==404


def test_main_action_sound_routes_precede_frontend_mount():
    from character_chat.main import app,docs_auth
    root_index=next(i for i,route in enumerate(app.routes) if getattr(route,"name",None)=="frontend")
    for path in ("/v1/admin/action-sounds","/v1/roleplay/action-sounds"):
        indices=[i for i,route in enumerate(app.routes) if getattr(route,"path",None)==path]
        assert indices and all(i<root_index for i in indices)
    def reject():
        raise HTTPException(401,"Test authentication required")
    previous=app.dependency_overrides.get(docs_auth)
    app.dependency_overrides[docs_auth]=reject
    try:
        response=TestClient(app).get("/v1/admin/action-sounds")
        assert response.status_code==401
        assert response.json()["detail"]=="Test authentication required"
    finally:
        if previous is None:app.dependency_overrides.pop(docs_auth,None)
        else:app.dependency_overrides[docs_auth]=previous

def test_long_bundled_wav_is_served_as_small_three_second_clip(client):
    import io
    import wave
    path = action_sounds.ROOT / "pencil-scratch-1.wav"
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(2)
        sound.setsampwidth(2)
        sound.setframerate(44100)
        sound.writeframes(b"\x01\x00" * 2 * 44100 * 40)
    assert path.stat().st_size > 5 * 1024 * 1024
    entry = next(row for row in client.get("/v1/roleplay/action-sounds").json()["sounds"] if row["title"] == path.stem)
    response = client.get(entry["url"])
    assert response.status_code == 200
    assert len(response.content) < 1024 * 1024
    with wave.open(io.BytesIO(response.content), "rb") as clip:
        assert clip.getnframes() / clip.getframerate() == 3
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(2)
        sound.setframerate(24000)
        sound.writeframes(b"\x02\x00" * 24000)
    new_entry = next(row for row in client.get("/v1/roleplay/action-sounds").json()["sounds"] if row["id"] == entry["id"])
    assert new_entry["url"] != entry["url"]
    with wave.open(io.BytesIO(client.get(new_entry["url"]).content), "rb") as clip:
        assert clip.getnframes() / clip.getframerate() == 1
