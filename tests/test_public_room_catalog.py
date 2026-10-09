
import os
os.environ.setdefault("DATABASE_URL","sqlite://")
from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from character_chat.models import Base,User,Character,CharacterPublication,Room,RoomMember,Message,AppSetting
from character_chat.schemas import CharacterSpec,RoomIn
from character_chat import main

def test_public_room_only_exposes_public_members_and_starts_private_chat(monkeypatch):
    monkeypatch.setattr(main,"enforce_character_policy",lambda *args:None)
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(main,"localized_greeting",lambda *args:"Hello")
    async def speech(*args):return None
    monkeypatch.setattr(main,"prepare_message_speech",speech)
    with Session() as db:
        db.add_all([User(id="owner"),User(id="visitor")])
        for key in ["a","b"]:
            character=CharacterSpec(id=key,name=key)
            db.add(Character(id=key,user_id="owner",name=key,spec=character.model_dump_json()))
            db.add(CharacterPublication(character_id=key,creator_user_id="owner",is_public=0))
        db.commit()
        with pytest.raises(HTTPException):
            main.create_room(RoomIn(name="Team",topic="Weekend plans",character_ids=["a","b"],is_public=True),db,"owner")
        for key in ["a","b"]:db.get(CharacterPublication,key).is_public=1
        db.commit()
        room=main.create_room(RoomIn(name="Team",topic="Weekend plans",character_ids=["a","b"],is_public=True),db,"owner")
        db.add(Message(id="secret-message",room_id=room["id"],sender_type="user",text="Private owner conversation"))
        db.commit()
        listing=main.public_rooms(db,"visitor")
        assert listing[0]["id"]==room["id"] and "messages" not in listing[0]
        with pytest.raises(HTTPException):main.messages(room["id"],db,"visitor")
        copy=main.start_public_room(room["id"],db,"visitor")
        assert copy["id"]!=room["id"] and copy["is_public"] is False
        assert copy["topic"]=="Weekend plans"
        assert db.get(Room,copy["id"]).user_id=="visitor"
        assert not any(row.text=="Private owner conversation" for row in db.query(Message).filter_by(room_id=copy["id"]))
        assert main.start_public_room(room["id"],db,"visitor")["id"]==copy["id"]
        db.get(CharacterPublication,"a").is_public=0;db.commit()
        assert main.public_rooms(db,"visitor")==[]
        with pytest.raises(HTTPException):main.start_public_room(room["id"],db,"visitor")
    engine.dispose()

def test_favorites_persist_per_account():
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    with sessionmaker(engine)() as db:
        db.add_all([User(id="one"),User(id="two")]);db.commit()
        main.save_catalog_favorites({"key":"character:test","favorite":True},db,"one")
        assert main.catalog_favorites(db,"one")=={"keys":["character:test"]}
        assert main.catalog_favorites(db,"two")=={"keys":[]}
        main.save_catalog_favorites({"key":"character:test","favorite":False},db,"one")
        assert main.catalog_favorites(db,"one")=={"keys":[]}
    engine.dispose()


def test_canonical_system_members_can_share_room_without_becoming_public(monkeypatch):
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    templates=[CharacterSpec(id="preset-"+key,name="System "+key,creation_type="preset",preset_type=key) for key in ["a","b"]]
    monkeypatch.setattr(main,"effective_presets",lambda db:templates)
    monkeypatch.setattr(main,"localized_greeting",lambda *args:"Hello")
    def unexpected_moderation(*args,**kwargs):
        pytest.fail("Catalog reuse must not call the creation moderator")
    monkeypatch.setattr(main,"enforce_character_policy",unexpected_moderation)
    monkeypatch.setattr(main,"install_default_expressions",lambda *args:None)
    monkeypatch.setattr(main,"character_source_image",lambda *args:None)
    async def speech(*args):return None
    monkeypatch.setattr(main,"prepare_message_speech",speech)
    with sessionmaker(engine,expire_on_commit=False)() as db:
        db.add_all([User(id="owner"),User(id="visitor")])
        for source in templates:
            card=source.model_copy(deep=True);card.id="owned-"+source.preset_type
            card.system_prompt=main.default_character_prompt(source)
            db.add(Character(id=card.id,user_id="owner",name=card.name,spec=card.model_dump_json()))
            db.add(CharacterPublication(character_id=card.id,creator_user_id="owner",is_public=0))
        db.commit()
        room=main.create_room(RoomIn(character_ids=["owned-a","owned-b"],is_public=True),db,"owner")
        assert len(main.public_rooms(db,"visitor"))==1
        assert all(db.get(CharacterPublication,id).is_public==0 for id in room["character_ids"])
        copy=main.start_public_room(room["id"],db,"visitor")
        assert copy["id"]!=room["id"] and not copy["is_public"]
        assert len(copy["character_ids"])==2
        assert all(db.get(Character,id).user_id=="visitor" for id in copy["character_ids"])
        assert all(main.spec(db.get(Character,id)).creation_type=="preset" for id in copy["character_ids"])
        assert main.start_public_room(room["id"],db,"visitor")["id"]==copy["id"]
        main.patch_room(room["id"],{"is_public":False},db,"owner")
        assert not main.room_is_public(db,room["id"])
        main.patch_room(room["id"],{"is_public":True},db,"owner")
        changed=main.spec(db.get(Character,"owned-a"));changed.description="Private custom details"
        db.get(Character,"owned-a").spec=changed.model_dump_json();db.commit()
        assert main.public_rooms(db,"visitor")==[]
        with pytest.raises(HTTPException):main.start_public_room(room["id"],db,"visitor")
    engine.dispose()


