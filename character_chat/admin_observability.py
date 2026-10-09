"""Read-only CMS views: conversation, voice, activity and database logs."""
import json
import csv
import io
import heapq
from itertools import islice
from datetime import date, datetime, timedelta, timezone
from fastapi.responses import StreamingResponse
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session as DBSession
from .db import (
    AIRequestLog, AuditEvent, Character, CharacterAsset, Message, Room, RoomMember, UserAccount, VoiceEvent,
)


def build_admin_observability_router(docs_auth, db_session, admin_tables,
                                     assistant_room_prefix, suggestion_values, character_spec):
    router = APIRouter()
    ADMIN_TABLES = admin_tables
    ASSISTANT_ROOM_PREFIX = assistant_room_prefix

    @router.get("/v1/admin/database")
    def admin_database_tables(_:None=Depends(docs_auth),db:DBSession=Depends(db_session)):
        return [{"name":name,"rows":db.query(model).count(),"columns":[column.name for column in model.__table__.columns]} for name,model in ADMIN_TABLES.items()]

    @router.get("/v1/admin/conversations")
    def admin_conversations(product:str="all",q:str="",limit:int=100,_:None=Depends(docs_auth),db:DBSession=Depends(db_session)):
        """Readable conversation index for CMS; production chat remains in the database."""
        stats=(db.query(Message.room_id,func.count(Message.id).label("message_count"),func.max(Message.created_at).label("last_at"))
            .group_by(Message.room_id).subquery())
        query=(db.query(Room,UserAccount,stats.c.message_count,stats.c.last_at)
            .outerjoin(UserAccount,UserAccount.user_id==Room.user_id)
            .outerjoin(stats,stats.c.room_id==Room.id)
            .filter(func.coalesce(stats.c.message_count,0)>0))
        if product=="assistant":query=query.filter(Room.name.like(ASSISTANT_ROOM_PREFIX+"%"))
        elif product=="roleplay":query=query.filter(~Room.name.like(ASSISTANT_ROOM_PREFIX+"%"))
        term=q.strip()[:100]
        if term:
            pattern=f"%{term}%"
            query=query.filter(or_(Room.name.ilike(pattern),Room.user_id.ilike(pattern),UserAccount.username.ilike(pattern),UserAccount.display_name.ilike(pattern)))
        rows=query.order_by(stats.c.last_at.desc()).limit(max(1,min(limit,200))).all()
        result=[]
        for room,account,message_count,last_at in rows:
            last=db.query(Message).filter_by(room_id=room.id).order_by(Message.created_at.desc()).first()
            mode=room.name.split(":",2)[1] if room.name.startswith(ASSISTANT_ROOM_PREFIX) and len(room.name.split(":",2))>1 else "roleplay"
            result.append({"id":room.id,"product":"assistant" if mode!="roleplay" else "roleplay","mode":mode,"title":room.name.split(":",2)[-1] if mode!="roleplay" else room.name,"user_id":room.user_id,"username":account.username if account else "","display_name":account.display_name if account else "","message_count":int(message_count or 0),"last_at":last_at or room.created_at,"preview":(last.text[:180] if last else "")})
        return result

    @router.get("/v1/admin/action-logs")
    def admin_action_logs(category:str="all",status_filter:str="all",q:str="",limit:int=500,_:None=Depends(docs_auth),db:DBSession=Depends(db_session)):
        limit=max(1,min(limit,1000));query=db.query(AuditEvent)
        if category!="all":query=query.filter(AuditEvent.category==category)
        if status_filter!="all":query=query.filter(AuditEvent.status==status_filter)
        term=q.strip()[:120]
        if term:
            pattern=f"%{term}%"
            query=query.filter(or_(AuditEvent.username.ilike(pattern),AuditEvent.user_id.ilike(pattern),AuditEvent.action.ilike(pattern),AuditEvent.path.ilike(pattern),AuditEvent.error.ilike(pattern)))
        items=query.order_by(AuditEvent.created_at.desc()).limit(limit).all()
        columns=["created_at","status","status_code","category","action","username","user_id","method","path","latency_ms","ip_address","user_agent","error","details"]
        rows=[{column:getattr(item,column) for column in columns} for item in items]
        return {"total":len(rows),"columns":columns,"rows":rows}

    @router.get("/v1/admin/voice-logs")
    def admin_voice_logs(event_type:str="all",status_filter:str="all",q:str="",limit:int=300,_:None=Depends(docs_auth),db:DBSession=Depends(db_session)):
        limit=max(1,min(limit,1000))
        query=db.query(VoiceEvent)
        if event_type in ("generation","listen"):query=query.filter(VoiceEvent.event_type==event_type)
        if status_filter in ("success","error","started"):query=query.filter(VoiceEvent.status==status_filter)
        term=q.strip()[:100]
        if term:
            pattern=f"%{term}%"
            query=query.filter(or_(VoiceEvent.user_id.ilike(pattern),VoiceEvent.character_id.ilike(pattern),VoiceEvent.message_id.ilike(pattern),VoiceEvent.model_id.ilike(pattern),VoiceEvent.voice_id.ilike(pattern),VoiceEvent.error.ilike(pattern)))
        events=query.order_by(VoiceEvent.created_at.desc(),VoiceEvent.id.desc()).limit(limit).all()
        accounts={item.user_id:item.username for item in db.query(UserAccount).filter(UserAccount.user_id.in_({row.user_id for row in events})).all()} if events else {}
        characters={item.id:item.name for item in db.query(Character).filter(Character.id.in_({row.character_id for row in events})).all()} if events else {}
        columns=["created_at","event_type","status","user","character","model_id","voice_id","latency_ms","audio_bytes","automatic","message_id","error"]
        rows=[{"created_at":item.created_at,"event_type":item.event_type,"status":item.status,"user":accounts.get(item.user_id,item.user_id),"character":characters.get(item.character_id,item.character_id),"model_id":item.model_id,"voice_id":item.voice_id,"latency_ms":item.latency_ms,"audio_bytes":item.audio_bytes,"automatic":"Có" if item.automatic else "Không","message_id":item.message_id,"error":item.error} for item in events]
        return {"total":len(rows),"columns":columns,"rows":rows}

    @router.get("/v1/admin/chat-log-gateways")
    def admin_chat_log_gateways(product:str="all",_:None=Depends(docs_auth),db:DBSession=Depends(db_session)):
        query=db.query(AIRequestLog.actual_api_base,AIRequestLog.primary_api_base)
        if product!="all":query=query.filter(AIRequestLog.product==product)
        return sorted({actual or primary for actual,primary in query.distinct().all() if actual or primary})

    def collect_chat_logs(db,product="all",q="",gateway="",limit=300,offset=0,export_all=False,start_at=None,end_at=None,max_rows=None):
        """One flat, readable table containing user input, product output and inference metadata."""
        limit=max(1,min(limit,1000));term=q.strip().casefold()[:100]
        rows=[]
        def identity(room):
            account=db.get(UserAccount,room.user_id) if room else None
            return (account.display_name or account.username) if account else (room.user_id if room else "")
        speakers={}
        def speaker(room,response):
            if room and room.name.startswith(ASSISTANT_ROOM_PREFIX):
                parts=room.name.split(":",2)
                return {"assistant_mode":parts[1] if len(parts)>1 else "assistant_general","character_id":"","character_name":"","character_avatar_url":""}
            character_id=(response.character_id if response else None) or ""
            if not character_id and room:
                member=db.query(RoomMember).filter_by(room_id=room.id).first()
                character_id=member.character_id if member else ""
            if character_id not in speakers:
                character=db.get(Character,character_id) if character_id else None
                name,avatar="",""
                if character:
                    try:
                        card=character_spec(character)
                        name=card.display_name or character.name
                        avatar=card.avatar_url or ""
                    except Exception:
                        name=character.name
                    asset=db.get(CharacterAsset,character.id)
                    if asset:
                        avatar=f"/v1/public/characters/{character.id}/avatar?v={hashlib.sha256(asset.content).hexdigest()[:12]}"
                speakers[character_id]={"assistant_mode":"","character_id":character_id,"character_name":name,"character_avatar_url":avatar}
            return speakers[character_id]
        def structured_row(log):
            room=db.get(Room,log.room_id);user_message=db.get(Message,log.user_message_id) if log.user_message_id else None
            response=db.get(Message,log.response_message_id) if log.response_message_id else None
            output=log.output_text or ((" | ".join(suggestion_values(db,response.id))) if log.task=="suggestion" and response else (response.text if response else ""))
            data={"created_at":log.created_at,"log_status":"Đã ghi đầy đủ"+(" · request lỗi" if log.error else ""),"user":identity(room),"user_id":log.user_id,"product":log.product,"task":log.task,"room_id":log.room_id,"user_message_id":log.user_message_id,"response_message_id":log.response_message_id,"room":room.name if room else log.room_id,**speaker(room,response),"user_message":user_message.text if user_message else "","model_response":output,"primary_model_config_id":log.primary_model_config_id,"primary_model_name":log.primary_model_name,"primary_api_base":log.primary_api_base,"actual_model_config_id":log.actual_model_config_id,"actual_model_name":log.actual_model_name,"actual_api_base":log.actual_api_base,"gateway_snapshot_source":log.gateway_snapshot_source or "unknown","primary_model":log.primary_model or "Không phân công","fallback_model":log.fallback_model or "Không phân công","fallback_model_2":log.fallback_model_2 or "Không phân công","fallback_used":"Có" if log.fallback_used else "Không","fallback_reason":log.fallback_reason,"actual_model":log.actual_model or log.primary_model,"thinking_mode":log.thinking_mode,"reasoning_effort":log.reasoning_effort,"continuation_count":log.continuation_count,"finish_status":log.finish_status,"client_suggestion_ms":log.client_suggestion_ms,"client_first_chunk_ms":log.client_first_chunk_ms,"server_prepare_ms":log.server_prepare_ms,"gateway_headers_ms":log.gateway_headers_ms,"gateway_first_chunk_ms":log.gateway_first_chunk_ms,"latency_ms":log.latency_ms,"error":log.error}
            try:snapshot=json.loads(log.conversation_snapshot or "{}")
            except (ValueError,TypeError):snapshot={}
            if isinstance(snapshot,dict):
                for field in ("user","room","room_id","room_type","room_characters","user_message_id","response_message_id","user_message","assistant_mode","character_id","character_name","character_avatar_url"):
                    if field in snapshot:data[field]=snapshot[field]
            if not data["user"]:
                account=db.get(UserAccount,log.user_id)
                data["user"]=(account.display_name or account.username) if account else log.user_id
            if log.archive_source=="legacy":data["log_status"]="Log cũ · chưa ghi metadata"
            return data
        def legacy_row(response,room):
            user_message=db.query(Message).filter(Message.room_id==room.id,Message.sender_type=="user",Message.created_at<=response.created_at).order_by(Message.created_at.desc(),Message.id.desc()).first()
            row_product="assistant" if room.name.startswith(ASSISTANT_ROOM_PREFIX) else "roleplay"
            data={"created_at":response.created_at,"log_status":"Log cũ · chưa ghi metadata","user":identity(room),"user_id":room.user_id,"product":row_product,"task":"response","room_id":room.id,"user_message_id":user_message.id if user_message else None,"response_message_id":response.id,"room":room.name,**speaker(room,response),"user_message":user_message.text if user_message else "","model_response":response.text,"primary_model_config_id":"","primary_model_name":"","primary_api_base":"","actual_model_config_id":"","actual_model_name":"","actual_api_base":"","gateway_snapshot_source":"unknown","primary_model":"Chưa ghi nhận","fallback_model":"Chưa ghi nhận","fallback_model_2":"Chưa ghi nhận","fallback_used":"Chưa ghi nhận","fallback_reason":"Chưa ghi nhận","actual_model":"Chưa ghi nhận","thinking_mode":"Chưa ghi nhận","reasoning_effort":"Chưa ghi nhận","continuation_count":"Chưa ghi nhận","finish_status":"Chưa ghi nhận","latency_ms":"Chưa ghi nhận","error":""}
            return data
        offset=max(0,offset)
        query=db.query(AIRequestLog)
        if product!="all":query=query.filter(AIRequestLog.product==product)
        used_base=func.coalesce(func.nullif(AIRequestLog.actual_api_base,""),AIRequestLog.primary_api_base)
        if gateway=="__unknown__":query=query.filter(or_(used_base=="",used_base.is_(None)))
        elif gateway:query=query.filter(used_base==gateway[:500])
        query=query.order_by(AIRequestLog.created_at.desc(),AIRequestLog.id.desc())
        columns=["created_at","log_status","user","user_id","product","task","room","room_id","room_type","room_characters","user_message_id","response_message_id","assistant_mode","character_id","character_name","character_avatar_url","user_message","model_response","primary_model","primary_model_config_id","primary_model_name","primary_api_base","fallback_model","fallback_model_2","fallback_used","fallback_reason","actual_model","actual_model_config_id","actual_model_name","actual_api_base","gateway_snapshot_source","thinking_mode","reasoning_effort","continuation_count","finish_status","client_suggestion_ms","client_first_chunk_ms","server_prepare_ms","gateway_headers_ms","gateway_first_chunk_ms","latency_ms","error"]
        if export_all:
            def stamp(row):
                try:
                    value=datetime.fromisoformat(str(row.get("created_at") or "").replace("Z","+00:00"))
                    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
                except (ValueError,TypeError):return datetime.min.replace(tzinfo=timezone.utc)
            def matches(data):
                value=stamp(data)
                return (start_at is None or value>=start_at) and (end_at is None or value<end_at) and (
                    not term or term in " ".join(str(value) for value in data.values()).casefold())
            def structured_rows():
                for log in query.yield_per(250):
                    data=structured_row(log)
                    if matches(data):yield data
            def legacy_rows():
                if gateway and gateway!="__unknown__":return
                responses=db.query(Message).filter(
                    Message.sender_type.in_(("assistant","character")),
                    ~db.query(AIRequestLog.id).filter(AIRequestLog.response_message_id==Message.id).exists(),
                ).order_by(Message.created_at.desc(),Message.id.desc())
                for response in responses.yield_per(250):
                    room=db.get(Room,response.room_id)
                    if not room:continue
                    data=legacy_row(response,room)
                    if product!="all" and data["product"]!=product:continue
                    if matches(data):yield data
            # Select the newest matching rows across structured and legacy logs.
            ordered=heapq.merge(structured_rows(),legacy_rows(),key=stamp,reverse=True)
            return {"columns":columns,"rows":islice(ordered,max_rows) if max_rows is not None else ordered}
        structured_count=0
        if term:
            # Search the archive, including records older than the first page.
            for log in query:
                data=structured_row(log)
                if term not in " ".join(str(value) for value in data.values()).casefold():continue
                if structured_count>=offset and len(rows)<limit+1:rows.append(data)
                structured_count+=1
                if len(rows)>=limit+1:break
        else:
            structured_count=query.order_by(None).count()
            rows.extend(structured_row(log) for log in query.offset(offset).limit(limit+1).all())
        if len(rows)<limit+1 and (not gateway or gateway=="__unknown__"):
            legacy_skip=max(0,offset-structured_count)
            legacy_seen=0
            responses=db.query(Message).filter(
                Message.sender_type.in_(("assistant","character")),
                ~db.query(AIRequestLog.id).filter(AIRequestLog.response_message_id==Message.id).exists(),
            ).order_by(Message.created_at.desc(),Message.id.desc())
            for response in responses.yield_per(100):
                room=db.get(Room,response.room_id)
                if not room:continue
                data=legacy_row(response,room)
                if product!="all" and data["product"]!=product:continue
                if term and term not in " ".join(str(value) for value in data.values()).casefold():continue
                if legacy_seen<legacy_skip:legacy_seen+=1;continue
                rows.append(data)
                if len(rows)>=limit+1:break
        has_more=len(rows)>limit
        return {"total":max(structured_count,offset+len(rows)),"offset":offset,"has_more":has_more,"columns":columns,"rows":rows[:limit]}

    @router.get("/v1/admin/chat-logs")
    def admin_chat_logs(product:str="all",q:str="",gateway:str="",limit:int=300,offset:int=0,_:None=Depends(docs_auth),db:DBSession=Depends(db_session)):
        return collect_chat_logs(db,product,q,gateway,limit,offset)

    @router.get("/v1/admin/chat-logs.csv")
    def export_chat_logs_csv(product:str="all",q:str="",gateway:str="",start_date:date|None=None,end_date:date|None=None,max_rows:int|None=Query(None,ge=1),_:None=Depends(docs_auth),db:DBSession=Depends(db_session)):
        bind=db.get_bind()
        vietnam=timezone(timedelta(hours=7))
        if start_date and end_date and start_date>end_date:
            raise HTTPException(422,"Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")
        try:
            start_at=datetime.combine(start_date,datetime.min.time(),vietnam).astimezone(timezone.utc) if start_date else None
            end_at=datetime.combine(end_date+timedelta(days=1),datetime.min.time(),vietnam).astimezone(timezone.utc) if end_date else None
        except (ValueError,OverflowError):raise HTTPException(422,"Khoảng ngày không hợp lệ")
        def safe_cell(value):
            if value is None:return ""
            if not isinstance(value,str):return value
            # Treat user content as text, including spreadsheet formula prefixes.
            if value.lstrip().startswith(("=","+","-","@")) or value.startswith(("\t","\r","\n")):
                return "'"+value
            return value
        def body():
            # Own the session for the entire download, independent of dependency cleanup.
            with DBSession(bind=bind) as export_db:
                data=collect_chat_logs(export_db,product,q,gateway,export_all=True,start_at=start_at,end_at=end_at,max_rows=max_rows)
                output=io.StringIO(newline="");writer=csv.writer(output,quoting=csv.QUOTE_ALL)
                headers=["created_at_vn" if field=="created_at" else "runtime_ms" if field=="latency_ms" else field for field in data["columns"]]
                writer.writerow(headers)
                yield ("\ufeff"+output.getvalue()).encode("utf-8")
                for row in data["rows"]:
                    stamp=row.get("created_at") or ""
                    try:
                        parsed=datetime.fromisoformat(stamp.replace("Z","+00:00"))
                        if parsed.tzinfo is None:parsed=parsed.replace(tzinfo=timezone.utc)
                        row["created_at"]=parsed.astimezone(vietnam).isoformat()
                    except (ValueError,TypeError):pass
                    output.seek(0);output.truncate(0)
                    writer.writerow([safe_cell(row.get(field)) for field in data["columns"]])
                    yield output.getvalue().encode("utf-8")
        filename="logchat_"+datetime.now(vietnam).strftime("%Y%m%d_%H%M%S")+".csv"
        return StreamingResponse(body(),media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition":f'attachment; filename="{filename}"',"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})

    @router.get("/v1/admin/conversations/{room_id}")
    def admin_conversation(room_id:str,_:None=Depends(docs_auth),db:DBSession=Depends(db_session)):
        room=db.get(Room,room_id)
        if not room:raise HTTPException(404,"Conversation not found")
        account=db.get(UserAccount,room.user_id);characters={row.id:row.name for row in db.query(Character).all()}
        messages=db.query(Message).filter_by(room_id=room.id).order_by(Message.created_at.asc()).limit(2000).all()
        return {"id":room.id,"name":room.name,"user":{"id":room.user_id,"username":account.username if account else "","display_name":account.display_name if account else ""},"product":"assistant" if room.name.startswith(ASSISTANT_ROOM_PREFIX) else "roleplay","messages":[{"id":item.id,"sender_type":item.sender_type,"sender_name":"Người dùng" if item.sender_type=="user" else characters.get(item.character_id,"AI Assistant"),"character_id":item.character_id,"text":item.text,"emotion":item.emotion,"created_at":item.created_at} for item in messages]}

    @router.get("/v1/admin/database/{table_name}")
    def admin_database_rows(table_name:str,limit:int=50,offset:int=0,user_id:str|None=None,_:None=Depends(docs_auth),db:DBSession=Depends(db_session)):
        model=ADMIN_TABLES.get(table_name)
        if not model:raise HTTPException(404,"Table is not available in CMS")
        limit=max(1,min(limit,200));offset=max(0,offset);query=db.query(model)
        if user_id and hasattr(model,"user_id"):query=query.filter(getattr(model,"user_id")==user_id)
        order=getattr(model,"created_at",None) or getattr(model,"updated_at",None)
        if order is not None:query=query.order_by(order.desc())
        total=query.count();rows=query.offset(offset).limit(limit).all();columns=[column.name for column in model.__table__.columns]
        def serialize(row):
            result={}
            for column in columns:
                value=getattr(row,column)
                if column in ("password_hash","token_hash","api_key_encrypted"):value="[REDACTED]"
                elif table_name=="app_settings" and column=="value" and str(getattr(row,"key","")).startswith(("credential:","credential_hint:","credential_base_meta:")):value="[REDACTED]"
                elif isinstance(value,(bytes,bytearray)):value=f"[BINARY {len(value)} bytes]"
                if isinstance(value,str) and len(value)>500:value=value[:500]+"…"
                result[column]=value
            return result
        return {"table":table_name,"total":total,"limit":limit,"offset":offset,"columns":columns,"rows":[serialize(row) for row in rows]}

    return router, (admin_database_tables, admin_conversations, admin_action_logs, admin_voice_logs, admin_chat_logs, admin_conversation, admin_database_rows)
