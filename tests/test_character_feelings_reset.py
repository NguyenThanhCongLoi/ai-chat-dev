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
