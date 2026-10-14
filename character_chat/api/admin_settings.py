"""api.admin_settings: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_get_admin_settings(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/v1/admin/settings")
    def get_admin_settings(
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        return {
            **runtime.runtime_settings(db),
            "_base_prompts": {
                "response": runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                "suggestion": runtime.character_engine.SUGGESTION_SYSTEM_PROMPT,
                "compiler": runtime.character_engine.CHARACTER_COMPILER_SYSTEM_PROMPT,
            },
        }

    runtime.get_admin_settings = get_admin_settings

    @runtime.app.put("/v1/admin/settings")
    def update_admin_settings(
        changes: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        unknown = set(changes) - set(runtime.SETTING_DEFAULTS)
        if unknown:
            raise runtime.HTTPException(
                400, "Unsupported settings: " + ", ".join(sorted(unknown))
            )
        merged = runtime.runtime_settings(db)
        for key, value in changes.items():
            value = (
                str(value).strip()
                if key not in ("response_instruction", "suggestion_instruction")
                else str(value).strip()
            )
            base_prompt = {
                "response_instruction": runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                "suggestion_instruction": runtime.character_engine.SUGGESTION_SYSTEM_PROMPT,
                "compiler_instruction": runtime.character_engine.CHARACTER_COMPILER_SYSTEM_PROMPT,
            }.get(key)
            if base_prompt:
                value = runtime.admin_prompt_addon(base_prompt, value)
            if (
                key
                in ("llm_model", "fallback_model", "moderation_model", "llm_api_base")
                and not value
            ):
                raise runtime.HTTPException(400, f"{key} không được để trống")
            if key == "llm_api_base" and not value.startswith("https://"):
                raise runtime.HTTPException(400, "LLM API base phải dùng https://")
            if key in ("default_temperature", "short_temperature"):
                try:
                    number = float(value)
                except ValueError:
                    raise runtime.HTTPException(400, f"{key} phải là số")
                if not 0 <= number <= 2:
                    raise runtime.HTTPException(400, f"{key} phải từ 0 đến 2")
            if key in ("default_max_tokens", "short_max_tokens"):
                try:
                    number = int(value)
                except ValueError:
                    raise runtime.HTTPException(400, f"{key} phải là số nguyên")
                if not 50 <= number <= 4000:
                    raise runtime.HTTPException(400, f"{key} phải từ 50 đến 4000")
            if len(value) > 8000:
                raise runtime.HTTPException(400, f"{key} vượt quá giới hạn")
            row = db.get(runtime.AppSetting, key)
            if row:
                row.value = value
                row.updated_at = runtime.now()
            else:
                db.add(runtime.AppSetting(key=key, value=value))
            merged[key] = value
        db.commit()
        runtime.apply_runtime_settings(merged)
        return merged

    runtime.update_admin_settings = update_admin_settings

    @runtime.app.get("/v1/admin/credentials")
    def admin_credentials(
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        row = db.get(runtime.AppSetting, "credential:avibi")
        configured = bool(row and row.value) or bool(
            (
                runtime.os.getenv("AIMP_API_KEY")
                or runtime.os.getenv("LLM_API_KEY")
                or ""
            ).strip()
        )
        bases = []
        for setting in (
            db.query(runtime.AppSetting)
            .filter(runtime.AppSetting.key.like("credential_base_meta:%"))
            .all()
        ):
            try:
                data = runtime.json.loads(setting.value)
                identifier = setting.key.removeprefix("credential_base_meta:")
                if db.get(runtime.AppSetting, "credential:base:" + identifier):
                    bases.append(
                        {
                            "id": identifier,
                            "api_base": data["api_base"],
                            "hint": data.get("hint", ""),
                        }
                    )
            except Exception:
                continue
        return {
            "avibi": {
                "configured": configured,
                "source": (
                    "cms"
                    if row and row.value
                    else ("environment" if configured else "missing")
                ),
                "hint": (
                    db.get(runtime.AppSetting, "credential_hint:avibi").value
                    if db.get(runtime.AppSetting, "credential_hint:avibi")
                    else ""
                ),
            },
            "bases": sorted(bases, key=lambda item: item["api_base"]),
        }

    runtime.admin_credentials = admin_credentials

    @runtime.app.put("/v1/admin/credentials/bases")
    def admin_save_base_credential(
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        base = runtime.normalized_api_base(data.get("api_base"))
        secret = str(data.get("api_key") or "").strip()
        if not secret:
            raise runtime.HTTPException(400, "API key không được để trống")
        identifier = runtime.base_credential_id(base)
        for setting_key, value in (
            ("credential:base:" + identifier, runtime.encrypt_admin_secret(secret)),
            (
                "credential_base_meta:" + identifier,
                runtime.json.dumps({"api_base": base, "hint": "••••" + secret[-4:]}),
            ),
        ):
            row = db.get(runtime.AppSetting, setting_key)
            if row:
                row.value = value
                row.updated_at = runtime.now()
            else:
                db.add(runtime.AppSetting(key=setting_key, value=value))
        db.commit()
        runtime.apply_model_registry(db)
        return {"id": identifier, "api_base": base, "hint": "••••" + secret[-4:]}

    runtime.admin_save_base_credential = admin_save_base_credential

    @runtime.app.delete("/v1/admin/credentials/bases/{identifier}")
    def admin_delete_base_credential(
        identifier: str,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        if not runtime.re.fullmatch(r"[0-9a-f]{64}", identifier):
            raise runtime.HTTPException(400, "API base ID không hợp lệ")
        for prefix in ("credential:base:", "credential_base_meta:"):
            row = db.get(runtime.AppSetting, prefix + identifier)
            if row:
                db.delete(row)
        db.commit()
        runtime.apply_model_registry(db)
        return {"deleted": True}

    runtime.admin_delete_base_credential = admin_delete_base_credential

    @runtime.app.put("/v1/admin/credentials/avibi")
    def update_avibi_credential(
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        key = str(data.get("api_key") or "").strip()
        if not key:
            raise runtime.HTTPException(400, "API key không được để trống")
        encrypted = runtime.encrypt_admin_secret(key)
        for setting_key, value in (
            ("credential:avibi", encrypted),
            ("credential_hint:avibi", "••••" + key[-4:]),
        ):
            row = db.get(runtime.AppSetting, setting_key)
            if row:
                row.value = value
                row.updated_at = runtime.now()
            else:
                db.add(runtime.AppSetting(key=setting_key, value=value))
        db.commit()
        runtime.apply_shared_credentials(db)
        runtime.apply_model_registry(db)
        return {"configured": True, "source": "cms", "hint": "••••" + key[-4:]}

    runtime.update_avibi_credential = update_avibi_credential

    @runtime.app.delete("/v1/admin/credentials/avibi")
    def delete_avibi_credential(
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        for key in ("credential:avibi", "credential_hint:avibi"):
            row = db.get(runtime.AppSetting, key)
            if row:
                db.delete(row)
        db.commit()
        runtime.apply_shared_credentials(db)
        runtime.apply_model_registry(db)
        configured = bool(runtime.character_engine.llm.api_key)
        return {
            "configured": configured,
            "source": "environment" if configured else "missing",
            "hint": "",
        }

    runtime.delete_avibi_credential = delete_avibi_credential
