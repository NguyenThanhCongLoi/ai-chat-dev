"""api.assistant_rooms: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_assistant_profiles_config(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def assistant_profiles_config(db):
        items = {}
        for purpose in (*runtime.ASSISTANT_PROMPTS, "assistant_suggestion"):
            row = db.get(runtime.AppSetting, "assistant_profile:" + purpose)
            try:
                profile = runtime.json.loads(row.value) if row else {}
            except (ValueError, TypeError):
                profile = {}
            items[purpose] = {
                "title": runtime.ASSISTANT_ROOM_TITLES.get(purpose, purpose),
                "slogan": "",
                "description": "",
                "greeting": "",
                "starters": [],
                "visible": True,
                "temperature": 0.7,
                "max_tokens": 1024,
                "user_pick": False,
                **profile,
            }
        return {"order": list(runtime.ASSISTANT_PROMPTS), "items": items}

    runtime.assistant_profiles_config = assistant_profiles_config

    def assistant_preferred_model(db, mode, value):
        # CMS permission is enforced server-side as well as in the model selector.
        return (
            str(value or "")
            if runtime.assistant_profiles_config(db)["items"]
            .get(mode, {})
            .get("user_pick")
            else ""
        )

    runtime.assistant_preferred_model = assistant_preferred_model

    @runtime.app.get("/v1/admin/assistant-profiles")
    def admin_assistant_profiles(
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        return runtime.assistant_profiles_config(db)

    runtime.admin_assistant_profiles = admin_assistant_profiles

    @runtime.app.put("/v1/admin/assistant-profiles/{purpose}")
    def admin_save_assistant_profile(
        purpose: str,
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        if purpose not in (*runtime.ASSISTANT_PROMPTS, "assistant_suggestion"):
            raise runtime.HTTPException(400, "Assistant mode is invalid")
        profile = runtime.assistant_profiles_config(db)["items"][purpose]
        for field in ("title", "slogan", "description", "greeting", "icon"):
            if field in data:
                profile[field] = str(data[field])[:4000]
        for field in ("visible", "user_pick"):
            if field in data:
                if not isinstance(data[field], bool):
                    raise runtime.HTTPException(422, field + " must be boolean")
                profile[field] = data[field]
        if "starters" in data:
            if not isinstance(data["starters"], list):
                raise runtime.HTTPException(422, "starters must be a list")
            profile["starters"] = [str(value)[:500] for value in data["starters"][:4]]
        # Generation parameters belong to each selected ModelConfig.
        row = db.get(runtime.AppSetting, "assistant_profile:" + purpose)
        if not row:
            row = runtime.AppSetting(key="assistant_profile:" + purpose, value="")
            db.add(row)
        row.value = runtime.json.dumps(profile, ensure_ascii=False)
        db.commit()
        return profile

    runtime.admin_save_assistant_profile = admin_save_assistant_profile

    @runtime.app.get("/v1/assistant/models")
    def assistant_client_models(
        mode: str = "assistant_general",
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        if mode not in runtime.ASSISTANT_PROMPTS:
            raise runtime.HTTPException(400, "Assistant mode is invalid")
        if not runtime.assistant_profiles_config(db)["items"][mode]["user_pick"]:
            return []
        roles = (mode, mode + "_fallback", mode + "_fallback_2")
        result = []
        enabled = [
            item
            for item in db.query(runtime.ModelConfig)
            .filter_by(assistant_enabled=1)
            .order_by(runtime.ModelConfig.created_at)
            .all()
            if "avatar_image" not in runtime.model_profile(db, item).get("purposes", [])
        ]
        for role in roles:
            item = next(
                (
                    model
                    for model in enabled
                    if role in runtime.model_profile(db, model).get("purposes", [])
                ),
                None,
            )
            if item and all(saved["id"] != item.id for saved in result):
                result.append(
                    {
                        "id": item.id,
                        "name": item.assistant_name or item.name,
                        "role": role,
                    }
                )
        for item in enabled:
            if all(saved["id"] != item.id for saved in result):
                result.append(
                    {
                        "id": item.id,
                        "name": item.assistant_name or item.name,
                        "role": "available",
                    }
                )
        return result

    runtime.assistant_client_models = assistant_client_models

    @runtime.app.get("/v1/assistant/chats")
    def assistant_chats(
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        rows = (
            db.query(runtime.Room)
            .filter(
                runtime.Room.user_id == user,
                runtime.Room.name.like(runtime.ASSISTANT_ROOM_PREFIX + "%"),
            )
            .order_by(runtime.Room.created_at.desc(), runtime.Room.id.desc())
            .all()
        )
        return [runtime.assistant_room_out(row, db) for row in rows]

    runtime.assistant_chats = assistant_chats

    @runtime.app.post("/v1/assistant/chats")
    def create_assistant_chat(
        data: dict,
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        mode = str(data.get("mode") or "assistant_general")
        if mode not in runtime.ASSISTANT_PROMPTS:
            raise runtime.HTTPException(400, "Assistant mode is invalid")
        if mode != "assistant_general":
            existing = (
                db.query(runtime.Room)
                .filter(
                    runtime.Room.user_id == user,
                    runtime.Room.name.like(f"{runtime.ASSISTANT_ROOM_PREFIX}{mode}:%"),
                )
                .order_by(runtime.Room.created_at.desc(), runtime.Room.id.desc())
                .first()
            )
            if existing:
                return {**runtime.assistant_room_out(existing, db), "is_new": False}
        row = runtime.Room(
            id=runtime.uid(),
            user_id=user,
            name=f"{runtime.ASSISTANT_ROOM_PREFIX}{mode}:{runtime.ASSISTANT_ROOM_TITLES[mode]}",
        )
        db.add(row)
        db.commit()
        return {**runtime.assistant_room_out(row), "is_new": True}

    runtime.create_assistant_chat = create_assistant_chat

    @runtime.app.delete("/v1/assistant/chats/{room_id}")
    def delete_assistant_chat(
        room_id: str,
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        room = runtime.assistant_room(db, user, room_id)
        db.query(runtime.AssistantMemory).filter_by(
            user_id=user, room_id=room_id
        ).delete(synchronize_session=False)
        runtime.purge_room_record(db, room)
        db.commit()
        return {"deleted": True}

    runtime.delete_assistant_chat = delete_assistant_chat

    @runtime.app.get("/v1/assistant/chats/{room_id}/messages")
    def assistant_messages(
        room_id: str,
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        runtime.assistant_room(db, user, room_id)
        rows = (
            db.query(runtime.Message)
            .filter_by(room_id=room_id)
            .order_by(runtime.Message.created_at)
            .all()
        )
        return [
            {
                "id": row.id,
                "role": "user" if row.sender_type == "user" else "assistant",
                "text": row.text,
                "sources": runtime.json.loads(row.sources or "[]"),
                "suggestions": runtime.suggestion_values(db, row.id),
                "interrupted": row.finish_status == "partial",
                "created_at": row.created_at,
            }
            for row in rows
        ]

    runtime.assistant_messages = assistant_messages

    @runtime.app.get("/v1/assistant/chats/{room_id}/files")
    def assistant_files(
        room_id: str,
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        runtime.assistant_room(db, user, room_id)
        result = []
        for link in db.query(runtime.RoomDocument).filter_by(room_id=room_id).all():
            document = db.get(runtime.Document, link.document_id)
            if document and document.user_id == user:
                result.append(
                    {
                        "id": document.id,
                        "filename": document.filename,
                        "status": document.status,
                        "error": document.error,
                        "created_at": document.created_at,
                    }
                )
        return result

    runtime.assistant_files = assistant_files

    @runtime.app.delete("/v1/assistant/chats/{room_id}/files/{document_id}")
    def delete_assistant_file(
        room_id: str,
        document_id: str,
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        runtime.assistant_room(db, user, room_id)
        link = (
            db.query(runtime.RoomDocument)
            .filter_by(room_id=room_id, document_id=document_id)
            .first()
        )
        document = db.get(runtime.Document, document_id)
        if not link or not document or document.user_id != user:
            raise runtime.HTTPException(404, "File not found")
        db.delete(link)
        db.flush()
        runtime.purge_document_record(db, document_id)
        db.commit()
        return {"deleted": True}

    runtime.delete_assistant_file = delete_assistant_file

    @runtime.app.get("/v1/assistant/chats/{room_id}/files/{document_id}/content")
    def assistant_file_content(
        room_id: str,
        document_id: str,
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        runtime.assistant_room(db, user, room_id)
        link = (
            db.query(runtime.RoomDocument)
            .filter_by(room_id=room_id, document_id=document_id)
            .first()
        )
        document = db.get(runtime.Document, document_id)
        stored = db.get(runtime.AssistantFile, document_id)
        if not link or not document or document.user_id != user or not stored:
            raise runtime.HTTPException(404, "File not found")
        return runtime.Response(
            content=stored.content,
            media_type=stored.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{document.filename}"'
            },
        )

    runtime.assistant_file_content = assistant_file_content

    @runtime.app.post("/v1/assistant/chats/{room_id}/files")
    def assistant_upload(
        room_id: str,
        file: runtime.UploadFile = runtime.File(...),
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        runtime.assistant_room(db, user, room_id)
        content = file.file.read(12 * 1024 * 1024 + 1)
        if len(content) > 12 * 1024 * 1024:
            raise runtime.HTTPException(413, "File tối đa 12 MB")
        mime = (file.content_type or "").lower()
        suffix = runtime.Path(file.filename or "").suffix.lower()
        is_image = mime in {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
        } and suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        if mime.startswith("image/") and not is_image:
            raise runtime.HTTPException(
                400, "Tệp ảnh cần có phần mở rộng và định dạng ảnh hợp lệ."
            )
        try:
            sections = (
                []
                if is_image
                else runtime.parse_document(file.filename or "file.txt", content)
            )
            if not is_image and not sections:
                raise ValueError(
                    "Không trích xuất được văn bản từ tệp. PDF scan cần OCR trước khi gửi."
                )
        except Exception as exc:
            raise runtime.HTTPException(400, str(exc))
        document = runtime.Document(
            id=runtime.uid(),
            user_id=user,
            filename=(file.filename or "file")[:180],
            status="ready",
        )
        db.add(document)
        db.flush()
        runtime.save_chunks(db, document.id, sections)
        try:
            stored_content, stored_mime = (
                runtime.optimize_card_avatar(content, max_side=1600)
                if is_image
                else (content, mime or "application/octet-stream")
            )
        except Exception as exc:
            db.rollback()
            raise runtime.HTTPException(400, f"Tệp không hợp lệ: {exc}")
        db.add(
            runtime.AssistantFile(
                document_id=document.id, mime_type=stored_mime, content=stored_content
            )
        )
        db.add(
            runtime.RoomDocument(
                id=runtime.uid(), room_id=room_id, document_id=document.id
            )
        )
        db.commit()
        return {"id": document.id, "filename": document.filename, "status": "ready"}

    runtime.assistant_upload = assistant_upload
