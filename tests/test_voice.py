from character_chat.schemas import CharacterSpec
import pytest
from character_chat.voice import character_voice_gender, normalize_voices, select_voice, vbee_voice_url, speech_api_base


@pytest.mark.parametrize("api_base", ["https://api-voice-uat.vbeelabs.ai/v1", "https://voice-tunnel.example"])
@pytest.mark.parametrize("catalog_mode", ["available", "empty", "unavailable"])
@pytest.mark.parametrize("preset_type", ["entertainment_lover", ""])
def test_prepared_audio_is_reused_until_voice_changes(monkeypatch, api_base, catalog_mode, preset_type):
    import asyncio
    import json
    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    import character_chat.main as main
    monkeypatch.setattr(main,"_vbee_voice_cache",{})
    monkeypatch.setenv("GATEWAY_CONNECT_TIMEOUT_SECONDS", "9")
    from character_chat.db import Base, AppSetting, Character, Message, MessageSpeech, ModelConfig, Room, User, VoiceEvent

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(engine, expire_on_commit=False)
    with session() as db:
        db.add(User(id="voice-user"))
        db.add(Room(id="voice-room", user_id="voice-user", name="Chat"))
        character = Character(id="voice-character", user_id="voice-user", name="Mia", spec=CharacterSpec(name="Mia", preset_type=preset_type).model_dump_json())
        message = Message(id="voice-message", room_id="voice-room", sender_type="character", character_id=character.id, text="*mỉm cười* Chào bạn")
        model = ModelConfig(id="voice-model", name="Vbee", provider="Vbee", model_id="avibi-tts-pro-1.0", api_base=api_base, enabled=1)
        db.add_all([character, message, model, AppSetting(key="model_profile:voice-model", value=json.dumps({"purposes": ["tts"], "tts_default_voice": "" if not preset_type and catalog_mode == "available" else "woman_vi"}))])
        db.commit()
        monkeypatch.setattr(main, "credential_for_model", lambda _db, _model: "test-key")
        calls = []

        def respond(request):
            calls.append(request.url.path)
            if request.url.path.endswith("/voices"):
                if catalog_mode=="empty":return httpx.Response(200,json={"voices":[]})
                if catalog_mode=="unavailable":return httpx.Response(503)
                return httpx.Response(200, json={"voices": [{"voice_id": "woman_vi", "gender": "female", "language": "vi"}]})
            assert request.url.path == "/v1/audio/speech"
            assert request.headers["authorization"] == "Bearer test-key"
            assert request.read().decode().find('"voice":"woman_vi"') >= 0
            if calls.count("/v1/audio/speech") == 1:
                assert request.extensions["timeout"]["connect"] == 9
                raise httpx.ConnectTimeout("connection stalled")
            assert request.extensions["timeout"]["connect"] == 3
            return httpx.Response(200, content=b"mp3 bytes", headers={"content-type": "audio/mpeg"})

        original_client = httpx.AsyncClient
        monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs))
        assert asyncio.run(main.prepare_message_speech(db, message, character)) == (b"mp3 bytes", "audio/mpeg")
        assert asyncio.run(main.prepare_message_speech(db, message, character)) == (b"mp3 bytes", "audio/mpeg")
        assert calls.count("/v1/audio/speech") == 2
        assert db.get(MessageSpeech, message.id).content == b"mp3 bytes"
        generated = db.query(VoiceEvent).filter_by(message_id=message.id, event_type="generation").all()
        assert len(generated) == 1
        assert generated[0].status == "success"
        assert generated[0].voice_id == "woman_vi"
        assert generated[0].audio_bytes == len(b"mp3 bytes")
        assert main.roleplay_message_listen(message.id, {"automatic": True, "latency_ms": 42}, db, "voice-user") == {"ok": True}
        listened = db.query(VoiceEvent).filter_by(message_id=message.id, event_type="listen").one()
        assert listened.automatic == 1
        assert listened.latency_ms == 42
        cms_logs = main.admin_voice_logs("all", "all", "", 20, None, db)
        assert cms_logs["total"] == 2
        assert {row["event_type"] for row in cms_logs["rows"]} == {"generation", "listen"}


