"""api.admin_overview: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_admin_overview(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/v1/admin/overview")
    def admin_overview(
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        """Protected product-wide CMS metrics and content inventory."""
        characters = (
            db.query(runtime.Character)
            .order_by(runtime.Character.updated_at.desc())
            .all()
        )
        rooms = db.query(runtime.Room).order_by(runtime.Room.created_at.desc()).all()
        room_ids = [item.id for item in rooms]
        documents = (
            db.query(runtime.Document)
            .order_by(runtime.Document.created_at.desc())
            .all()
        )
        messages = (
            db.query(runtime.Message)
            .filter(runtime.Message.room_id.in_(room_ids))
            .order_by(runtime.Message.created_at.desc())
            .limit(12)
            .all()
            if room_ids
            else []
        )
        traces = (
            db.query(runtime.PromptTrace)
            .order_by(runtime.PromptTrace.created_at.desc())
            .limit(8)
            .all()
        )
        return {
            "stats": {
                "characters": len(characters),
                "rooms": len(rooms),
                "messages": (
                    db.query(runtime.Message)
                    .filter(runtime.Message.room_id.in_(room_ids))
                    .count()
                    if room_ids
                    else 0
                ),
                "documents": len(documents),
                "ready_documents": sum(item.status == "ready" for item in documents),
                "failed_documents": sum(item.status == "failed" for item in documents),
                "memories": db.query(runtime.Memory).count(),
                "users": db.query(runtime.User).count(),
            },
            "characters": [
                {
                    "id": item.id,
                    "name": item.name,
                    "role": runtime.spec(item).identity.role,
                    "type": runtime.spec(item).creation_type,
                    "category": runtime.spec(item).category,
                    "updated_at": item.updated_at,
                }
                for item in characters
            ],
            "rooms": [
                {
                    "id": item.id,
                    "name": item.name,
                    "members": db.query(runtime.RoomMember)
                    .filter_by(room_id=item.id)
                    .count(),
                    "messages": db.query(runtime.Message)
                    .filter_by(room_id=item.id)
                    .count(),
                    "updated_at": item.created_at,
                }
                for item in rooms[:12]
            ],
            "documents": [runtime.document_out(item) for item in documents[:12]],
            "activity": [
                {
                    "id": item.id,
                    "type": item.sender_type,
                    "room_id": item.room_id,
                    "preview": item.text[:120],
                    "created_at": item.created_at,
                }
                for item in messages
            ],
            "ai_activity": [
                {
                    "id": item.id,
                    "character_id": item.character_id,
                    "layers": len(runtime.json.loads(item.layers)),
                    "memories": len(runtime.json.loads(item.memory_ids)),
                    "documents": len(runtime.json.loads(item.document_ids)),
                    "created_at": item.created_at,
                }
                for item in traces
            ],
        }

    runtime.admin_overview = admin_overview
