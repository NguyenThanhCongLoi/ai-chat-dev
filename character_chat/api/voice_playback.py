"""api.voice_playback: domain-specific application implementation.

Listen, streaming audio and timing endpoints; provider/cache logic is in services/speech.py.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_roleplay_message_speech_stream(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.post("/v1/roleplay/messages/{message_id}/speech/stream")
    async def roleplay_message_speech_stream(
        message_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        return await runtime._roleplay_speech_stream(message_id, db, user)

    runtime.roleplay_message_speech_stream = roleplay_message_speech_stream


def bind_roleplay_message_speech(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.post("/v1/roleplay/messages/{message_id}/speech")
    async def roleplay_message_speech(
        message_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        message = db.get(runtime.Message, message_id)
        if (
            not message
            or message.sender_type != "character"
            or not message.character_id
        ):
            raise runtime.HTTPException(404, "Không tìm thấy câu trả lời")
        room = db.get(runtime.Room, message.room_id)
        character = db.get(runtime.Character, message.character_id)
        if (
            not room
            or room.user_id != user
            or not character
            or character.user_id != user
        ):
            raise runtime.HTTPException(404, "Không tìm thấy câu trả lời")
        speech_text = runtime.speech_message_text(db, message, character)
        runtime.require_supported_voice_language(
            db,
            user,
            speech_text,
            runtime.message_speech_segments(message, speech_text, db, character),
            runtime.spec(character),
        )
        content, mime_type = await runtime.prepare_message_speech(
            db, message, character
        )
        return runtime.Response(
            content=content,
            media_type=mime_type,
            headers={"Cache-Control": "private, no-store"},
        )

    runtime.roleplay_message_speech = roleplay_message_speech

    @runtime.app.post("/v1/messages/{message_id}/timing")
    def record_message_timing(
        message_id: str,
        data: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        fields = {
            field: data[field]
            for field in ("client_first_chunk_ms", "client_suggestion_ms")
            if field in data
        }
        if not fields:
            raise runtime.HTTPException(422, "At least one timing field is required")
        for field, value in fields.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 3600000
            ):
                raise runtime.HTTPException(
                    422, field + " must be an integer between 0 and 3600000"
                )
        message = db.get(runtime.Message, message_id)
        room = db.get(runtime.Room, message.room_id) if message else None
        if (
            not room
            or room.user_id != user
            or message.sender_type not in ("assistant", "character")
        ):
            raise runtime.HTTPException(404, "Reply not found")
        for field, value in fields.items():
            query = db.query(runtime.AIRequestLog).filter(
                runtime.AIRequestLog.response_message_id == message_id,
                runtime.AIRequestLog.user_id == user,
                getattr(runtime.AIRequestLog, field).is_(None),
            )
            query = (
                query.filter(runtime.AIRequestLog.task == "suggestion")
                if field == "client_suggestion_ms"
                else query.filter(
                    runtime.AIRequestLog.task.notin_(("suggestion", "regenerate"))
                )
            )
            query.update({field: value}, synchronize_session=False)
        db.commit()
        return {"ok": True}

    runtime.record_message_timing = record_message_timing

    @runtime.app.post("/v1/roleplay/messages/{message_id}/listen")
    def roleplay_message_listen(
        message_id: str,
        data: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        message = db.get(runtime.Message, message_id)
        if (
            not message
            or message.sender_type != "character"
            or not message.character_id
        ):
            raise runtime.HTTPException(404, "Không tìm thấy câu trả lời")
        room = db.get(runtime.Room, message.room_id)
        character = db.get(runtime.Character, message.character_id)
        if (
            not room
            or room.user_id != user
            or not character
            or character.user_id != user
        ):
            raise runtime.HTTPException(404, "Không tìm thấy câu trả lời")
        cached = db.get(runtime.MessageSpeech, message_id)
        try:
            latency_ms = max(0, min(int(data.get("latency_ms", 0)), 120000))
        except (TypeError, ValueError):
            latency_ms = 0
        db.add(
            runtime.VoiceEvent(
                id=runtime.uid(),
                message_id=message.id,
                character_id=character.id,
                user_id=user,
                event_type="listen",
                status="started",
                latency_ms=latency_ms,
                audio_bytes=len(cached.content) if cached and cached.content else 0,
                automatic=int(bool(data.get("automatic"))),
            )
        )
        db.commit()
        return {"ok": True}

    runtime.roleplay_message_listen = roleplay_message_listen
