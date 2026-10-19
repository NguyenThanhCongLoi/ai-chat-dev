"""Ordinary chat social actions; clients never submit state or numeric deltas."""
from .. import character_social as social
from ..models import CharacterSocialState as Edge, Room,RoomMember,Message
from ..group_routing import mentioned_characters

def bind(runtime):
    app=runtime.app
    def check_body(data,allowed):
        if not isinstance(data,dict) or set(data)-set(allowed):raise runtime.HTTPException(422,"Unexpected fields")
    def actor(db,user,ident):
        try:return social.owned(db,user,ident)
        except ValueError:raise runtime.HTTPException(404,"Character not found") from None
    def read(db,user,ident):
        row=db.get(Edge,ident)
        if not row or row.user_id!=user or row.scope!=social.SCOPE:raise runtime.HTTPException(404,"Connection not found")
        actor(db,user,row.character_a_id);actor(db,user,row.character_b_id)
        return row
    def detail(db,row):
        value=social.projection(db,row)
        reverse=social.edge(db,row.user_id,row.character_b_id,row.character_a_id)
        value["reverse"]=social.projection(db,reverse) if reverse else None
        return value

    @app.get("/v1/roleplay/characters/{character_id}/connections")
    def connections(character_id:str,db=runtime.Depends(runtime.db_session),user:str=runtime.Depends(runtime.current_user)):
        actor(db,user,character_id)
        rows=db.query(Edge).filter_by(user_id=user,scope=social.SCOPE,character_a_id=character_id).order_by(Edge.updated_at.desc()).limit(100).all()
        return [detail(db,r) for r in rows if db.get(runtime.Character,r.character_b_id)]

    @app.post("/v1/roleplay/characters/{character_id}/connections")
    def connect(character_id:str,data:dict,db=runtime.Depends(runtime.db_session),user:str=runtime.Depends(runtime.current_user)):
        check_body(data,("other_character_id","mutual"))
        other=data.get("other_character_id")
        if not isinstance(other,str) or other==character_id or type(data.get("mutual",True)) is not bool:raise runtime.HTTPException(422,"Choose another character")
        actor(db,user,character_id);actor(db,user,other)
        row=social.introduce(db,user,character_id,other,data.get("mutual",True))
        db.commit();return detail(db,row)

    @app.get("/v1/roleplay/characters/{character_id}/connection-suggestion")
    def suggestion(character_id:str,room_id:str,message_id:str,db=runtime.Depends(runtime.db_session),user:str=runtime.Depends(runtime.current_user)):
        actor(db,user,character_id);room=db.get(Room,room_id);message=db.get(Message,message_id)
        members=db.query(RoomMember).filter_by(room_id=room_id).all()
        if not room or room.user_id!=user or len(members)!=1 or members[0].character_id!=character_id or not message or message.room_id!=room_id or message.sender_type!="user":
            raise runtime.HTTPException(404,"Source unavailable")
        candidates=[runtime.spec(c) for c in db.query(runtime.Character).filter(runtime.Character.user_id==user,runtime.Character.id!=character_id).all()]
        found=mentioned_characters(message.text,candidates)
        if len(found)!=1 or social.edge(db,user,character_id,found[0].id):return {"candidate":None}
        return {"candidate":social.snapshot(actor(db,user,found[0].id)),"source_message_id":message.id}

    @app.get("/v1/roleplay/character-connections/{connection_id}")
    def get_connection(connection_id:str,db=runtime.Depends(runtime.db_session),user:str=runtime.Depends(runtime.current_user)):
        return detail(db,read(db,user,connection_id))

    @app.post("/v1/roleplay/character-connections/{connection_id}/introduce")
    def reintroduce(connection_id:str,db=runtime.Depends(runtime.db_session),user:str=runtime.Depends(runtime.current_user)):
        old=read(db,user,connection_id)
        row=social.introduce(db,user,old.character_a_id,old.character_b_id,True)
        db.commit();return detail(db,row)

    @app.delete("/v1/roleplay/character-connections/{connection_id}")
    def disconnect(connection_id:str,db=runtime.Depends(runtime.db_session),user:str=runtime.Depends(runtime.current_user)):
        row=read(db,user,connection_id)
        for a,b in ((row.character_a_id,row.character_b_id),(row.character_b_id,row.character_a_id)):
            found=social.edge(db,user,a,b)
            if found:found.active=0;found.updated_at=runtime.now()
        db.commit();return detail(db,row)

    @app.post("/v1/roleplay/character-connections/{connection_id}/shared-interaction")
    def shared(connection_id:str,data:dict,db=runtime.Depends(runtime.db_session),user:str=runtime.Depends(runtime.current_user)):
        check_body(data,("room_id","source_message_id"))
        row=read(db,user,connection_id);room_id=data.get("room_id");source_id=data.get("source_message_id")
        if not isinstance(room_id,str) or not isinstance(source_id,str):raise runtime.HTTPException(422,"Source IDs required")
        members={m.character_id for m in db.query(RoomMember).filter_by(room_id=room_id)}
        room=db.get(Room,room_id)
        if not room or room.user_id!=user or not {row.character_a_id,row.character_b_id}<=members:raise runtime.HTTPException(404,"Shared source not found")
        social.record_turn(db,user,room_id,source_id);db.commit();return detail(db,row)
