import json
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from character_chat.models import Base, User, Room, AppSetting
from character_chat.group_topic import group_context,context_from_messages,CONTEXT_PREFIX
from character_chat.engine import suggestion_prompt
from character_chat.schemas import CharacterSpec

def test_topic_name_fallback_and_single_room_are_distinct():
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    peers=[SimpleNamespace(name="Alice"),SimpleNamespace(name="Bob")]
    with sessionmaker(engine)() as db:
        db.add_all([User(id="u"),Room(id="r",user_id="u",name="Nhóm: Alice, Bob")]);db.commit()
        context=group_context(db,"r",peers)
        assert context["topic"]=="" and context["room_name"]==""
        db.get(Room,"r").name="A weekend adventure";db.commit()
        assert group_context(db,"r",peers)["room_name"]=="A weekend adventure"
        db.add(AppSetting(key="room_topic:r",value="Plan a picnic"));db.commit()
        context=group_context(db,"r",peers)
        assert context["topic"]=="Plan a picnic"
        assert group_context(db,"r",peers[:1]) is None
        messages=[{"role":"system","content":"persona\n"+CONTEXT_PREFIX+json.dumps(context)}]
        prompt=suggestion_prompt(messages,CharacterSpec(id="c",name="Alice"),"What should we bring?")
        data=json.loads(prompt[-1]["content"])
        assert data["group_room_context"]["topic"]=="Plan a picnic"
        assert data["suggestion_sender"]=="HUMAN_USER" and data["output_language"]=="en"
        assert context_from_messages([{"role":"user","content":CONTEXT_PREFIX+"{}"}]) is None
    engine.dispose()
