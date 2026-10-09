"""Conversation snapshots retained independently of user-visible chats."""
import hashlib
import json
from .models import AIRequestLog, Character, CharacterAsset, Message, MessageSuggestion, Room, RoomMember, UserAccount
from .schemas import uid


def character_avatar_metadata_url(db, character_id):
    # Fetch only a tiny version stamp, never the image BLOB on chat/log paths.
    metadata=db.query(CharacterAsset.updated_at).filter_by(character_id=character_id).first()
    if metadata is None:return None
    version=hashlib.sha256(str(metadata[0]).encode()).hexdigest()[:12]
    return f"/v1/public/characters/{character_id}/avatar?v={version}"


def capture_log_conversation(db, log, character_id=None):
    if log.conversation_snapshot:
        return
    room = db.get(Room, log.room_id)
    question = db.get(Message, log.user_message_id) if log.user_message_id else None
    response = db.get(Message, log.response_message_id) if log.response_message_id else None
    account = db.get(UserAccount, log.user_id)
    name = (account.display_name or account.username) if account else log.user_id
    mode = room.name.split(":", 2)[1] if log.product=="assistant" and room and room.name.startswith("assistant:") else ""
    character_id = (response.character_id if response else None) or character_id or ""
    if not character_id and room and not mode:
        members = db.query(RoomMember).filter_by(room_id=room.id).all()
        # Without a response or explicit speaker, a group request has no known speaker.
        character_id = members[0].character_id if len(members)==1 else ""
    character = db.get(Character, character_id) if character_id else None
    character_name, avatar = "", ""
    if character:
        character_name = character.name
        try:
            card = json.loads(character.spec)
            character_name = card.get("display_name") or character.name
            avatar = card.get("avatar_url") or ""
        except (ValueError, TypeError):
            pass
        avatar = character_avatar_metadata_url(db,character.id) or avatar
    members=db.query(RoomMember).filter_by(room_id=log.room_id).all() if room and not mode else []
    room_characters=[{"id":member.character_id,"name":item.name if (item:=db.get(Character,member.character_id)) else member.character_id} for member in members]
    log.conversation_snapshot = json.dumps({
        "user": name, "room": room.name if room else log.room_id,
        "room_id":log.room_id,"user_message_id":log.user_message_id,
        "response_message_id":log.response_message_id,
        "room_type":"group" if len(members)>1 else ("assistant" if mode else "single"),
        "room_characters":room_characters,
        "user_message": question.text if question else "",
        "assistant_mode": mode, "character_id": character_id,
        "character_name": character_name, "character_avatar_url": avatar,
    }, ensure_ascii=False)
    if not log.output_text and response:
        if log.task == "suggestion":
            log.output_text = " | ".join(row.text for row in db.query(MessageSuggestion).filter_by(message_id=response.id).all())
        else:
            log.output_text = response.text


def archive_chat_before_delete(db, room_id, message_ids=None):
    """Capture existing logs and materialize legacy CMS rows in the same delete transaction."""
    room = db.get(Room, room_id)
    if not room:
        return
    for log in db.query(AIRequestLog).filter_by(room_id=room_id).all():
        capture_log_conversation(db, log)
    responses = db.query(Message).filter(Message.room_id == room_id, Message.sender_type.in_(("assistant", "character")))
    if message_ids is not None:
        responses = responses.filter(Message.id.in_(message_ids))
    for response in responses.order_by(Message.created_at, Message.id).all():
        if db.query(AIRequestLog.id).filter_by(response_message_id=response.id).first():
            continue
        question = db.query(Message).filter(
            Message.room_id == room_id, Message.sender_type == "user",
            Message.created_at <= response.created_at,
        ).order_by(Message.created_at.desc(), Message.id.desc()).first()
        log = AIRequestLog(
            id=uid(), user_id=room.user_id, room_id=room_id,
            user_message_id=question.id if question else None, response_message_id=response.id,
            product="assistant" if room.name.startswith("assistant:") else "roleplay",
            task="response", output_text=response.text, created_at=response.created_at,
            archive_source="legacy",
        )
        db.add(log)
        capture_log_conversation(db, log)
