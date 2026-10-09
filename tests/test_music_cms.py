
import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from character_chat.models import Base, BackgroundMusicAsset
from character_chat.background_music import build_background_music_router

@pytest.fixture
def music_client(tmp_path,monkeypatch):
    monkeypatch.setenv("ROLEPLAY_MUSIC_DIR",str(tmp_path))
    (tmp_path/"Ambient.mp3").write_bytes(b"ID3bundled")
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session=sessionmaker(engine,expire_on_commit=False)
    def database():
        with Session() as db:yield db
    def admin(x_admin:str=Header("")):
        if x_admin!="yes":raise HTTPException(401)
    app=FastAPI();app.include_router(build_background_music_router(lambda:"user",database,admin))
    with TestClient(app) as client:yield client,Session
    engine.dispose()

def test_admin_auth_settings_selection_and_persistence(music_client):
    client,Session=music_client
    assert client.get("/v1/admin/background-music").status_code==401
    assert client.put("/v1/admin/background-music",json={"volume":1,"selected_ids":[]}).status_code==401
    assert client.post("/v1/admin/background-music/upload",files={"file":("x.mp3",b"ID3x")}).status_code==401
    headers={"X-Admin":"yes"}
    catalog=client.get("/v1/admin/background-music",headers=headers).json()
    key=catalog["tracks"][0]["id"]
    assert client.put("/v1/admin/background-music",headers=headers,json={"volume":1.1,"selected_ids":[]}).status_code==400
    assert client.put("/v1/admin/background-music",headers=headers,json={"volume":.6,"selected_ids":["unknown"]}).status_code==400
    assert client.put("/v1/admin/background-music",headers=headers,json={"volume":.6,"selected_ids":[key]}).status_code==200
    assert client.get("/v1/roleplay/background-music").json()["volume"]==.6
    assert client.get("/v1/admin/background-music",headers=headers).json()["selected_ids"]==[key]
    client.put("/v1/admin/background-music",headers=headers,json={"volume":.6,"selected_ids":[]})
    assert client.get("/v1/roleplay/background-music").json()["tracks"]==[]

def test_upload_rejects_non_audio_deduplicates_and_streams_ranges(music_client):
    client,Session=music_client;headers={"X-Admin":"yes"}
    assert client.post("/v1/admin/background-music/upload",headers=headers,files={"file":("secrets.mp3",b"not audio")}).status_code==400
    content=b"ID3abcdefgh"
    first=client.post("/v1/admin/background-music/upload",headers=headers,files={"file":("song.mp3",content)}).json()
    second=client.post("/v1/admin/background-music/upload",headers=headers,files={"file":("other.mp3",content)}).json()
    assert first==second
    with Session() as db:assert db.query(BackgroundMusicAsset).count()==1
    catalog=client.get("/v1/admin/background-music",headers=headers).json()
    assert len(catalog["tracks"])==2
    response=client.get("/v1/roleplay/background-music/"+first["id"],headers={"Range":"bytes=3-6"})
    assert response.status_code==206 and response.content==b"abcd"
    assert client.get("/v1/roleplay/background-music/"+first["id"],headers={"Range":"bytes=999-"}).status_code==416

def test_deleting_bundled_and_uploaded_tracks_removes_from_playlist(music_client):
    client,Session=music_client;headers={"X-Admin":"yes"}
    bundled=client.get("/v1/admin/background-music",headers=headers).json()["tracks"][0]["id"]
    uploaded=client.post("/v1/admin/background-music/upload",headers=headers,files={"file":("delete.mp3",b"ID3delete")}).json()["id"]
    client.put("/v1/admin/background-music",headers=headers,json={"volume":.4,"selected_ids":[bundled,uploaded]})
    assert client.delete("/v1/admin/background-music/"+bundled).status_code==401
    assert client.delete("/v1/admin/background-music/"+bundled,headers=headers).status_code==200
    assert client.get("/v1/admin/background-music",headers=headers).json()["selected_ids"]==[uploaded]
    assert client.get("/v1/roleplay/background-music/"+bundled).status_code==404
    assert client.delete("/v1/admin/background-music/"+uploaded,headers=headers).status_code==200
    assert client.get("/v1/admin/background-music",headers=headers).json()["tracks"]==[]
    assert client.get("/v1/roleplay/background-music").json()["tracks"]==[]
    with Session() as db:assert db.get(BackgroundMusicAsset,uploaded) is None

def test_cms_saves_playlist_without_client_volume(music_client):
    client,_=music_client
    headers={"X-Admin":"yes"}
    key=client.get("/v1/admin/background-music",headers=headers).json()["tracks"][0]["id"]
    client.put("/v1/admin/background-music",headers=headers,json={"volume":.6,"selected_ids":[]})
    response=client.put("/v1/admin/background-music",headers=headers,json={"selected_ids":[key]})
    assert response.status_code==200
    assert response.json()["selected_ids"]==[key]
    assert response.json()["volume"]==.6
    assert len(client.get("/v1/roleplay/background-music").json()["tracks"])==1
