from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from character_chat.models import Base,User,Room,Character,Message,MessageSuggestion
from character_chat.schemas import CharacterSpec
import character_chat.main as main

def test_old_greeting_suggestions_hidden_but_later_reply_kept(monkeypatch):
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main,"localized_greeting",lambda *args:"Hello!")
    monkeypatch.setattr(main,"message_speech_info",lambda *args,**kwargs:{})
    with Session(engine) as db:
        db.add_all([User(id="u"),Room(id="r",user_id="u",name="R"),
          Character(id="c",user_id="u",name="C",spec=CharacterSpec(id="c",name="C").model_dump_json()),
          Message(id="g",room_id="r",sender_type="character",character_id="c",text="Hello!",created_at="2026-01-01T00:00:00")])
        options=["Tell me more","Let us continue","What happens next?"]
        db.add_all([MessageSuggestion(id="g"+str(i),message_id="g",position=i,text=t) for i,t in enumerate(options)])
        db.commit()
        assert main.messages("r",db,"u")[0]["suggestions"]==[]
        db.add_all([Message(id="user",room_id="r",sender_type="user",text="Hi",created_at="2026-01-01T00:01:00"),
          Message(id="reply",room_id="r",sender_type="character",character_id="c",text="Nice to meet you",created_at="2026-01-01T00:02:00")])
        db.add_all([MessageSuggestion(id="reply"+str(i),message_id="reply",position=i,text=t) for i,t in enumerate(options)])
        db.commit()
        history=main.messages("r",db,"u")
        assert history[0]["suggestions"]==[]
        assert history[-1]["suggestions"]==options
        assert db.query(MessageSuggestion).filter_by(message_id="g").count()==3
    engine.dispose()
