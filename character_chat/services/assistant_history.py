"""services.assistant_history: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_bounded_assistant_history(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def bounded_assistant_history(rows, max_messages=10, max_chars=24000):
        """Keep newest turns while bounding gateway request size."""
        result = []
        used = 0
        for item in reversed(rows[-max_messages:]):
            text = item.text or ""
            remaining = max_chars - used
            if remaining <= 0:
                break
            value = text[-min(len(text), 5000, remaining) :]
            result.append(
                {
                    "role": "user" if item.sender_type == "user" else "assistant",
                    "content": value,
                }
            )
            used += len(value)
        return list(reversed(result))

    runtime.bounded_assistant_history = bounded_assistant_history

    def assistant_history_with_images(db, room_id, rows, max_images=4):
        """Reattach recent room-owned image files to their original user turns."""
        messages = runtime.bounded_assistant_history(rows)
        selected = rows[-len(messages) :] if messages else []
        remaining = max_images
        for index in range(len(selected) - 1, -1, -1):
            message = selected[index]
            if message.sender_type != "user" or remaining <= 0:
                continue
            try:
                source_ids = [
                    str(value.get("document_id"))
                    for value in runtime.json.loads(message.sources or "[]")
                    if isinstance(value, dict) and value.get("document_id")
                ]
            except Exception:
                source_ids = []
            if not source_ids:
                continue
            linked = {
                row.document_id
                for row in db.query(runtime.RoomDocument)
                .filter(
                    runtime.RoomDocument.room_id == room_id,
                    runtime.RoomDocument.document_id.in_(source_ids),
                )
                .all()
            }
            images = (
                db.query(runtime.AssistantFile)
                .filter(
                    runtime.AssistantFile.document_id.in_(linked),
                    runtime.AssistantFile.mime_type.like("image/%"),
                )
                .order_by(runtime.AssistantFile.created_at.desc())
                .limit(remaining)
                .all()
                if linked
                else []
            )
            if not images:
                continue
            content = [{"type": "text", "text": message.text or ""}]
            for image_file in reversed(images):
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_file.mime_type};base64,{runtime.base64.b64encode(image_file.content).decode('ascii')}"
                        },
                    }
                )
            messages[index]["content"] = content
            remaining -= len(images)
        return messages

    runtime.assistant_history_with_images = assistant_history_with_images

    def latest_room_images(db, room_id, user_id, max_images=4):
        rows = (
            db.query(runtime.Message)
            .filter_by(room_id=room_id, sender_type="user")
            .order_by(runtime.Message.created_at.desc())
            .limit(40)
            .all()
        )
        images = []
        seen = set()
        for message in rows:
            try:
                sources = runtime.json.loads(message.sources or "[]")
            except Exception:
                sources = []
            for source in sources:
                document_id = (
                    str(source.get("document_id") or "")
                    if isinstance(source, dict)
                    else ""
                )
                if not document_id or document_id in seen:
                    continue
                seen.add(document_id)
                link = (
                    db.query(runtime.RoomDocument)
                    .filter_by(room_id=room_id, document_id=document_id)
                    .first()
                )
                document = db.get(runtime.Document, document_id)
                if not link or not document or document.user_id != user_id:
                    continue
                stored = db.get(runtime.AssistantFile, document_id)
                if stored and stored.mime_type.startswith("image/"):
                    images.append(stored)
                    if len(images) >= max_images:
                        return images
        return images

    runtime.latest_room_images = latest_room_images