def test_vbee_voice_catalog_selects_matching_gender_and_language():
    voices = normalize_voices({"voices": [
        {"voice_id": "male_en", "name": "English man", "gender": "male", "language": "en"},
        {"voice_id": "female_vi", "name": "Vietnamese woman", "gender": "female", "language": "vi"},
        {"voice_id": "male_vi", "name": "Vietnamese man", "gender": "male", "language": "vi"},
    ]})
    assert select_voice(voices, "male", "vi") == "male_vi"
    assert select_voice(voices, "female", "vi") == "female_vi"
    assert select_voice(voices, "unspecified", "vi") == "female_vi"
    assert select_voice(voices, "unspecified", "en") == "male_en"
    assert vbee_voice_url("https://api-voice-uat.vbeelabs.ai/v1") == "https://api-voice-uat.vbeelabs.ai/api/v1/voices"
    assert speech_api_base("https://voice-tunnel.example") == "https://voice-tunnel.example/v1"


def test_voice_catalog_retries_connect_timeout(monkeypatch):
    import asyncio
    import httpx
    import character_chat.main as main
    monkeypatch.setenv("GATEWAY_CONNECT_TIMEOUT_SECONDS", "9")
    attempts=[]
    def respond(request):
        attempts.append(request.extensions["timeout"]["connect"])
        if len(attempts)==1:raise httpx.ConnectTimeout("connection stalled")
        return httpx.Response(200,json={"voices":[{"voice_id":"voice_vi","gender":"female","language":"vi"}]})
    original_client=httpx.AsyncClient
    monkeypatch.setattr(main.httpx,"AsyncClient",lambda **kwargs:original_client(transport=httpx.MockTransport(respond),**kwargs))
    voices=asyncio.run(main.vbee_voices("https://catalog-retry.example/v1","test-key"))
    assert voices[0]["id"]=="voice_vi"
    assert attempts==[9,3]


def test_character_gender_prefers_cms_and_known_presets():
    preset = CharacterSpec(name="Mia", preset_type="entertainment_lover")
    assert character_voice_gender(preset) == "female"
    public = CharacterSpec(name="Minh", description="Một chàng trai thích kể chuyện", tts_gender="female")
    assert character_voice_gender(public) == "female"
    public.tts_gender = "unspecified"
    assert character_voice_gender(public) == "male"
    assert character_voice_gender(CharacterSpec(name="Alex")) == "unspecified"


def test_roleplay_suggestion_fallback_keeps_assigned_models(monkeypatch):
    import concurrent.futures
    import character_chat.main as main
    monkeypatch.setattr(main.llm, "purpose_models", {"suggestion": "deepseek/primary", "suggestion_fallback": "openai/backup"})
    meta = main.roleplay_suggestion_initial_meta()
    meta["fallback_reason"] = main.roleplay_suggestion_error(concurrent.futures.TimeoutError())
    _, fallback_meta = main.finalize_suggestions([], "Thử gì cơ?", "vi", meta)
    assert fallback_meta["primary_model"] == "deepseek/primary"
    assert fallback_meta["fallback_model"] == "openai/backup"
    assert fallback_meta["actual_model"] == "local_static"
    assert "1 second" in fallback_meta["fallback_reason"]


