from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from character_chat import main
from character_chat.schemas import CharacterSpec

def test_deleting_character_clears_emotional_state_and_readding_starts_fresh(tmp_path):
    engine=create_engine("sqlite:///"+str(tmp_path/"feelings.sqlite"))
    main.Base.metadata.create_all(engine)
    Session=sessionmaker(engine,expire_on_commit=False)
    with Session() as db:
        db.add(main.User(id="user"))
        db.add_all([main.Character(id=id,user_id="user",name=id,spec=CharacterSpec(name=id).model_dump_json()) for id in ("ruby","other")])
        db.add_all([
            main.Relationship(id="relationship",user_id="user",character_id="ruby",familiarity=.8,trust=.7,affinity=.6,tension=.4),
            main.CharacterState(id="state",user_id="user",character_id="ruby",emotion="angry",intensity=.9),
            main.RelationshipEvent(id="event",user_id="user",character_id="ruby",event_type="conflict"),
            main.Relationship(id="other-relationship",user_id="user",character_id="other",familiarity=.5),
            main.CharacterState(id="other-state",user_id="user",character_id="other",emotion="happy",intensity=.6),
        ])
        db.commit()
        assert main.delete_character("ruby",db,"user")["deleted"]
        db.expire_all()
        assert db.query(main.Relationship).filter_by(character_id="ruby").count()==0
        assert db.query(main.CharacterState).filter_by(character_id="ruby").count()==0
        assert db.query(main.RelationshipEvent).filter_by(character_id="ruby").count()==0
        assert db.get(main.Relationship,"other-relationship").familiarity==.5
        assert db.get(main.CharacterState,"other-state").emotion=="happy"
        db.add(main.Character(id="ruby",user_id="user",name="ruby",spec=CharacterSpec(name="ruby").model_dump_json()))
        db.commit()
        result=main.get_relationship("ruby",db,"user")
        assert all(result[key]==0 for key in ("familiarity","trust","affection","conflict","emotion_intensity"))
        assert result["emotion"]=="neutral"
        assert result["recent_events"]==[]
    engine.dispose()


def test_deleting_room_resets_member_feelings_but_keeps_collection_and_other_users(tmp_path):
    engine=create_engine("sqlite:///"+str(tmp_path/"room-reset.sqlite"))
    main.Base.metadata.create_all(engine)
    with sessionmaker(engine,expire_on_commit=False)() as db:
        db.add_all([main.User(id="user"),main.User(id="other-user")])
        for id in ("ruby","elf","unrelated"):
            db.add(main.Character(id=id,user_id="user",name=id,spec=CharacterSpec(id=id,name=id).model_dump_json()))
        db.add(main.Room(id="room",user_id="user",name="Group"))
        for id in ("ruby","elf"):
            db.add(main.RoomMember(id="member-"+id,room_id="room",character_id=id))
            db.add(main.Relationship(id="rel-"+id,user_id="user",character_id=id,familiarity=.8,trust=.7,affinity=.6,tension=.4,respect=.5))
            db.add(main.CharacterState(id="state-"+id,user_id="user",character_id=id,emotion="angry",intensity=.9))
            db.add(main.RelationshipEvent(id="event-"+id,user_id="user",character_id=id,event_type="conflict"))
            db.add(main.CharacterReflection(id="reflection-"+id,user_id="user",character_id=id,content="An old conflict"))
        db.add_all([
            main.Relationship(id="other-user-rel",user_id="other-user",character_id="ruby",familiarity=.6),
            main.CharacterState(id="other-user-state",user_id="other-user",character_id="ruby",emotion="happy",intensity=.6),
            main.Relationship(id="unrelated-rel",user_id="user",character_id="unrelated",familiarity=.5),
        ])
        db.commit()
        assert main.delete_room("room",db,"user")["deleted"]
        db.expire_all()
        assert db.get(main.Room,"room") is None
        for id in ("ruby","elf"):
            assert db.get(main.Character,id) is not None
            result=main.get_relationship(id,db,"user")
            assert all(result[key]==0 for key in ("familiarity","trust","affection","conflict","respect","emotion_intensity"))
            assert result["emotion"]=="neutral" and result["recent_events"]==[]
            assert db.query(main.CharacterReflection).filter_by(user_id="user",character_id=id).count()==0
        assert db.get(main.Relationship,"other-user-rel").familiarity==.6
        assert db.get(main.CharacterState,"other-user-state").emotion=="happy"
        assert db.get(main.Relationship,"unrelated-rel").familiarity==.5
    engine.dispose()


def test_late_background_analysis_does_not_restore_deleted_room_feelings(tmp_path,monkeypatch):
    from character_chat import background
    from character_chat.schemas import TurnAnalysis
    engine=create_engine("sqlite:///"+str(tmp_path/"late-analysis.sqlite"))
    main.Base.metadata.create_all(engine)
    Local=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(background,"Session",Local)
    with Local() as db:
        db.add(main.User(id="user"))
        db.add(main.Character(id="ruby",user_id="user",name="Ruby",spec=CharacterSpec(id="ruby",name="Ruby").model_dump_json()))
        db.add(main.Room(id="room",user_id="user",name="Chat"))
        db.add(main.RoomMember(id="member",room_id="room",character_id="ruby"))
        db.add(main.Message(id="question",room_id="room",sender_type="user",text="Old conflict"))
        db.commit()
    def analyze_and_delete(*args,**kwargs):
        with Local() as db:main.delete_room("room",db,"user")
        return TurnAnalysis(confidence=.9,significance=.8,relationship_event="conflict",
                            reflection="Old anger",memory_worthy=True,memory_summary="Old conflict")
    monkeypatch.setattr(background.llm,"json",analyze_and_delete)
    background.analyze_turn("user","room","question",["ruby"])
    with Local() as db:
        assert db.query(main.RelationshipEvent).count()==0
        assert db.query(main.CharacterReflection).count()==0
        assert db.query(main.MoodObservation).count()==0
        assert db.query(main.Memory).count()==0
    engine.dispose()

def test_reset_rejects_late_analysis_from_another_retained_room(tmp_path,monkeypatch):
    from character_chat import background,jev
    from character_chat.schemas import TurnAnalysis
    engine=create_engine("sqlite:///"+str(tmp_path/"cross-room-late.sqlite"))
    main.Base.metadata.create_all(engine)
    Local=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(background,"Session",Local)
    monkeypatch.setattr(jev,"enabled",lambda task:False)
    with Local() as db:
        db.add(main.User(id="user"))
        db.add(main.Character(id="selene",user_id="user",name="Selene",spec=CharacterSpec(id="selene",name="Selene").model_dump_json()))
        for room in ("deleted","retained"):
            db.add(main.Room(id=room,user_id="user",name=room))
            db.add(main.RoomMember(id="member-"+room,room_id=room,character_id="selene"))
        db.add(main.Message(id="old-question",room_id="retained",sender_type="user",text="Remember this old event"))
        db.commit()
    def analyzed(*args,**kwargs):
        with Local() as db:main.delete_room("deleted",db,"user")
        return TurnAnalysis(confidence=.9,significance=.8,relationship_event="conflict",reflection="Old conflict",memory_worthy=True,memory_summary="Old memory")
    monkeypatch.setattr(background.llm,"json",analyzed)
    background.analyze_turn("user","retained","old-question",["selene"])
    with Local() as db:
        assert db.get(main.Message,"old-question") is not None
        assert db.query(main.Memory).count()==0
        assert db.query(main.CharacterReflection).count()==0
        assert db.query(main.RelationshipEvent).count()==0
    engine.dispose()
