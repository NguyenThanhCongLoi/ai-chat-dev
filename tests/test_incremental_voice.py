import asyncio, base64, io, json, threading, wave
from character_chat.incremental_voice import SentenceBuffer, SentenceSpeech, replay_parts

def test_sentence_actions_and_decimal():
    buffer=SentenceBuffer()
    assert buffer.feed("**smiles. ")==[]
    assert buffer.feed("warmly** Hello there. Next")==["**smiles. warmly** Hello there."]
    assert buffer.feed(" sentence!")==["Next sentence!"]
    assert buffer.feed(" unfinished")==[]
    assert buffer.feed("",True)==["unfinished"]
    assert SentenceBuffer().feed("Value 3.14 is fine. More")==["Value 3.14 is fine."]

def test_early_voice_and_durable_cache(tmp_path,monkeypatch):
    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import character_chat.main as main
    from character_chat.schemas import CharacterSpec
    engine=create_engine("sqlite:///"+str(tmp_path/"voice.sqlite"),connect_args={"check_same_thread":False})
    main.Base.metadata.create_all(engine)
    session=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(main,"Session",session)
    monkeypatch.setattr(main,"credential_for_model",lambda *_:"test-key")
    with session() as db:
        db.add_all([main.User(id="u"),main.Room(id="r",user_id="u",name="Chat"),main.Character(id="c",user_id="u",name="Mia",spec=CharacterSpec(name="Mia",tts_voice_id="old").model_dump_json()),main.Message(id="m",room_id="r",sender_type="character",character_id="c",text="",finish_status="generating"),main.ModelConfig(id="tts",name="TTS",provider="test",model_id="flash",api_base="https://tts.example/v1",enabled=1),main.AppSetting(key="model_profile:tts",value=json.dumps({"purposes":["tts"]}))]);db.commit()
        signature=main.speech_cache_signature(db,db.get(main.Character,"c"),"")
        db.add(main.MessageSpeechRun(message_id="m",signature=signature));db.commit()
    calls=[];first=threading.Event();release=threading.Event()
    def respond(request):
        calls.append(json.loads(request.read()));first.set()
        pcm=b"\x01\x00"*240
        events=[{"type":"speech.audio.delta","format":"pcm","sample_rate":24000,"audio":base64.b64encode(pcm).decode()},{"type":"speech.audio.done"}]
        class Delayed(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield ("data: "+json.dumps(events[0])+"\n\n").encode()
                if len(calls)==1:assert await asyncio.to_thread(release.wait,4)
                yield ("data: "+json.dumps(events[1])+"\n\n").encode()
        return httpx.Response(200,stream=Delayed(),headers={"content-type":"text/event-stream"})
    original=httpx.AsyncClient
    monkeypatch.setattr(main.httpx,"AsyncClient",lambda **kwargs:original(transport=httpx.MockTransport(respond),**kwargs))
    job=SentenceSpeech(main,"m","u",signature)
    try:
        job.feed("Hello there. ")
        assert first.wait(3)
        async def early():
            stream=replay_parts(main,"m",signature)
            assert "speech.audio.delta" in await asyncio.wait_for(anext(stream),3)
            await stream.aclose()
        asyncio.run(early())
        with session() as db:
            assert db.get(main.MessageSpeech,"m") is None
            msg=db.get(main.Message,"m");msg.text="Hello there. How are you? Welcome back!";msg.finish_status="";msg.speech_segments=json.dumps([{"text":msg.text,"language":"en"}]);db.commit()
        job.feed("How are you? Welcome back!",language="en");job.finish("Hello there. How are you? Welcome back!")
        release.set()
        job.thread.join(4)
        assert not job.thread.is_alive()
        assert [c["input"] for c in calls]==["Hello there.","How are you? Welcome back!"]
        with session() as db:
            cached=db.get(main.MessageSpeech,"m");assert cached is not None
            with wave.open(io.BytesIO(cached.content),"rb") as wav:assert wav.getnframes()==480
            assert db.get(main.MessageSpeechRun,"m").status=="ready"
            assert db.query(main.MessageSpeechPart).count()==0
            response=asyncio.run(main.roleplay_message_speech_stream("m",db,"u"))
            assert response.media_type=="audio/wav";assert len(calls)==2
    finally:
        release.set()
        if job.thread.is_alive():job.cancel();job.thread.join(4)
        engine.dispose()