def test_preset_marker_alone_never_exposes_private_character(monkeypatch):
    from character_chat.models import CharacterAsset
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    source=CharacterSpec(id="preset-a",name="System",creation_type="preset",preset_type="a")
    monkeypatch.setattr(main,"effective_presets",lambda db:[source])
    with sessionmaker(engine)() as db:
        db.add(User(id="owner"))
        card=source.model_copy(deep=True);card.id="private";card.description="Unpublished content"
        db.add(Character(id=card.id,user_id="owner",name=card.name,spec=card.model_dump_json()));db.commit()
        row=db.get(Character,card.id)
        assert not main.room_member_shareable(db,row)
        card.description=source.description;row.spec=card.model_dump_json()
        db.add(CharacterAsset(character_id=card.id,content=b"private picture",mime_type="image/png"));db.commit()
        assert not main.room_member_shareable(db,row)
    engine.dispose()


def test_catalog_reuse_skips_moderation_but_custom_creation_still_checks(monkeypatch):
    from fastapi import BackgroundTasks
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    source=CharacterSpec(id="preset-a",name="Canonical",creation_type="preset",preset_type="a")
    monkeypatch.setattr(main,"effective_presets",lambda db:[source])
    monkeypatch.setattr(main,"install_default_expressions",lambda *args:None)
    monkeypatch.setattr(main,"character_source_image",lambda *args:None)
    calls=[]
    def unavailable(data,*args,**kwargs):
        calls.append(data)
        raise HTTPException(503,"Moderator unavailable")
    monkeypatch.setattr(main,"enforce_character_policy",unavailable)
    with sessionmaker(engine,expire_on_commit=False)() as db:
        db.add(User(id="visitor"));db.commit()
        payload=source.model_dump();payload["description"]="Untrusted client changes"
        saved=main.create_character(payload,BackgroundTasks(),db,"visitor")
        assert saved.description==source.description and saved.name=="Canonical"
        assert calls==[]
        assert main.create_character(source.model_dump(),BackgroundTasks(),db,"visitor").id==saved.id
        with pytest.raises(HTTPException) as unknown:
            main.create_character(CharacterSpec(id="fake",name="Fake",creation_type="preset",preset_type="missing").model_dump(),BackgroundTasks(),db,"visitor")
        assert unknown.value.status_code==400
        custom=CharacterSpec(id="custom",name="New custom",description="New user content")
        with pytest.raises(HTTPException) as blocked:
            main.create_character(custom.model_dump(),BackgroundTasks(),db,"visitor")
        assert blocked.value.status_code==503 and len(calls)==1
        assert db.get(Character,"custom") is None
    engine.dispose()


def test_public_clone_reuses_server_card_without_moderation(monkeypatch):
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    def unavailable(*args,**kwargs):
        pytest.fail("Public catalog clone must not call creation moderator")
    monkeypatch.setattr(main,"enforce_character_policy",unavailable)
    with sessionmaker(engine,expire_on_commit=False)() as db:
        db.add_all([User(id="owner"),User(id="visitor")])
        source=CharacterSpec(id="published",name="Published",description="Server content")
        db.add(Character(id=source.id,user_id="owner",name=source.name,spec=source.model_dump_json()))
        db.add(CharacterPublication(character_id=source.id,creator_user_id="owner",is_public=1))
        db.commit()
        clone=main.clone_public_character(source.id,db,"visitor")
        assert clone["name"]==source.name and clone["description"]==source.description
        assert db.get(Character,clone["id"]).user_id=="visitor"
        db.get(CharacterPublication,source.id).is_public=0;db.commit()
        with pytest.raises(HTTPException) as private:
            main.clone_public_character(source.id,db,"visitor")
        assert private.value.status_code==404
    engine.dispose()
