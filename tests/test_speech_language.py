import asyncio, base64, io, json, wave
import pytest
from character_chat.speech_language import LanguageStream, detect_speech_language, sentence_segments, speech_info

def test_fragmented_metadata_never_leaks_and_does_not_wait_for_sentence():
    parser=LanguageStream();events=[]
    for chunk in ["[[la","ng:vi]]Chào ","bạn! [[lang:","en]]How are ","you?"]:
        events+=parser.feed(chunk)
    events+=parser.feed("",final=True)
    assert [value for event,value in events if event=="language"]==["vi","en"]
    assert "".join(value for event,value in events if event=="delta")=="Chào bạn! How are you?"
    parser=LanguageStream();assert parser.feed("Hello ")==[("delta","Hello ")]
    assert parser.feed("[[lang:")==[]
    assert parser.feed("",final=True)==[]

@pytest.mark.parametrize("text,code",[("你好","zh"),("こんにちは","ja"),("안녕하세요","ko"),("မင်္ဂလာပါ","my"),("Bonjour","fr"),("Hola","es"),("Hello","en"),("Chào bạn","vi"),("xyz","unknown")])
def test_content_language_ignores_ui(text,code):
    assert detect_speech_language(text)==code
    assert speech_info(text)["speech_supported"]==(code in {"vi","en"})
    if code not in {"vi","en","unknown"}:
        assert not speech_info(text,[{"text":text,"language":"en"}])["speech_supported"]

@pytest.fixture
def setup_voice(tmp_path,monkeypatch):
    import httpx
    import character_chat.main as main
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from character_chat.schemas import CharacterSpec
    engine=create_engine("sqlite:///"+str(tmp_path/"mixed.sqlite"),connect_args={"check_same_thread":False})
    main.Base.metadata.create_all(engine);session=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(main,"Session",session)
    monkeypatch.setattr(main,"credential_for_model",lambda *_:"test-key")
    segments=[{"text":"Chào bạn! ","language":"vi"},{"text":"How are you?","language":"en"}]
    with session() as db:
        db.add_all([main.User(id="u"),main.User(id="other"),main.UserProfile(user_id="u",language="ja"),main.Room(id="r",user_id="u",name="Chat"),
          main.Character(id="c",user_id="u",name="Mia",spec=CharacterSpec(name="Mia",tts_voice_mode="separate",tts_voice_vi="voice-vi",tts_voice_en="voice-en").model_dump_json()),
          main.Message(id="m",room_id="r",sender_type="character",character_id="c",text="Chào bạn! How are you?",speech_segments=json.dumps(segments)),
          main.ModelConfig(id="tts",name="TTS",provider="test",model_id="flash",api_base="https://tts.example/v1",enabled=1),
          main.AppSetting(key="model_profile:tts",value=json.dumps({"purposes":["tts"]}))]);db.commit()
    calls=[]
    def respond(request):
        payload=json.loads(request.read());calls.append(payload)
        event={"type":"speech.audio.delta","format":"pcm","sample_rate":24000,"audio":base64.b64encode(b"\x01\x00"*10).decode()}
        return httpx.Response(200,content="data: "+json.dumps(event)+"\n\ndata: "+json.dumps({"type":"speech.audio.done"})+"\n\n",headers={"content-type":"text/event-stream"})
    original=httpx.AsyncClient
    monkeypatch.setattr(main.httpx,"AsyncClient",lambda **kwargs:original(transport=httpx.MockTransport(respond),**kwargs))
    yield main,session,calls
    engine.dispose()

def test_mixed_voice_cache_shared_mode_volume_and_isolation(setup_voice):
    main,session,calls=setup_voice
    async def listen(db):
        response=await main.roleplay_message_speech_stream("m",db,"u")
        if response.media_type=="text/event-stream":
            return "".join([chunk async for chunk in response.body_iterator])
        return response
    with session() as db:
        data=asyncio.run(listen(db))
        assert data.count('"type": "speech.audio.delta"')==2
        assert data.count("speech.audio.done")==1
        assert [item["voice"] for item in calls]==["voice-vi","voice-en"]
        cached=db.get(main.MessageSpeech,"m");assert cached is not None
        with wave.open(io.BytesIO(cached.content),"rb") as wav:assert wav.getnframes()==20
        assert asyncio.run(listen(db)).media_type=="audio/wav";assert len(calls)==2
        before=main.speech_cache_signature(db,db.get(main.Character,"c"),"Chào bạn! How are you?")
        assert main.set_voice_volume("c",{"volume":.4},db,"u")=={"volume":.4}
        assert main.voice_preferences(db,"u")=={"c":.4}
        assert main.voice_preferences(db,"other")=={}
        with pytest.raises(main.HTTPException):main.set_voice_volume("c",{"volume":.5},db,"other")
        with pytest.raises(main.HTTPException):main.set_voice_volume("c",{"volume":2},db,"u")
        assert main.speech_cache_signature(db,db.get(main.Character,"c"),"Chào bạn! How are you?")==before
        char=db.get(main.Character,"c");spec=main.spec(char);spec.tts_voice_mode="shared";spec.tts_voice_id="shared-clone";char.spec=spec.model_dump_json();db.commit()
        asyncio.run(listen(db))
        assert [item["voice"] for item in calls[-2:]]==["shared-clone","shared-clone"]

