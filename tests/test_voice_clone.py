
import asyncio,io,json
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from character_chat.models import Base,User,Character,ModelConfig,AppSetting
from character_chat.schemas import CharacterSpec
from character_chat import main
from character_chat.voice_clone import upload_voice

@pytest.fixture(autouse=True)
def no_remote_reaction_jobs(monkeypatch):
    monkeypatch.setattr(main,"queue_reaction_generation",lambda *args,**kwargs:{"status":"generating"})

def test_upload_voice_uses_documented_multipart_and_bearer(monkeypatch):
    original=httpx.AsyncClient
    calls=[]
    def response(request):
        calls.append(request.url.path)
        assert request.url.path=="/api/v1/voices"
        assert request.headers["authorization"]=="Bearer test-key"
        content=request.read()
        assert b'name="audio"' in content and b'name="name"' in content
        assert b'name="enhance_audio"' in content and b"true" in content
        return httpx.Response(200,json={"voice":{"voice_id":"mia_clone"}})
    monkeypatch.setattr(httpx,"AsyncClient",lambda **kwargs:original(transport=httpx.MockTransport(response),**kwargs))
    assert asyncio.run(upload_voice("https://voice.example/v1","test-key","Mia",b"fLaCsample","sample.flac","audio/flac","female","vi","Xin chào",True))=="mia_clone"
    assert calls==["/api/v1/voices"]

def test_upload_auth_error_does_not_leak_upstream_secrets(monkeypatch):
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,"AsyncClient",lambda **kwargs:original(transport=httpx.MockTransport(lambda request:httpx.Response(401,text="secret upstream body")),**kwargs))
    with pytest.raises(main.HTTPException) as error:
        asyncio.run(upload_voice("https://voice.example","test-key","Mia",b"ID3sample","a.mp3","audio/mpeg","female","vi"))
    assert error.value.status_code==502 and "secret" not in error.value.detail

