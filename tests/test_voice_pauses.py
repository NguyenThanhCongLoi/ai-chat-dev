import struct
from character_chat.voice_pauses import PcmPauseCompactor

def pcm(samples):
    return struct.pack("<"+"h"*len(samples),*samples)

def test_streamed_pauses_are_bounded_without_changing_spoken_samples():
    rate=24000
    voice=[3000,-3000]*1200
    silence=[0]*rate
    clip=pcm(silence+voice+silence+voice)
    processor=PcmPauseCompactor(rate)
    # Irregular boundaries must not reset silence duration.
    result=b"".join(processor.feed(clip[i:i+754]) for i in range(0,len(clip),754))
    assert result==pcm([0]*1440+voice+[0]*5760+voice)

def test_normal_pause_and_first_audio_do_not_wait_for_done():
    processor=PcmPauseCompactor(24000)
    first=pcm([1]*240)
    assert processor.feed(first)==first
    voice=pcm([500,-500]*240)
    assert processor.feed(voice)==voice
    pause=pcm([0]*2400)
    assert processor.feed(pause)==pause
    assert processor.feed(voice)==voice

def test_boundary_silence_spans_multiple_events():
    processor=PcmPauseCompactor(8000)
    assert processor.feed(pcm([1000]*160))==pcm([1000]*160)
    assert len(processor.feed(pcm([0]*1600)))==3200
    assert len(processor.feed(pcm([0]*1600)))==640
    assert processor.feed(pcm([1000]*160))==pcm([1000]*160)


def test_short_greeting_reuses_stored_translation_language():
    import hashlib
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from character_chat import main
    from character_chat.schemas import CharacterSpec
    engine=create_engine("sqlite://")
    main.Base.metadata.create_all(engine)
    with Session(engine) as db:
        character=main.Character(id="c",user_id="u",name="Mia",
            spec=CharacterSpec(name="Mia",initial_greeting="Xin chào!").model_dump_json())
        digest=hashlib.sha256("Xin chào!".encode()).hexdigest()
        db.add_all([main.User(id="u"),main.UserProfile(user_id="u",language="en"),character,
            main.AppSetting(key=f"character_translation:v3:u:en:{digest}",value="Welcome back!")])
        db.commit()
        message=main.Message(id="m",room_id="r",sender_type="character",text="Xin chào!",speech_segments="[]")
        info=main.message_speech_info(message,"Welcome back!",db,character)
        assert info=={"speech_languages":["en"],"speech_supported":True}
        # UI language alone must not relabel unknown text as English.
        assert main.message_speech_info(message,"Unmatched",db,character)["speech_supported"] is False
    engine.dispose()