def test_separate_mode_never_uses_wrong_language_catalog_default():
    from character_chat.voice import select_voice
    voices=[{"id":"vi-only","language":"vi","gender":"female"}]
    assert select_voice(voices,"female","en",strict_language=True)==""
    assert select_voice(voices,"female","vi",strict_language=True)=="vi-only"

def test_response_llm_supplies_language_in_one_stream_without_raw_markers(monkeypatch):
    import character_chat.main as main
    monkeypatch.setattr(main.llm,"model","language-model")
    monkeypatch.setattr(main.llm,"fallback_model","")
    monkeypatch.setattr(main.llm,"fallback_model_2","")
    monkeypatch.setattr(main.llm,"api_key","test-key")
    monkeypatch.setattr(main,"model_circuit_remaining",lambda *_:0)
    monkeypatch.setattr(main,"record_model_success",lambda *_:None)
    calls=[]
    def upstream(*args):
        calls.append(args)
        yield "[[la"
        yield "ng:vi]]Chào bạn! [[lang:"
        yield "en]]How are you?"
        yield {"_stream_status":"complete"}
    monkeypatch.setattr(main,"chat_stream",upstream)
    events=list(main.stream_roleplay_answer([], .5, 200, "normal"))
    assert len(calls)==1
    assert "[[lang:vi]]" in calls[0][0][-1]["content"]
    assert [value for event,value in events if event=="language"]==["vi","en"]
    assert "".join(value for event,value in events if event=="delta")=="Chào bạn! How are you?"

def test_character_language_switches_and_future_voice():
    from character_chat.schemas import CharacterSpec
    from character_chat.speech_language import configured_voice
    item=CharacterSpec(name="Ruby",tts_voice_id="shared")
    assert speech_info("Chào bạn!",spec=item)["speech_supported"]
    assert speech_info("Hello there!",spec=item)["speech_supported"]
    assert not speech_info("こんにちは",spec=item)["speech_supported"]
    item=CharacterSpec(name="Ruby",tts_languages={
        "vi":{"enabled":False}, "ja":{"enabled":True,"voice_id":"ja-clone"},
        "ko":{"enabled":True,"voice_id":""},
    })
    assert not speech_info("Chào bạn!",spec=item)["speech_supported"]
    assert speech_info("Hello there!",spec=item)["speech_supported"]
    assert speech_info("こんにちは",spec=item)["speech_supported"]
    assert configured_voice(item,"ja")=="ja-clone"
    assert configured_voice(item,"ko")==""
    assert not speech_info("안녕하세요",spec=item)["speech_supported"]
    assert not speech_info("Chào bạn! Hello there!",spec=item)["speech_supported"]

def test_vietnamese_reply_is_not_hidden_by_wrong_model_language_tag():
    text="Chống cằm, mắt hơi nheo lại, nhìn thẳng một lúc lâu. Không phải khó chịu. Chỉ là cái kiểu nói nửa vời rồi để người khác tự đoán, tôi không thích."
    assert speech_info(text,[{"text":text,"language":"ja"}])=={"speech_languages":["vi"],"speech_supported":True}

def test_disabled_voice_rejects_cache_and_future_voice_routes_to_assigned_id(setup_voice):
    from character_chat.schemas import CharacterSpec
    main,session,calls=setup_voice
    with session() as db:
        char=db.get(main.Character,"c")
        item=main.spec(char)
        item.tts_languages=CharacterSpec(name="Ruby",tts_languages={"en":{"enabled":False}}).tts_languages
        char.spec=item.model_dump_json();db.commit()
        info=main.message_speech_info(db.get(main.Message,"m"),"Chào bạn! How are you?",db,char)
        assert not info["speech_supported"]
        with pytest.raises(main.HTTPException) as exc:
            asyncio.run(main.roleplay_message_speech_stream("m",db,"u"))
        assert exc.value.status_code==422
        assert calls==[]
        before=main.speech_cache_signature(db,char,"")
        item.tts_languages=CharacterSpec(name="Ruby",tts_languages={"ja":{"enabled":True,"voice_id":"japanese-voice"}}).tts_languages
        char.spec=item.model_dump_json()
        msg=db.get(main.Message,"m");msg.text="こんにちは";msg.speech_segments=json.dumps([{"text":msg.text,"language":"ja"}]);db.commit()
        assert main.speech_cache_signature(db,char,"")!=before
        assert main.message_speech_info(msg,msg.text,db,char)["speech_supported"]
        async def consume():
            response=await main.roleplay_message_speech_stream("m",db,"u")
            return "".join([chunk async for chunk in response.body_iterator])
        assert "speech.audio.done" in asyncio.run(consume())
        assert calls[-1]["voice"]=="japanese-voice"

def test_cms_persists_character_voice_language_switches(setup_voice):
    main,session,_=setup_voice
    settings={"vi":{"enabled":False,"voice_id":""},"en":{"enabled":True,"voice_id":""},"ja":{"enabled":True,"voice_id":"ja-id"}}
    with session() as db:
        result=main.admin_update_character("c",{"tts_languages":settings},None,db)
        assert result["spec"]["tts_languages"]==settings
        db.expire_all()
        assert main.character_out(db.get(main.Character,"c"))["tts_languages"]==settings
        assert db.get(main.AppSetting,"character_override:c") is not None