def test_clone_endpoint_auth_and_saves_user_and_preset_voice(monkeypatch):
    monkeypatch.setenv("DOCS_USERNAME","cms")
    monkeypatch.setenv("DOCS_PASSWORD","test-password")
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine);Session=sessionmaker(engine,expire_on_commit=False)
    with Session() as db:
        db.add(User(id="owner"))
        spec=CharacterSpec(id="mia",name="Mia")
        db.add(Character(id="mia",user_id="owner",name="Mia",spec=spec.model_dump_json()))
        preset=main.effective_presets(db)[0]
        copy=preset.model_copy(deep=True);copy.id="preset-copy";copy.creation_type="preset"
        db.add(Character(id=copy.id,user_id="owner",name=copy.name,spec=copy.model_dump_json()))
        db.add(ModelConfig(id="tts",name="TTS",provider="Avibi",model_id="avibi-tts-flash-1.0",api_base="https://voice.example/v1",enabled=1))
        db.add(AppSetting(key="model_profile:tts",value=json.dumps({"purposes":["tts"]})));db.commit()
    def database():
        with Session() as db:yield db
    before=dict(main.app.dependency_overrides)
    main.app.dependency_overrides[main.db_session]=database
    calls=[]
    async def upload(*args):calls.append(args);return "voice_cloned"
    import character_chat.voice_clone as clone
    monkeypatch.setattr(clone,"upload_voice",upload)
    monkeypatch.setattr(main,"credential_for_model",lambda *args:"test-key")
    try:
        with TestClient(main.app) as client:
            url="/v1/admin/characters/mia/voice/clone"
            fields={"name":"Mia voice","language":"vi","gender":"female"}
            assert client.post(url,data=fields,files={"audio":("a.flac",b"fLaCsample")}).status_code==401
            assert not calls
            response=client.post(url,data=fields,files={"audio":("a.flac",b"fLaCsample")},auth=("cms","test-password"))
            assert response.status_code==200,response.text
            with Session() as db:assert main.spec(db.get(Character,"mia")).tts_voice_id=="voice_cloned"
            response=client.post("/v1/admin/characters/preset:"+preset.preset_type+"/voice/clone",data=fields,files={"audio":("a.mp3",b"ID3sample")},auth=("cms","test-password"))
            assert response.status_code==200,response.text
            with Session() as db:
                assert main.spec(db.get(Character,"preset-copy")).tts_voice_id=="voice_cloned"
                assert next(item for item in main.effective_presets(db) if item.preset_type==preset.preset_type).tts_voice_id=="voice_cloned"
            auth=("cms","test-password")
            volume_saved=client.put("/v1/admin/characters/mia",json={"tts_volume":2},auth=auth)
            assert volume_saved.status_code==200 and volume_saved.json()["spec"]["tts_volume"]==2
            assert client.put("/v1/admin/characters/mia",json={"tts_volume":2.01},auth=auth).status_code==400

            sample_url="/v1/admin/characters/mia/voice/sample/"
            assert client.get(sample_url+"shared").status_code==401
            shared=client.get(sample_url+"shared",auth=auth).json()
            assert shared["filename"]=="a.flac" and shared["available"]
            assert "content" not in shared
            assert client.get(sample_url+"shared/audio",auth=auth).content==b"fLaCsample"
            assert client.get(sample_url+"en",auth=auth).json()["available"] is False
            assert client.get(sample_url+"en/audio",auth=auth).status_code==404
            response=client.post(url,data={**fields,"target":"en","language":"en"},files={"audio":("english.flac",b"fLaCenglish")},auth=auth)
            assert response.status_code==200,response.text
            assert client.get(sample_url+"en",auth=auth).json()["filename"]=="english.flac"
            assert client.get(sample_url+"vi",auth=auth).json()["voice_id"]==""
            response=client.post(url,data={**fields,"target":"vi"},files={"audio":("vietnamese.flac",b"fLaCvietnamese")},auth=auth)
            assert response.status_code==200,response.text
            assert client.get(sample_url+"vi/audio",auth=auth).content==b"fLaCvietnamese"
            assert client.get(sample_url+"en/audio",auth=auth).content==b"fLaCenglish"
            with Session() as db:
                configured=main.spec(db.get(Character,"mia"))
                assert configured.tts_voice_source_en=="clone" and configured.tts_voice_source_vi=="clone"
            response=client.put("/v1/admin/characters/mia",json={"tts_voice_source_en":"catalog","tts_voice_en":"api-english"},auth=auth)
            assert response.status_code==200,response.text
            assert response.json()["spec"]["tts_voice_source_en"]=="catalog"
            assert response.json()["spec"]["tts_voice_source_vi"]=="clone"
            assert response.json()["spec"]["tts_voice_vi"]=="voice_cloned"
            assert client.put("/v1/admin/characters/mia",json={"tts_voice_source_en":"invalid"},auth=auth).status_code==400

            response=client.post(url,data={**fields,"target":"en","language":"en"},files={"audio":("english-new.flac",b"fLaCnew")},auth=auth)
            assert response.status_code==200,response.text
            assert client.get(sample_url+"en/audio",auth=auth).content==b"fLaCnew"
            assert client.get(sample_url+"vi/audio",auth=auth).content==b"fLaCvietnamese"
            assert client.get(sample_url+"invalid",auth=auth).status_code==400
            preset_url="/v1/admin/characters/preset:"+preset.preset_type+"/voice/sample/shared"
            assert client.get(preset_url,auth=auth).json()["filename"]=="a.mp3"
            assert client.get("/v1/admin/characters/preset-copy/voice/sample/shared/audio",auth=auth).content==b"ID3sample"
            # A manually replaced voice cannot expose the previous voice's file.
            with Session() as db:
                item=db.get(Character,"mia"); value=main.spec(item)
                value.tts_voice_en="manually-replaced";item.spec=value.model_dump_json();db.commit()
            assert client.get(sample_url+"en",auth=auth).json()["available"] is False
            assert client.get(sample_url+"en/audio",auth=auth).status_code==404
            count=len(calls)
            invalid=client.post(url,data=fields,files={"audio":("not.mp3",b"not audio")},auth=("cms","test-password"))
            assert invalid.status_code==400 and len(calls)==count
    finally:main.app.dependency_overrides.clear();main.app.dependency_overrides.update(before);engine.dispose()
