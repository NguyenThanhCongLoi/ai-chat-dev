"""api.rooms: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_public_rooms(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/v1/public/rooms")
    def public_rooms(
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        result = []
        for setting in db.query(runtime.AppSetting).filter(
            runtime.AppSetting.key.like("room_public:%"),
            runtime.AppSetting.value == "true",
        ):
            room = db.get(runtime.Room, setting.key.removeprefix("room_public:"))
            if room and runtime.public_room_members(db, room):
                result.append(
                    {
                        **runtime.room_out(db, room),
                        "characters": [
                            runtime.character_out(db.get(runtime.Character, id), db)
                            for id in runtime.room_out(db, room)["character_ids"]
                        ],
                    }
                )
        return sorted(result, key=lambda item: item["created_at"], reverse=True)

    runtime.public_rooms = public_rooms

    @runtime.app.post("/v1/public/rooms/{room_id}/start")
    def start_public_room(
        room_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        source = db.get(runtime.Room, room_id)
        if (
            not source
            or not runtime.room_is_public(db, room_id)
            or not runtime.public_room_members(db, source)
        ):
            raise runtime.HTTPException(404, "Room not found")
        if source.user_id == user:
            return runtime.room_out(db, source)
        key = "room_template_use:" + user + ":" + room_id
        previous = db.get(runtime.AppSetting, key)
        if previous:
            existing = db.get(runtime.Room, previous.value)
            if existing and existing.user_id == user:
                return runtime.room_out(db, existing)
        ids = []
        templates = runtime.effective_presets(db)
        for member in db.query(runtime.RoomMember).filter_by(room_id=room_id).all():
            source_character = db.get(runtime.Character, member.character_id)
            system_source = runtime.system_room_source(db, source_character, templates)
            if system_source:
                saved = runtime.create_character(
                    system_source.model_dump(), runtime.BackgroundTasks(), db, user
                )
                ids.append(saved.id)
            else:
                ids.append(
                    runtime.clone_public_character(member.character_id, db, user)["id"]
                )
        result = runtime.create_room(
            runtime.RoomIn(
                name=source.name,
                topic=runtime.room_topic(db, source.id),
                character_ids=ids,
            ),
            db,
            user,
        )
        if previous:
            previous.value = result["id"]
        else:
            db.add(runtime.AppSetting(key=key, value=result["id"]))
        db.commit()
        return result

    runtime.start_public_room = start_public_room

    @runtime.app.get("/v1/roleplay/favorites")
    def catalog_favorites(
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        row = db.get(runtime.AppSetting, "catalog_favorites:" + user)
        return {"keys": runtime.json.loads(row.value) if row else []}

    runtime.catalog_favorites = catalog_favorites

    @runtime.app.put("/v1/roleplay/favorites")
    def save_catalog_favorites(
        data: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        key = str(data.get("key", ""))
        if not key.startswith(("character:", "preset:")) or len(key) > 200:
            raise runtime.HTTPException(400, "Invalid favorite")
        row = db.get(runtime.AppSetting, "catalog_favorites:" + user)
        keys = set(runtime.json.loads(row.value) if row else [])
        if data.get("favorite"):
            keys.add(key)
        else:
            keys.discard(key)
        if len(keys) > 2000:
            raise runtime.HTTPException(400, "Too many favorites")
        value = runtime.json.dumps(sorted(keys))
        if row:
            row.value = value
        else:
            db.add(runtime.AppSetting(key="catalog_favorites:" + user, value=value))
        db.commit()
        return {"keys": sorted(keys)}

    runtime.save_catalog_favorites = save_catalog_favorites

    @runtime.app.post("/v1/rooms")
    def create_room(
        data: runtime.RoomIn,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        ids = list(dict.fromkeys(data.character_ids))
        if len(ids) != len(data.character_ids):
            raise runtime.HTTPException(400, "Duplicate character")
        members = [runtime.owned(db, runtime.Character, id, user) for id in ids]
        templates = runtime.effective_presets(db) if data.is_public else []
        if data.is_public and (
            len(ids) < 2
            or any(not runtime.room_member_shareable(db, c, templates) for c in members)
        ):
            raise runtime.HTTPException(
                400, "Cần công khai từng nhân vật trước khi công khai phòng chat."
            )
        if len(ids) == 1:
            candidates = (
                db.query(runtime.Room)
                .join(runtime.RoomMember, runtime.RoomMember.room_id == runtime.Room.id)
                .filter(
                    runtime.Room.user_id == user,
                    runtime.RoomMember.character_id == ids[0],
                )
                .order_by(runtime.Room.created_at.desc(), runtime.Room.id.desc())
                .all()
            )
            for existing in candidates:
                if (
                    db.query(runtime.RoomMember).filter_by(room_id=existing.id).count()
                    == 1
                ):
                    return {**runtime.room_out(db, existing), "created": False}
        room = runtime.Room(
            id=runtime.uid(),
            user_id=user,
            name=data.name or " + ".join(x.name for x in members),
        )
        db.add(room)
        db.add(
            runtime.AppSetting(
                key="room_public:" + room.id,
                value="true" if data.is_public else "false",
            )
        )
        if len(ids) > 1:
            db.add(
                runtime.AppSetting(
                    key="room_topic:" + room.id, value=data.topic.strip()
                )
            )
        greeting_messages = []
        for c in members:
            db.add(
                runtime.RoomMember(id=runtime.uid(), room_id=room.id, character_id=c.id)
            )
            if (
                not db.query(runtime.CharacterUsage)
                .filter_by(character_id=c.id, user_id=user)
                .first()
            ):
                db.add(
                    runtime.CharacterUsage(
                        id=runtime.uid(), character_id=c.id, user_id=user
                    )
                )
            character = runtime.spec(c)
            greeting = runtime.localized_greeting(db, user, character)
            greeting_message = runtime.Message(
                id=runtime.uid(),
                room_id=room.id,
                sender_type="character",
                character_id=c.id,
                text=greeting,
                emotion=runtime.reply_expression(greeting),
            )
            db.add(greeting_message)
            greeting_messages.append((greeting_message, c))
        db.commit()
        for greeting_message, character in greeting_messages:
            try:
                runtime.asyncio.run(
                    runtime.prepare_message_speech(db, greeting_message, character)
                )
            except Exception:
                pass
        return {**runtime.room_out(db, room), "created": True}

    runtime.create_room = create_room

    def room_out(db, room):
        ids = [
            x.character_id
            for x in db.query(runtime.RoomMember).filter_by(room_id=room.id).all()
        ]
        return {
            "id": room.id,
            "name": room.name,
            "character_ids": ids,
            "created_at": room.created_at,
            "is_public": runtime.room_is_public(db, room.id),
            "topic": runtime.room_topic(db, room.id),
        }

    runtime.room_out = room_out

    @runtime.app.get("/v1/rooms")
    def list_rooms(
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        rows = (
            db.query(runtime.Room)
            .filter(
                runtime.Room.user_id == user,
                ~runtime.Room.name.like(runtime.ASSISTANT_ROOM_PREFIX + "%"),
            )
            .all()
        )
        return [runtime.room_out(db, x) for x in rows]

    runtime.list_rooms = list_rooms

    @runtime.app.get("/v1/rooms/{room_id}")
    def get_room(
        room_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        return runtime.room_out(db, runtime.owned(db, runtime.Room, room_id, user))

    runtime.get_room = get_room

    @runtime.app.patch("/v1/rooms/{room_id}")
    def patch_room(
        room_id: str,
        changes: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        room = runtime.owned(db, runtime.Room, room_id, user)
        if "name" in changes:
            room.name = str(changes["name"])[:100]
        if "topic" in changes:
            if not isinstance(changes["topic"], str) or len(changes["topic"]) > 500:
                raise runtime.HTTPException(422, "Topic must be at most 500 characters")
            topic_row = db.get(runtime.AppSetting, "room_topic:" + room.id)
            if topic_row:
                topic_row.value = changes["topic"].strip()
            else:
                db.add(
                    runtime.AppSetting(
                        key="room_topic:" + room.id, value=changes["topic"].strip()
                    )
                )
        if "is_public" in changes:
            if not isinstance(changes["is_public"], bool):
                raise runtime.HTTPException(400, "is_public must be boolean")
            if changes["is_public"] and not runtime.public_room_members(db, room):
                raise runtime.HTTPException(
                    400, "Cần công khai từng nhân vật trước khi công khai phòng chat."
                )
            row = db.get(runtime.AppSetting, "room_public:" + room.id)
            value = "true" if changes["is_public"] else "false"
            if row:
                row.value = value
            else:
                db.add(runtime.AppSetting(key="room_public:" + room.id, value=value))
        db.commit()
        return runtime.room_out(db, room)

    runtime.patch_room = patch_room

    @runtime.app.delete("/v1/rooms/{room_id}")
    def delete_room(
        room_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        room = runtime.owned(db, runtime.Room, room_id, user)
        runtime.purge_room_record(db, room, reset_all=True)
        db.commit()
        return {"deleted": True}

    runtime.delete_room = delete_room

    @runtime.app.get("/v1/rooms/{room_id}/messages")
    def messages(
        room_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        runtime.owned(db, runtime.Room, room_id, user)
        result = []
        seen_user = False
        for m in (
            db.query(runtime.Message)
            .filter_by(room_id=room_id)
            .order_by(runtime.Message.created_at)
            .all()
        ):
            sources = runtime.json.loads(m.sources)
            emotion = None
            display_text = m.text
            is_opening_greeting = m.sender_type == "character" and not seen_user
            if m.sender_type == "character" and m.character_id and not seen_user:
                character = db.get(runtime.Character, m.character_id)
                if character:
                    display_text = runtime.localized_greeting(
                        db, user, runtime.spec(character)
                    )
            if m.sender_type == "user":
                seen_user = True
            if m.character_id:
                # Re-evaluate every reply independently. A neutral answer must not
                # inherit anger, sadness, or another expression from an older turn.
                emotion = runtime.reply_expression(m.text)
                if emotion != m.emotion:
                    m.emotion = emotion
            item = {
                "id": m.id,
                "sender_type": m.sender_type,
                "character_id": m.character_id,
                "text": display_text,
                "sources": sources,
                "suggestions": (
                    [] if is_opening_greeting else runtime.suggestion_values(db, m.id)
                ),
                "emotion": emotion,
                "interrupted": m.finish_status == "partial",
                "created_at": m.created_at,
            }
            if m.sender_type == "character":
                item.update(
                    runtime.message_speech_info(
                        m, display_text, db, db.get(runtime.Character, m.character_id)
                    )
                )
            if m.sender_type == "document" and sources:
                document = db.get(runtime.Document, sources[0].get("document_id"))
                if document:
                    item["attachment"] = {
                        "document_id": document.id,
                        "filename": document.filename,
                        "status": document.status,
                        "error": document.error,
                    }
            result.append(item)
        db.commit()
        return result

    runtime.messages = messages
