"""services.lifecycle: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_lifespan(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.asynccontextmanager
    async def lifespan(app):
        runtime.init_db()
        with runtime.Session() as db:
            preset_map = {p.preset_type: p for p in runtime.effective_presets(db)}
            overridden = {
                item.key.removeprefix("character_override:")
                for item in db.query(runtime.AppSetting)
                .filter(runtime.AppSetting.key.like("character_override:%"))
                .all()
            }
            runtime.apply_runtime_settings(runtime.runtime_settings(db))
            runtime.apply_shared_credentials(db)
            runtime.apply_model_registry(db)
            for row in db.query(runtime.Character).all():
                if row.id in overridden:
                    continue
                current = runtime.spec(row)
                template = preset_map.get(current.preset_type)
                if template and not current.system_prompt:
                    current.system_prompt = template.system_prompt
                    if current.description in ("", current.display_name):
                        current.description = template.description
                if template and not current.initial_greeting:
                    current.initial_greeting = template.initial_greeting
                if template:
                    row.spec = current.model_dump_json()
                    row.updated_at = runtime.now()
            db.commit()
        try:
            yield
        finally:
            runtime.close_chat_transport()

    runtime.lifespan = lifespan
