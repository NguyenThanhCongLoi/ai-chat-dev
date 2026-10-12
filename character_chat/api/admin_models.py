"""api.admin_models: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_admin_models(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/v1/admin/models")
    def admin_models(
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        runtime.ensure_model_registry(db)
        return [
            runtime.model_out(item, db)
            for item in db.query(runtime.ModelConfig)
            .order_by(runtime.ModelConfig.created_at.desc())
            .all()
        ]

    runtime.admin_models = admin_models

    @runtime.app.post("/v1/admin/models")
    def admin_create_model(
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        required = {"name", "provider", "model_id", "api_base"}
        if any(not str(data.get(key, "")).strip() for key in required):
            raise runtime.HTTPException(
                400, "Thiếu tên, provider, model ID hoặc API base"
            )
        api_base = str(data["api_base"]).strip().rstrip("/")
        if not api_base.startswith("https://"):
            raise runtime.HTTPException(400, "API base phải dùng https://")
        duplicate = next(
            (
                item
                for item in db.query(runtime.ModelConfig)
                .filter_by(model_id=str(data["model_id"]).strip())
                .all()
                if runtime.normalized_api_base(item.api_base)
                == runtime.normalized_api_base(api_base)
            ),
            None,
        )
        if duplicate:
            raise runtime.HTTPException(409, "Model ID đã tồn tại trong API base này")
        key = str(data.get("api_key", "")).strip()
        display_name = str(data["name"]).strip()[:100]
        core_model_id = str(data["model_id"]).strip()[:180]
        item = runtime.ModelConfig(
            id=runtime.uid(),
            name=display_name,
            provider=str(data["provider"]).strip()[:80],
            model_id=core_model_id,
            api_base=api_base[:500],
            api_key_encrypted=runtime.encrypt_admin_secret(key) if key else "",
            api_key_hint=("••••" + key[-4:] if key else ""),
            logo=str(data.get("logo") or "AI")[:4],
            enabled=int(bool(data.get("enabled", True))),
            assistant_name=display_name,
            assistant_model_id=core_model_id,
            assistant_enabled=1,
            role="available",
        )
        db.add(item)
        db.commit()
        runtime.apply_model_registry(db)
        return runtime.model_out(item, db)

    runtime.admin_create_model = admin_create_model

    @runtime.app.patch("/v1/admin/assistant-models/{model_id}")
    def admin_update_assistant_model(
        model_id: str,
        changes: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        item = db.get(runtime.ModelConfig, model_id)
        if not item:
            raise runtime.HTTPException(404, "Model config not found")
        if "name" in changes:
            value = str(changes["name"]).strip()
            if not value:
                raise runtime.HTTPException(
                    400, "Tên hiển thị Assistant không được để trống"
                )
            item.assistant_name = value[:100]
        if "model_id" in changes:
            value = str(changes["model_id"]).strip()
            if not value:
                raise runtime.HTTPException(
                    400, "Core Model ID của Assistant không được để trống"
                )
            duplicate = next(
                (
                    other
                    for other in db.query(runtime.ModelConfig)
                    .filter(
                        runtime.ModelConfig.assistant_model_id == value,
                        runtime.ModelConfig.id != item.id,
                    )
                    .all()
                    if runtime.normalized_api_base(other.api_base)
                    == runtime.normalized_api_base(item.api_base)
                ),
                None,
            )
            if duplicate:
                raise runtime.HTTPException(
                    409, "Core Model ID của Assistant đã tồn tại"
                )
            item.assistant_model_id = value[:180]
        if "enabled" in changes:
            item.assistant_enabled = int(bool(changes["enabled"]))
        if "thinking_mode" in changes:
            value = str(changes["thinking_mode"])
            if value not in ("default", "enabled", "disabled"):
                raise runtime.HTTPException(400, "Thinking mode không hợp lệ")
            item.assistant_thinking_mode = value
        if "reasoning_effort" in changes:
            value = str(changes["reasoning_effort"])
            if value not in ("default", "low", "high", "max"):
                raise runtime.HTTPException(400, "Reasoning effort không hợp lệ")
            item.assistant_reasoning_effort = value
        if item.assistant_thinking_mode == "disabled":
            item.assistant_reasoning_effort = "default"
        item.updated_at = runtime.now()
        db.commit()
        return runtime.model_out(item, db)

    runtime.admin_update_assistant_model = admin_update_assistant_model

    @runtime.app.patch("/v1/admin/models/{model_id}")
    def admin_update_model(
        model_id: str,
        changes: dict,
        background: runtime.BackgroundTasks,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        item = db.get(runtime.ModelConfig, model_id)
        if not item:
            raise runtime.HTTPException(404, "Model config not found")
        previous_profile = runtime.model_profile(db, item)
        was_image_model = bool(
            item.enabled and "avatar_image" in previous_profile.get("purposes", [])
        )
        previous_base = item.api_base
        previous_enabled = bool(item.enabled)
        previous_purposes = set(previous_profile.get("purposes", []))
        for field in ("name", "provider", "logo"):
            if field in changes:
                setattr(
                    item,
                    field,
                    str(changes[field]).strip()[: 100 if field != "logo" else 4],
                )
        if "model_id" in changes:
            value = str(changes["model_id"]).strip()
            if not value:
                raise runtime.HTTPException(400, "Model ID không được để trống")
            item.model_id = value[:180]
        if "api_base" in changes:
            value = str(changes["api_base"]).strip().rstrip("/")
            if not value.startswith("https://"):
                raise runtime.HTTPException(400, "API base phải dùng https://")
            item.api_base = value[:500]
        duplicate = next(
            (
                other
                for other in db.query(runtime.ModelConfig)
                .filter(
                    runtime.ModelConfig.model_id == item.model_id,
                    runtime.ModelConfig.id != item.id,
                )
                .all()
                if runtime.normalized_api_base(other.api_base)
                == runtime.normalized_api_base(item.api_base)
            ),
            None,
        )
        if duplicate:
            raise runtime.HTTPException(409, "Model ID đã tồn tại trong API base này")
        assistant_duplicate = next(
            (
                other
                for other in db.query(runtime.ModelConfig)
                .filter(
                    runtime.ModelConfig.assistant_model_id == item.assistant_model_id,
                    runtime.ModelConfig.id != item.id,
                )
                .all()
                if runtime.normalized_api_base(other.api_base)
                == runtime.normalized_api_base(item.api_base)
            ),
            None,
        )
        if assistant_duplicate:
            raise runtime.HTTPException(
                409, "Core Model ID của Assistant đã tồn tại trong API base này"
            )
        if "api_key" in changes and str(changes["api_key"]).strip():
            key = str(changes["api_key"]).strip()
            item.api_key_encrypted = runtime.encrypt_admin_secret(key)
            item.api_key_hint = "••••" + key[-4:]
        if changes.get("clear_api_key"):
            item.api_key_encrypted = ""
            item.api_key_hint = ""
        if "enabled" in changes:
            item.enabled = int(bool(changes["enabled"]))
        if "role" in changes:
            role = str(changes["role"])
            if role not in ("available", "primary", "fallback"):
                raise runtime.HTTPException(400, "Role model không hợp lệ")
            if role in ("primary", "fallback"):
                for other in db.query(runtime.ModelConfig).filter_by(role=role).all():
                    other.role = "available"
            item.role = role
        profile = runtime.model_profile(db, item)
        for field in (
            "response_instruction",
            "suggestion_instruction",
            "compiler_instruction",
            "moderation_instruction",
            "emotion_instruction",
            "tts_default_voice",
            *(purpose + "_instruction" for purpose in runtime.ASSISTANT_PROMPTS),
            *(
                purpose + "_fallback_instruction"
                for purpose in runtime.ASSISTANT_PROMPTS
            ),
            *(
                purpose + "_fallback_2_instruction"
                for purpose in runtime.ASSISTANT_PROMPTS
            ),
            "assistant_suggestion_instruction",
            "assistant_suggestion_fallback_instruction",
            "assistant_suggestion_fallback_2_instruction",
            "temperature",
            "short_temperature",
            "max_tokens",
            "short_max_tokens",
            "gateway_read_timeout_seconds",
            "thinking_mode",
            "reasoning_effort",
        ):
            if field in changes:
                value = str(changes[field])
                if field == "thinking_mode" and value not in (
                    "default",
                    "enabled",
                    "disabled",
                ):
                    raise runtime.HTTPException(400, "Thinking mode không hợp lệ")
                if field == "reasoning_effort" and value not in (
                    "default",
                    "low",
                    "high",
                    "max",
                ):
                    raise runtime.HTTPException(400, "Reasoning effort không hợp lệ")
                if field == "gateway_read_timeout_seconds":
                    try:
                        seconds = int(value)
                    except ValueError:
                        raise runtime.HTTPException(
                            400, "Gateway timeout phải là số giây từ 4 đến 45"
                        )
                    if not 4 <= seconds <= 45:
                        raise runtime.HTTPException(
                            400, "Gateway timeout phải là số giây từ 4 đến 45"
                        )
                    value = str(seconds)
                if field == "tts_default_voice":
                    value = value.strip()[:160]
                base = {
                    "response_instruction": runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                    "suggestion_instruction": runtime.character_engine.SUGGESTION_SYSTEM_PROMPT,
                    "compiler_instruction": runtime.character_engine.CHARACTER_COMPILER_SYSTEM_PROMPT,
                    "moderation_instruction": runtime.MODERATION_SYSTEM_PROMPT,
                    "emotion_instruction": runtime.EMOTION_DETECTION_SYSTEM_PROMPT,
                    **{
                        purpose + "_instruction": prompt
                        for purpose, prompt in runtime.ASSISTANT_PROMPTS.items()
                    },
                    **{
                        purpose + "_fallback_instruction": prompt
                        for purpose, prompt in runtime.ASSISTANT_PROMPTS.items()
                    },
                    **{
                        purpose + "_fallback_2_instruction": prompt
                        for purpose, prompt in runtime.ASSISTANT_PROMPTS.items()
                    },
                    "assistant_suggestion_instruction": runtime.ASSISTANT_SUGGESTION_PROMPT,
                    "assistant_suggestion_fallback_instruction": runtime.ASSISTANT_SUGGESTION_PROMPT,
                    "assistant_suggestion_fallback_2_instruction": runtime.ASSISTANT_SUGGESTION_PROMPT,
                }.get(field)
                profile[field] = (
                    runtime.admin_prompt_addon(base, value) if base else value
                )
        if "purposes" in changes:
            assistant_fallbacks = {
                purpose + "_fallback" for purpose in runtime.ASSISTANT_PROMPTS
            }
            assistant_fallbacks_2 = {
                purpose + "_fallback_2" for purpose in runtime.ASSISTANT_PROMPTS
            }
            assistant_suggestion_roles = {
                "assistant_suggestion",
                "assistant_suggestion_fallback",
                "assistant_suggestion_fallback_2",
            }
            allowed = {
                "response",
                "suggestion",
                "suggestion_fallback",
                "suggestion_fallback_2",
                "compiler",
                "moderation",
                "fallback",
                "fallback_2",
                "avatar_image",
                "emotion",
                "emotion_fallback",
                "emotion_fallback_2",
                "tts",
                *runtime.ASSISTANT_PROMPTS,
                *assistant_fallbacks,
                *assistant_fallbacks_2,
                *assistant_suggestion_roles,
            }
            profile["purposes"] = [x for x in changes["purposes"] if x in allowed]
            for purpose in profile["purposes"]:
                if purpose in allowed:
                    for other in (
                        db.query(runtime.AppSetting)
                        .filter(runtime.AppSetting.key.like("model_profile:%"))
                        .all()
                    ):
                        if other.key == "model_profile:" + item.id:
                            continue
                        try:
                            saved = runtime.json.loads(other.value)
                            if purpose in saved.get("purposes", []):
                                saved["purposes"].remove(purpose)
                                other.value = runtime.json.dumps(
                                    saved, ensure_ascii=False
                                )
                                other.updated_at = runtime.now()
                        except Exception:
                            continue
        if profile.get("thinking_mode") == "disabled":
            profile["reasoning_effort"] = "default"
        profile_key = "model_profile:" + item.id
        profile_row = db.get(runtime.AppSetting, profile_key)
        if profile_row:
            profile_row.value = runtime.json.dumps(profile, ensure_ascii=False)
            profile_row.updated_at = runtime.now()
        else:
            db.add(
                runtime.AppSetting(
                    key=profile_key,
                    value=runtime.json.dumps(profile, ensure_ascii=False),
                )
            )
        item.updated_at = runtime.now()
        db.commit()
        runtime.apply_model_registry(db)
        is_image_model = bool(
            item.enabled and "avatar_image" in profile.get("purposes", [])
        )
        image_config_changed = (
            ("api_base" in changes and item.api_base != previous_base)
            or bool(str(changes.get("api_key") or "").strip())
            or bool(changes.get("clear_api_key"))
            or ("enabled" in changes and bool(item.enabled) != previous_enabled)
            or (
                "purposes" in changes
                and set(profile.get("purposes", [])) != previous_purposes
            )
        )
        # The backfill is idempotent: it groups identical source images, skips every
        # character whose shared source already has a complete cached set, and calls
        # the image model once only for each missing unique source.
        generation = None
        if is_image_model and (not was_image_model or image_config_changed):
            generation = runtime.expression_backfill_plan(db)
            background.add_task(runtime.backfill_character_expressions)
        result = runtime.model_out(item, db)
        if generation is not None:
            result["expression_generation"] = generation
        return result

    runtime.admin_update_model = admin_update_model

    @runtime.app.put("/v1/admin/assistant-purposes/{purpose}")
    def admin_save_assistant_purpose(
        purpose: str,
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        if purpose not in (*runtime.ASSISTANT_PROMPTS.keys(), "assistant_suggestion"):
            raise runtime.HTTPException(404, "Unknown Assistant task")
        slots = ("primary", "fallback", "fallback_2")
        ids = [str(data.get(slot + "_model_id") or "").strip() for slot in slots]
        chosen = [value for value in ids if value]
        if len(chosen) != 3:
            raise runtime.HTTPException(
                400, "Cần gán đủ model chính, fallback 1 và fallback 2 cho tác vụ này"
            )
        if len(chosen) != len(set(chosen)):
            raise runtime.HTTPException(400, "Mỗi vị trí cần một model riêng")
        items = {
            item.id: item
            for item in db.query(runtime.ModelConfig)
            .filter(
                runtime.ModelConfig.id.in_(chosen),
                runtime.ModelConfig.assistant_enabled == 1,
            )
            .all()
        }
        if len(items) != len(chosen):
            raise runtime.HTTPException(400, "Model được chọn không tồn tại")
        role_names = (purpose, purpose + "_fallback", purpose + "_fallback_2")
        all_items = db.query(runtime.ModelConfig).all()
        profiles = {item.id: runtime.model_profile(db, item) for item in all_items}
        for item in all_items:
            profile = profiles[item.id]
            profile["purposes"] = [
                role for role in profile.get("purposes", []) if role not in role_names
            ]
        base = runtime.ASSISTANT_PROMPTS.get(
            purpose, runtime.ASSISTANT_SUGGESTION_PROMPT
        )
        for index, item_id in enumerate(ids):
            if not item_id:
                continue
            profile = profiles[item_id]
            profile["purposes"].append(role_names[index])
            prompt_field = purpose + (
                "_instruction"
                if index == 0
                else (
                    "_fallback_instruction" if index == 1 else "_fallback_2_instruction"
                )
            )
            if slots[index] + "_prompt" in data:
                profile[prompt_field] = runtime.admin_prompt_addon(
                    base, str(data.get(slots[index] + "_prompt") or "")
                )
        for item in all_items:
            key = "model_profile:" + item.id
            row = db.get(runtime.AppSetting, key)
            value = runtime.json.dumps(profiles[item.id], ensure_ascii=False)
            if row:
                row.value = value
                row.updated_at = runtime.now()
            else:
                db.add(runtime.AppSetting(key=key, value=value))
        db.commit()
        runtime.apply_model_registry(db)
        return {
            "saved": True,
            "purpose": purpose,
            "assignments": dict(zip(role_names, ids)),
        }

    runtime.admin_save_assistant_purpose = admin_save_assistant_purpose

    @runtime.app.delete("/v1/admin/models/{model_id}")
    def admin_delete_model(
        model_id: str,
        force: bool = False,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        item = db.get(runtime.ModelConfig, model_id)
        if not item:
            raise runtime.HTTPException(404, "Model config not found")
        if not force and item.role in ("primary", "fallback"):
            raise runtime.HTTPException(
                409, "Unassign the primary or fallback role before deleting this model"
            )
        profile = db.get(runtime.AppSetting, "model_profile:" + item.id)
        if profile:
            db.delete(profile)
        db.delete(item)
        db.commit()
        runtime.apply_model_registry(db)
        return {"deleted": True}

    runtime.admin_delete_model = admin_delete_model