@pytest.mark.parametrize("complete", [True, False])
def test_pcm_sse_stream_caches_only_after_done(monkeypatch, complete):
    import base64
    import json
    import httpx
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    import character_chat.main as main
    from character_chat.db import Base, AppSetting, Character, Message, MessageSpeech, ModelConfig, Room, User, VoiceEvent

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(engine, expire_on_commit=False)
    with session() as db:
        db.add(User(id="pcm-user"))
        db.add(Room(id="pcm-room", user_id="pcm-user", name="Chat"))
        db.add(Character(id="pcm-character", user_id="pcm-user", name="Mia", spec=CharacterSpec(name="Mia", tts_voice_id="woman_vi").model_dump_json()))
        db.add(Message(id="pcm-message", room_id="pcm-room", sender_type="character", character_id="pcm-character", text="Hello"))
        db.add(ModelConfig(id="pcm-model", name="TTS", provider="test", model_id="avibi-tts-flash-1.0", api_base="https://tts.example/v1", enabled=1))
        db.add(AppSetting(key="model_profile:pcm-model", value=json.dumps({"purposes": ["tts"]})))
        db.commit()
    def override():
        with session() as db:
            yield db
    monkeypatch.setattr(main, "credential_for_model", lambda _db, _model: "test-key")
    calls = []
    pcm = b"\x00\x00\xff\x7f"
    def respond(request):
        calls.append(request)
        assert request.url.path == "/v1/audio/speech"
        assert request.headers["authorization"] == "Bearer test-key"
        assert request.headers["accept"] == "text/event-stream"
        payload = json.loads(request.read())
        assert payload["response_format"] == "pcm"
        assert payload["stream_format"] == "sse"
        assert payload["voice"] == "woman_vi"
        delta = {"type": "speech.audio.delta", "audio": base64.b64encode(pcm).decode(), "format": "pcm", "sample_rate": 24000}
        second = {**delta, "audio": base64.b64encode(b"\x01\x00\x00\x80").decode()}
        chunks = ["data: " + json.dumps(delta) + "\n\n", "data: " + json.dumps(second) + "\n\n"]
        if complete:
            chunks.append('data: {"type":"speech.audio.done","usage":{}}\n\n')
        return httpx.Response(200, content="".join(chunks), headers={"content-type": "text/event-stream"})
    original_client = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs))
    previous_override = main.app.dependency_overrides.get(main.db_session)
    main.app.dependency_overrides[main.db_session] = override
    try:
        client = TestClient(main.app)
        response = client.post("/v1/roleplay/messages/pcm-message/speech/stream", headers={"X-Demo-User-Id": "pcm-user"})
        assert response.status_code == 200
        assert "speech.audio.delta" in response.text
        assert ('"type":"speech.audio.done"' in response.text) is complete
        with session() as db:
            cached = db.get(MessageSpeech, "pcm-message")
            events = db.query(VoiceEvent).filter_by(message_id="pcm-message", event_type="generation").all()
            assert len(events) == 1
            assert events[0].status == ("success" if complete else "error")
            if complete:
                assert cached and cached.mime_type == "audio/wav" and cached.content.startswith(b"RIFF")
                assert cached.content.endswith(pcm + b"\x01\x00\x00\x80")
            else:
                assert cached is None
        if complete:
            replay = client.post("/v1/roleplay/messages/pcm-message/speech/stream", headers={"X-Demo-User-Id": "pcm-user"})
            assert replay.headers["content-type"].startswith("audio/wav")
            assert replay.content.startswith(b"RIFF")
            assert len(calls) == 1
    finally:
        if previous_override is None:
            main.app.dependency_overrides.pop(main.db_session, None)
        else:
            main.app.dependency_overrides[main.db_session] = previous_override


@pytest.mark.parametrize("language",["zh","ja","ko","my"])
@pytest.mark.parametrize("endpoint",["roleplay_message_speech","roleplay_message_speech_stream"])
def test_unsupported_voice_language_is_blocked_before_gateway(monkeypatch,language,endpoint):
    import asyncio
    from types import SimpleNamespace
    import character_chat.main as main
    rows={
        main.Message:SimpleNamespace(sender_type="character",character_id="character",room_id="room",finish_status="complete",text={"zh":"你好","ja":"こんにちは","ko":"안녕하세요","my":"မင်္ဂလာပါ"}[language]),
        main.Room:SimpleNamespace(user_id="user"),
        main.Character:SimpleNamespace(user_id="user"),
        main.UserProfile:SimpleNamespace(language="en"),
    }
    db=SimpleNamespace(get=lambda model,key:rows.get(model))
    def unexpected(*args,**kwargs):
        pytest.fail("Unsupported voice must not call the gateway")
    monkeypatch.setattr(main,"speech_message_text",lambda db,message,character:message.text)
    monkeypatch.setattr(main,"prepare_message_speech",unexpected)
    monkeypatch.setattr(main,"credential_for_model",unexpected)
    with pytest.raises(main.HTTPException) as error:
        asyncio.run(getattr(main,endpoint)("message",db,"user"))
    assert error.value.status_code==422
    assert "Vietnamese (vi) and English (en)" in error.value.detail


@pytest.mark.parametrize("language",["vi","en",None])
def test_supported_voice_languages_remain_available(language):
    from types import SimpleNamespace
    import character_chat.main as main
    db=SimpleNamespace(get=lambda *args:SimpleNamespace(language=language) if language else None)
    main.require_supported_voice_language(db,"user")
