import json
import pytest
import httpx
from fastapi import HTTPException
from character_chat import character_policy as policy
from character_chat.schemas import CharacterSpec

@pytest.fixture
def classifier(monkeypatch):
    monkeypatch.setenv("ADMIN_MODERATION_MODEL","moderator")
    monkeypatch.setenv("ADMIN_MODERATION_API_KEY","fake")
    monkeypatch.setenv("ADMIN_MODERATION_API_BASE","https://moderator.invalid/v1")
    calls=[]
    response={"decision":"allow","categories":[]}
    def handler(request):
        calls.append(json.loads(request.read()))
        return httpx.Response(200,json={"choices":[{"message":{"content":json.dumps(response)}}]})
    original=httpx.Client
    monkeypatch.setattr(policy.httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    return response,calls

@pytest.mark.parametrize("description",["Chúa trong một bối cảnh tôn giáo","A political leader","宗教人物","宗教的な人物","종교 인물","ဘာသာရေးဇာတ်ကောင်","តួអង្គសាសនា"])
def test_every_language_is_submitted_even_without_keyword_match(classifier,description):
    decision,calls=classifier;decision.update(decision="block",categories=["religion"])
    with pytest.raises(HTTPException) as exc:policy.enforce_character_policy({"name":"X","description":description})
    assert exc.value.status_code==400
    assert exc.value.detail["categories"]==["religion"]
    assert json.loads(calls[-1]["messages"][-1]["content"])["description"]==description

def test_all_content_fields_are_checked_and_benign_under18_character_is_allowed(classifier):
    _,calls=classifier
    item=CharacterSpec(name="Mai",identity={"age_description":"16 tuổi"},scenario="Học tập",
        sample_dialogues=["Chào bạn"],persona_knowledge=["Kiến thức học đường"])
    policy.enforce_character_policy(item)
    data=json.loads(calls[0]["messages"][-1]["content"])
    assert data["identity"]["age_description"]=="16 tuổi"
    assert data["sample_dialogues"]==["Chào bạn"]
    assert data["persona_knowledge"]==["Kiến thức học đường"]
    assert "tts_voice_id" not in data
    assert "Age, gender" in calls[0]["messages"][0]["content"]

@pytest.mark.parametrize("category",["politics","religion","sexual","minor_sexual","harmful"])
def test_blocked_content_returns_specific_category(classifier,category):
    decision,_=classifier;decision.update(decision="block",categories=[category])
    with pytest.raises(HTTPException) as exc:policy.enforce_character_policy({"description":"input"})
    assert exc.value.detail["code"]=="character_policy_blocked"
    assert exc.value.detail["categories"]==[category]

def test_uncertain_does_not_create_or_report_confirmed_violation(classifier):
    decision,_=classifier;decision.update(decision="uncertain",categories=[])
    with pytest.raises(HTTPException) as exc:policy.enforce_character_policy({"name":"X"})
    assert exc.value.status_code==503
    assert exc.value.detail["code"]=="character_policy_unavailable"

def test_missing_moderator_fails_closed(monkeypatch):
    monkeypatch.delenv("ADMIN_MODERATION_MODEL",raising=False)
    with pytest.raises(HTTPException) as exc:policy.enforce_character_policy({"name":"X"})
    assert exc.value.status_code==503

def test_voice_only_edit_does_not_recheck_unchanged_content(classifier):
    _,calls=classifier
    previous=CharacterSpec(name="X");updated=previous.model_copy(update={"tts_volume":1.5})
    policy.enforce_character_policy(updated,previous)
    assert calls==[]
    updated.description="new description";policy.enforce_character_policy(updated,previous)
    assert len(calls)==1

def test_full_character_is_checked_before_any_database_write(classifier,tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from character_chat import main
    engine=create_engine("sqlite:///"+str(tmp_path/"policy.sqlite"))
    main.Base.metadata.create_all(engine)
    decision,_=classifier;decision.update(decision="block",categories=["sexual"])
    with sessionmaker(engine)() as db:
        with pytest.raises(HTTPException):main.save_character(db,"u",CharacterSpec(name="X"))
        assert db.query(main.Character).count()==0
        assert db.query(main.CharacterVersion).count()==0
    engine.dispose()

@pytest.mark.parametrize("result",[
    {"decision":"allow","categories":["religion"]},
    {"decision":"block","categories":[]},
    {"decision":"invalid","categories":[]},
])
def test_inconsistent_classifier_output_is_not_reported_as_confirmed_violation(classifier,result):
    decision,_=classifier;decision.clear();decision.update(result)
    with pytest.raises(HTTPException) as exc:policy.enforce_character_policy({"name":"X"})
    assert exc.value.status_code==503

def test_generated_output_and_cms_changes_share_the_policy_gate(monkeypatch,tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from character_chat import main
    from character_chat.schemas import GenerateIn
    engine=create_engine("sqlite:///"+str(tmp_path/"entrypoints.sqlite"))
    main.Base.metadata.create_all(engine)
    calls=[]
    def gate(data,previous=None):
        values=data.model_dump() if hasattr(data,"model_dump") else data
        calls.append(values)
        if values.get("description")=="blocked":
            raise HTTPException(400,detail={"code":"character_policy_blocked","categories":["religion"]})
    monkeypatch.setattr(main,"enforce_character_policy",gate)
    monkeypatch.setattr(main,"compile_character",lambda *a,**kw:CharacterSpec(name="X",description="blocked"))
    with sessionmaker(engine,expire_on_commit=False)() as db:
        db.add(main.User(id="u"));db.commit()
        with pytest.raises(HTTPException) as exc:
            main.generate_character(GenerateIn(name="X",description="normal user input"),db,"u")
        assert exc.value.status_code==400
        assert calls[0]["description"]=="normal user input"
        assert calls[-1]["description"]=="blocked"
        assert db.query(main.Character).count()==0
        item=CharacterSpec(name="X")
        db.add(main.Character(id="existing",user_id="u",name="X",spec=item.model_dump_json()));db.commit()
        with pytest.raises(HTTPException):main.patch_character("existing",{"description":"blocked"},db,"u")
        assert main.spec(db.get(main.Character,"existing")).description==""
        with pytest.raises(HTTPException):main.admin_update_character("existing",{"description":"blocked"},None,db)
        assert main.spec(db.get(main.Character,"existing")).description==""
    engine.dispose()

def test_publication_tags_are_checked_before_visibility_changes(monkeypatch,tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from character_chat import main
    engine=create_engine("sqlite:///"+str(tmp_path/"publication.sqlite"))
    main.Base.metadata.create_all(engine)
    received=[]
    def reject(data,previous=None):
        received.append(data)
        raise HTTPException(400,detail={"code":"character_policy_blocked","categories":["politics"]})
    monkeypatch.setattr(main,"enforce_character_policy",reject)
    with sessionmaker(engine,expire_on_commit=False)() as db:
        db.add(main.User(id="u"))
        db.add(main.Character(id="c",user_id="u",name="X",spec=CharacterSpec(name="X").model_dump_json()))
        db.add(main.CharacterPublication(character_id="c",creator_user_id="u",is_public=0,tags="[]"))
        db.commit()
        with pytest.raises(HTTPException):
            main.update_character_publication("c",{"tags":["political tag"],"is_public":True},db,"u")
        assert received[-1]["tags"]==["political tag"]
        assert db.get(main.CharacterPublication,"c").is_public==0
        assert db.get(main.CharacterPublication,"c").tags=="[]"
    engine.dispose()

def test_mirror_birth_date_is_included_without_serialization_error(classifier):
    from datetime import date
    from character_chat.schemas import MirrorIn
    _,calls=classifier
    data=MirrorIn(name="Mai",description="Một người bạn tốt",birth_date=date(2000,1,1))
    policy.enforce_character_policy(data)
    assert json.loads(calls[-1]["messages"][-1]["content"])["birth_date"]=="2000-01-01"
