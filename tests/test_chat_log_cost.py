import json
from sqlalchemy import create_engine,event
from sqlalchemy.orm import sessionmaker
from character_chat.models import Base,User,Character,CharacterAsset,Room,RoomMember,Message,AIRequestLog
from character_chat.schemas import CharacterSpec
from character_chat.log_archive import capture_log_conversation
from character_chat import main

def test_log_snapshot_does_not_select_avatar_blob():
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    statements=[]
    with sessionmaker(engine)() as db:
        card=CharacterSpec(id="c",name="Character")
        db.add_all([User(id="u"),Character(id="c",user_id="u",name=card.name,spec=card.model_dump_json()),
          CharacterAsset(character_id="c",mime_type="image/png",content=b"large-image"*100000),
          Room(id="r",user_id="u",name="Group"),RoomMember(id="member",room_id="r",character_id="c"),
          Message(id="q",room_id="r",sender_type="user",text="Hello"),
          Message(id="a",room_id="r",sender_type="character",character_id="c",text="Reply")])
        db.commit()
        event.listen(engine,"before_cursor_execute",lambda conn,cursor,statement,*args:statements.append(statement))
        log=AIRequestLog(id="log",user_id="u",room_id="r",user_message_id="q",response_message_id="a",product="roleplay",task="response")
        capture_log_conversation(db,log)
        snapshot=json.loads(log.conversation_snapshot)
        assert snapshot["character_id"]=="c"
        assert snapshot["character_avatar_url"].startswith("/v1/public/characters/c/avatar?v=")
        asset_queries=[sql for sql in statements if "character_assets" in sql and sql.lstrip().upper().startswith("SELECT")]
        assert asset_queries and all("character_assets.content" not in sql for sql in asset_queries)
    engine.dispose()

def test_unchanged_catalog_read_does_not_update_preset(monkeypatch):
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    source=CharacterSpec(id="preset-c",name="System",creation_type="preset",preset_type="test")
    saved=source.model_copy(deep=True);saved.id="owned-c"
    monkeypatch.setattr(main,"effective_presets",lambda db:[source])
    monkeypatch.setattr(main,"character_out",lambda row,db:main.spec(row).model_dump())
    with sessionmaker(engine)() as db:
        db.add(User(id="u"));db.add(Character(id=saved.id,user_id="u",name=saved.name,spec=saved.model_dump_json(),updated_at="original"))
        db.commit()
        updates=[]
        event.listen(engine,"before_cursor_execute",lambda conn,cursor,sql,*args:updates.append(sql) if sql.lstrip().upper().startswith("UPDATE") else None)
        main.characters(db,"u");main.characters(db,"u")
        assert db.get(Character,saved.id).updated_at=="original"
        assert updates==[]
        changed=source.model_copy(deep=True);changed.description="Updated system description"
        monkeypatch.setattr(main,"effective_presets",lambda db:[changed])
        main.characters(db,"u")
        assert main.spec(db.get(Character,saved.id)).description==changed.description
        assert len(updates)==1
    engine.dispose()


def test_cms_legacy_logs_exclude_archived_messages_in_sql():
    from character_chat.admin_observability import build_admin_observability_router
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    router,_=build_admin_observability_router(lambda:None,lambda:None,{}, "assistant:",lambda *args:[],main.spec)
    endpoint=next(route.endpoint for route in router.routes if route.path=="/v1/admin/chat-logs")
    with sessionmaker(engine)() as db:
        db.add_all([User(id="u"),Room(id="r",user_id="u",name="assistant:general:Test"),
            Message(id="q",room_id="r",sender_type="user",text="Hello"),
            Message(id="archived",room_id="r",sender_type="assistant",text="Saved reply"),
            Message(id="legacy",room_id="r",sender_type="assistant",text="Legacy reply"),
            AIRequestLog(id="log",user_id="u",room_id="r",user_message_id="q",
                response_message_id="archived",product="assistant",task="response")])
        db.commit()
        statements=[]
        event.listen(engine,"before_cursor_execute",lambda conn,cursor,sql,*args:statements.append(sql))
        data=endpoint(product="all",q="",gateway="",limit=10,offset=0,_=None,db=db)
        assert len(data["rows"])==2
        assert sum(row["model_response"]=="Legacy reply" for row in data["rows"])==1
        assert any("NOT (EXISTS" in sql and "ai_request_logs.response_message_id = messages.id" in sql for sql in statements)
    engine.dispose()
