"""services.roleplay_context: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_extract_memory(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def extract_memory(db, user, room_id, message_id, text, character_ids):
        if len(text) < 20 or not runtime.re.search(
            r"\b(tôi|mình|tao|tớ|my|i)\b", text, runtime.re.I
        ):
            return
        if not runtime.re.search(
            r"thích|ghét|đang|sẽ|muốn|tên|ngày|tuần|love|hate|interview|remember|nhớ",
            text,
            runtime.re.I,
        ):
            return
        private = len(character_ids) == 1
        memory_type = (
            "preference"
            if runtime.re.search(r"thích|ghét|love|hate", text, runtime.re.I)
            else (
                "event"
                if runtime.re.search(
                    r"hôm qua|hôm nay|tuần trước|đã|vừa|yesterday|today",
                    text,
                    runtime.re.I,
                )
                else "fact"
            )
        )
        importance = 0.75 if memory_type in ("preference", "event") else 0.6
        runtime.store_memory(
            db,
            user_id=user,
            character_id=character_ids[0] if private else None,
            room_id=None if private else room_id,
            visibility="CHARACTER_PRIVATE" if private else "ROOM_SHARED",
            content=text[:500],
            importance=importance,
            confidence=0.7,
            type=memory_type,
            source_message_id=message_id,
        )

    runtime.extract_memory = extract_memory

    def model_log_snapshot(db, config_id, wire_model, product):
        item = db.get(runtime.ModelConfig, config_id) if config_id else None
        if not item and wire_model:
            matches = [
                row
                for row in db.query(runtime.ModelConfig).all()
                if (
                    (row.assistant_model_id or row.model_id)
                    if product == "assistant"
                    else row.model_id
                )
                == wire_model
            ]
            if len(matches) == 1:
                item = matches[0]
        if not item:
            return "", ""
        name = (
            (item.assistant_name or item.name) if product == "assistant" else item.name
        )
        return str(name or wire_model)[:100], str(item.api_base or "")[:500]

    runtime.model_log_snapshot = model_log_snapshot
