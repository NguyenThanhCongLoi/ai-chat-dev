"""api.voice_preferences: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_voice_preferences(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/v1/roleplay/voice-preferences")
    def voice_preferences(
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        prefix = "voice_volume:" + user + ":"
        return {
            row.key[len(prefix) :]: float(row.value)
            for row in db.query(runtime.AppSetting)
            .filter(runtime.AppSetting.key.startswith(prefix))
            .all()
        }

    runtime.voice_preferences = voice_preferences

    @runtime.app.put("/v1/roleplay/characters/{character_id}/volume")
    def set_voice_volume(
        character_id: str,
        data: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        runtime.owned(db, runtime.Character, character_id, user)
        volume = data.get("volume")
        if (
            isinstance(volume, bool)
            or not isinstance(volume, (int, float))
            or not __import__("math").isfinite(volume)
            or not 0 <= volume <= 1
        ):
            raise runtime.HTTPException(400, "Volume must be between 0 and 1")
        key = "voice_volume:" + user + ":" + character_id
        row = db.get(runtime.AppSetting, key)
        if row:
            row.value = str(volume)
            row.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=key, value=str(volume)))
        db.commit()
        return {"volume": volume}

    runtime.set_voice_volume = set_voice_volume
