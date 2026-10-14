"""services.model_registry: domain-specific application implementation.

Model assignments, runtime settings and encrypted provider credentials.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_runtime_settings(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def runtime_settings(db):
        saved = dict(
            db.query(runtime.AppSetting.key, runtime.AppSetting.value)
            .filter(runtime.AppSetting.key.in_(tuple(runtime.SETTING_DEFAULTS)))
            .all()
        )
        return {**runtime.SETTING_DEFAULTS, **saved}

    runtime.runtime_settings = runtime_settings

    def effective_project_prompt(base, configured):
        configured = (configured or "").strip()
        return configured or base

    runtime.effective_project_prompt = effective_project_prompt

    def admin_prompt_addon(base, configured):
        """Collapse legacy copies of the base while preserving real Admin prompts."""
        value = (configured or "").strip()
        base = base.strip()
        if not value or value == base:
            return ""
        legacy_marker = "Admin-configured instruction:"
        if (
            value.startswith(base + "\n")
            and legacy_marker in value[len(base) : len(base) + 100]
        ):
            value = value[len(base) :].lstrip()
            if value.startswith(legacy_marker):
                value = value[len(legacy_marker) :].lstrip()
        return value

    runtime.admin_prompt_addon = admin_prompt_addon

    def apply_runtime_settings(settings):
        runtime.character_engine.llm.model = settings["llm_model"]
        runtime.character_engine.llm.fallback_model = settings["fallback_model"]
        runtime.character_engine.llm.url = settings["llm_api_base"].rstrip("/")
        runtime.character_engine.ADMIN_RESPONSE_INSTRUCTION = (
            runtime.effective_project_prompt(
                runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                settings["response_instruction"],
            )
        )
        runtime.character_engine.ADMIN_SUGGESTION_INSTRUCTION = (
            runtime.effective_project_prompt(
                runtime.character_engine.SUGGESTION_SYSTEM_PROMPT,
                settings["suggestion_instruction"],
            )
        )
        runtime.character_engine.ADMIN_COMPILER_INSTRUCTION = (
            runtime.effective_project_prompt(
                runtime.character_engine.CHARACTER_COMPILER_SYSTEM_PROMPT,
                settings["compiler_instruction"],
            )
        )
        runtime.character_engine.llm.default_temperature = float(
            settings["default_temperature"]
        )
        runtime.character_engine.llm.short_temperature = float(
            settings["short_temperature"]
        )
        runtime.character_engine.llm.default_max_tokens = int(
            settings["default_max_tokens"]
        )
        runtime.character_engine.llm.short_max_tokens = int(
            settings["short_max_tokens"]
        )
        runtime.os.environ["MODERATION_MODEL"] = settings["moderation_model"]

    runtime.apply_runtime_settings = apply_runtime_settings

    def _vault_cipher():
        source = (
            runtime.os.getenv("DOCS_PASSWORD")
            or runtime.os.getenv("ADMIN_ENCRYPTION_KEY")
            or ""
        ).encode()
        if not source:
            raise runtime.HTTPException(503, "Chưa cấu hình khóa mã hóa CMS")
        return runtime.Fernet(
            runtime.base64.urlsafe_b64encode(
                runtime.hashlib.sha256(b"ai-role-play-model-vault:" + source).digest()
            )
        )

    runtime._vault_cipher = _vault_cipher

    def encrypt_admin_secret(value):
        return runtime._vault_cipher().encrypt(value.encode()).decode()

    runtime.encrypt_admin_secret = encrypt_admin_secret

    def decrypt_admin_secret(value):
        try:
            return runtime._vault_cipher().decrypt(value.encode()).decode()
        except runtime.InvalidToken:
            raise runtime.HTTPException(
                503, "Không thể giải mã API key; hãy nhập lại key trong CMS"
            )

    runtime.decrypt_admin_secret = decrypt_admin_secret

    def normalized_api_base(value):
        from urllib.parse import urlsplit

        base = str(value or "").strip().rstrip("/")
        parsed = urlsplit(base)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise runtime.HTTPException(400, "API base phải là URL HTTPS hợp lệ")
        return base.lower()

    runtime.normalized_api_base = normalized_api_base

    def base_credential_id(api_base):
        return runtime.hashlib.sha256(
            runtime.normalized_api_base(api_base).encode()
        ).hexdigest()

    runtime.base_credential_id = base_credential_id

    def environment_credential(api_base):
        # Explicit provider keys travel in private env files, never in Git or API responses.
        raw = runtime.os.getenv("PROVIDER_API_KEYS_JSON", "").strip()
        if not raw:
            return ""
        try:
            mapping = runtime.json.loads(raw)
            if not isinstance(mapping, dict):
                raise ValueError()
            normalized = {}
            for base, key in mapping.items():
                if not isinstance(key, str) or not key.strip():
                    raise ValueError()
                normalized[runtime.normalized_api_base(base)] = key.strip()
            return normalized.get(runtime.normalized_api_base(api_base), "")
        except (ValueError, TypeError, runtime.HTTPException):
            # Do not include the JSON payload or credentials in error details.
            raise runtime.HTTPException(503, "Invalid PROVIDER_API_KEYS_JSON configuration") from None

    runtime.environment_credential = environment_credential

    def credential_for_base(db, api_base):
        if key := runtime.environment_credential(api_base):
            return key
        base = runtime.normalized_api_base(api_base)
        stored = db.get(
            runtime.AppSetting, "credential:base:" + runtime.base_credential_id(base)
        )
        if stored and stored.value:
            return runtime.decrypt_admin_secret(stored.value)
        if base == "https://gateway.avibi.ai/v1":
            shared = db.get(runtime.AppSetting, "credential:avibi")
            if shared and shared.value:
                return runtime.decrypt_admin_secret(shared.value)
            return (
                runtime.os.getenv("AIMP_API_KEY")
                or runtime.os.getenv("LLM_API_KEY")
                or runtime.os.getenv("OPENAI_API_KEY")
                or ""
            ).strip()
        return ""

    runtime.credential_for_base = credential_for_base

    def credential_for_model(db, model):
        if key := runtime.environment_credential(model.api_base):
            return key
        if model.api_key_encrypted:
            return runtime.decrypt_admin_secret(model.api_key_encrypted)
        return runtime.credential_for_base(db, model.api_base)

    runtime.credential_for_model = credential_for_model

    def model_profile(db, item):
        settings = runtime.runtime_settings(db)
        defaults = {
            "purposes": [],
            "response_instruction": runtime.admin_prompt_addon(
                runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                settings["response_instruction"],
            ),
            "suggestion_instruction": runtime.admin_prompt_addon(
                runtime.character_engine.SUGGESTION_SYSTEM_PROMPT,
                settings["suggestion_instruction"],
            ),
            "compiler_instruction": runtime.admin_prompt_addon(
                runtime.character_engine.CHARACTER_COMPILER_SYSTEM_PROMPT,
                settings["compiler_instruction"],
            ),
            "moderation_instruction": "",
            "emotion_instruction": "",
            "tts_default_voice": "",
            **{purpose + "_instruction": "" for purpose in runtime.ASSISTANT_PROMPTS},
            **{
                purpose + "_fallback_instruction": ""
                for purpose in runtime.ASSISTANT_PROMPTS
            },
            **{
                purpose + "_fallback_2_instruction": ""
                for purpose in runtime.ASSISTANT_PROMPTS
            },
            "assistant_suggestion_instruction": "",
            "assistant_suggestion_fallback_instruction": "",
            "assistant_suggestion_fallback_2_instruction": "",
            "temperature": settings["default_temperature"],
            "short_temperature": settings["short_temperature"],
            "max_tokens": settings["default_max_tokens"],
            "short_max_tokens": settings["short_max_tokens"],
            "gateway_read_timeout_seconds": "12",
            "thinking_mode": "default",
            "reasoning_effort": "default",
        }
        row = db.get(runtime.AppSetting, "model_profile:" + item.id)
        if row:
            try:
                return {**defaults, **runtime.json.loads(row.value)}
            except Exception:
                pass
        return defaults

    runtime.model_profile = model_profile

    def model_out(item, db=None):
        result = {
            "id": item.id,
            "name": item.name,
            "provider": item.provider,
            "model_id": item.model_id,
            "api_base": item.api_base,
            "logo": item.logo,
            "enabled": bool(item.enabled),
            "assistant_name": item.assistant_name or item.name,
            "assistant_model_id": item.assistant_model_id or item.model_id,
            "assistant_enabled": bool(item.assistant_enabled),
            "assistant_thinking_mode": item.assistant_thinking_mode or "default",
            "assistant_reasoning_effort": item.assistant_reasoning_effort or "default",
            "role": item.role,
            "has_api_key": bool(item.api_key_encrypted),
            "api_key_hint": item.api_key_hint,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        if db:
            profile = runtime.model_profile(db, item)
            # Empty stored instructions mean "use the project prompt". Return the
            # effective values so Admin can always inspect and edit what is used.
            profile["response_instruction"] = runtime.effective_project_prompt(
                runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                profile.get("response_instruction", ""),
            )
            profile["suggestion_instruction"] = runtime.effective_project_prompt(
                runtime.character_engine.SUGGESTION_SYSTEM_PROMPT,
                profile.get("suggestion_instruction", ""),
            )
            profile["compiler_instruction"] = runtime.effective_project_prompt(
                runtime.character_engine.CHARACTER_COMPILER_SYSTEM_PROMPT,
                profile.get("compiler_instruction", ""),
            )
            profile["moderation_instruction"] = runtime.effective_project_prompt(
                runtime.MODERATION_SYSTEM_PROMPT,
                profile.get("moderation_instruction", ""),
            )
            profile["emotion_instruction"] = runtime.effective_project_prompt(
                runtime.EMOTION_DETECTION_SYSTEM_PROMPT,
                profile.get("emotion_instruction", ""),
            )
            for purpose in runtime.ASSISTANT_PROMPTS:
                profile[purpose + "_instruction"] = runtime.effective_project_prompt(
                    runtime.ASSISTANT_PROMPTS[purpose],
                    profile.get(purpose + "_instruction", ""),
                )
                profile[purpose + "_fallback_instruction"] = (
                    runtime.effective_project_prompt(
                        runtime.ASSISTANT_PROMPTS[purpose],
                        profile.get(purpose + "_fallback_instruction", ""),
                    )
                )
                profile[purpose + "_fallback_2_instruction"] = (
                    runtime.effective_project_prompt(
                        runtime.ASSISTANT_PROMPTS[purpose],
                        profile.get(purpose + "_fallback_2_instruction", ""),
                    )
                )
            for field in (
                "assistant_suggestion_instruction",
                "assistant_suggestion_fallback_instruction",
                "assistant_suggestion_fallback_2_instruction",
            ):
                profile[field] = runtime.effective_project_prompt(
                    runtime.ASSISTANT_SUGGESTION_PROMPT, profile.get(field, "")
                )
            result.update(profile)
        return result

    runtime.model_out = model_out

    def ensure_model_registry(db):
        """Migrate legacy saved model settings into the editable registry once."""
        settings = runtime.runtime_settings(db)
        if not db.query(runtime.ModelConfig).count():
            assignments = {}
            for purpose, key in (
                ("response", "llm_model"),
                ("suggestion", "llm_model"),
                ("compiler", "llm_model"),
                ("fallback", "fallback_model"),
                ("moderation", "moderation_model"),
            ):
                model_id = settings.get(key, "").strip()
                if model_id:
                    assignments.setdefault(model_id, []).append(purpose)
            for model_id, purposes in assignments.items():
                item = runtime.ModelConfig(
                    id=runtime.uid(),
                    name=model_id.split("/")[-1],
                    provider=(
                        model_id.split("/")[0].upper() if "/" in model_id else "AVIBI"
                    ),
                    model_id=model_id,
                    api_base=settings["llm_api_base"],
                    api_key_encrypted="",
                    api_key_hint="",
                    logo="AI",
                    enabled=1,
                    role="available",
                )
                db.add(item)
                profile = {"purposes": purposes}
                db.add(
                    runtime.AppSetting(
                        key="model_profile:" + item.id,
                        value=runtime.json.dumps(profile, ensure_ascii=False),
                    )
                )
            db.flush()
        image_migration = db.get(
            runtime.AppSetting, "migration:image_model_registry:v1"
        )
        if not image_migration:
            image_model_id = runtime.os.getenv(
                "AVATAR_IMAGE_MODEL", "openai/gpt-image-1-mini"
            )
            image_model = (
                db.query(runtime.ModelConfig).filter_by(model_id=image_model_id).first()
            )
            if not image_model:
                image_model = runtime.ModelConfig(
                    id=runtime.uid(),
                    name="GPT Image 1 Mini",
                    provider="OPENAI / AVIBI",
                    model_id=image_model_id,
                    api_base=settings["llm_api_base"],
                    api_key_encrypted="",
                    api_key_hint="",
                    logo="IMG",
                    enabled=1,
                    role="available",
                )
                db.add(image_model)
                db.flush()
            # Register the image model so it remains editable in CMS, but leave image
            # generation disabled until an administrator explicitly assigns the
            # ``avatar_image`` purpose. This also makes an unassignment persistent
            # across application restarts.
            db.add(
                runtime.AppSetting(
                    key="migration:image_model_registry:v1", value="done"
                )
            )
            db.flush()
        # One-time compatibility migration: profiles created by the old CMS inherit
        # every prompt and generation number that was active before this redesign.
        for item in db.query(runtime.ModelConfig).all():
            key = "model_profile:" + item.id
            row = db.get(runtime.AppSetting, key)
            try:
                profile = runtime.json.loads(row.value) if row else {}
            except Exception:
                profile = {}
            if not profile.get("legacy_config_inherited"):
                profile.update(
                    {
                        "response_instruction": settings["response_instruction"],
                        "suggestion_instruction": settings["suggestion_instruction"],
                        "compiler_instruction": settings["compiler_instruction"],
                        "temperature": settings["default_temperature"],
                        "short_temperature": settings["short_temperature"],
                        "max_tokens": settings["default_max_tokens"],
                        "short_max_tokens": settings["short_max_tokens"],
                        "legacy_config_inherited": True,
                    }
                )
                if row:
                    row.value = runtime.json.dumps(profile, ensure_ascii=False)
                    row.updated_at = runtime.now()
                else:
                    db.add(
                        runtime.AppSetting(
                            key=key,
                            value=runtime.json.dumps(profile, ensure_ascii=False),
                        )
                    )
                if not row:
                    db.flush()
                    row = db.get(runtime.AppSetting, key)
            if not profile.get("project_prompt_inherited"):
                prompt_fields = (
                    (
                        "response_instruction",
                        runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                    ),
                    (
                        "suggestion_instruction",
                        runtime.character_engine.SUGGESTION_SYSTEM_PROMPT,
                    ),
                    (
                        "compiler_instruction",
                        runtime.character_engine.CHARACTER_COMPILER_SYSTEM_PROMPT,
                    ),
                )
                for field, base in prompt_fields:
                    current = str(profile.get(field) or "").strip()
                    legacy = str(settings.get(field) or "").strip()
                    if not current or current == legacy:
                        profile[field] = runtime.effective_project_prompt(base, legacy)
                profile["project_prompt_inherited"] = True
                if row:
                    row.value = runtime.json.dumps(profile, ensure_ascii=False)
                    row.updated_at = runtime.now()
                else:
                    db.add(
                        runtime.AppSetting(
                            key=key,
                            value=runtime.json.dumps(profile, ensure_ascii=False),
                        )
                    )
            if not profile.get("base_prompt_addon_migrated_v1"):
                for field, base in (
                    (
                        "response_instruction",
                        runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                    ),
                    (
                        "suggestion_instruction",
                        runtime.character_engine.SUGGESTION_SYSTEM_PROMPT,
                    ),
                    (
                        "compiler_instruction",
                        runtime.character_engine.CHARACTER_COMPILER_SYSTEM_PROMPT,
                    ),
                ):
                    profile[field] = runtime.admin_prompt_addon(
                        base, profile.get(field, "")
                    )
                profile["base_prompt_addon_migrated_v1"] = True
                if row:
                    row.value = runtime.json.dumps(profile, ensure_ascii=False)
                    row.updated_at = runtime.now()
                else:
                    db.add(
                        runtime.AppSetting(
                            key=key,
                            value=runtime.json.dumps(profile, ensure_ascii=False),
                        )
                    )
        db.commit()

    runtime.ensure_model_registry = ensure_model_registry

    def apply_model_registry(db):
        # Reset first so removed or disabled assignments cannot remain active.
        runtime.apply_runtime_settings(runtime.runtime_settings(db))
        # CMS role assignments are authoritative after the registry is created.
        runtime.character_engine.llm.model = ""
        runtime.character_engine.llm.fallback_model = ""
        runtime.character_engine.llm.fallback_model_2 = ""
        rows = db.query(runtime.ModelConfig).filter_by(enabled=1).all()
        runtime.character_engine.llm.model_api_keys = {}
        runtime.character_engine.llm.model_api_bases = {}
        runtime.character_engine.llm.model_wire_ids = {}
        runtime.character_engine.llm.model_thinking_modes = {}
        runtime.character_engine.llm.model_reasoning_efforts = {}
        runtime.character_engine.llm.model_generation = {}
        runtime.character_engine.llm.model_gateway_timeouts = {}
        runtime.character_engine.llm.purpose_models = {}
        runtime.character_engine.llm.fallback_instruction = ""
        for key in (
            "ADMIN_EMOTION_INSTRUCTION",
            "ADMIN_EMOTION_FALLBACK_INSTRUCTION",
            "ADMIN_MODERATION_INSTRUCTION",
            "ADMIN_MODERATION_MODEL",
            "ADMIN_MODERATION_API_BASE",
            "ADMIN_MODERATION_API_KEY",
        ):
            runtime.os.environ.pop(key, None)
        for item in rows:
            profile = runtime.model_profile(db, item)
            purposes = profile.get("purposes", [])
            runtime.character_engine.llm.model_wire_ids[item.id] = item.model_id
            try:
                runtime.character_engine.llm.model_api_keys[item.id] = (
                    runtime.credential_for_model(db, item)
                )
            except runtime.HTTPException:
                runtime.character_engine.llm.model_api_keys[item.id] = ""
            runtime.character_engine.llm.model_api_bases[item.id] = item.api_base
            runtime.character_engine.llm.model_thinking_modes[item.id] = str(
                profile.get("thinking_mode") or "default"
            )
            runtime.character_engine.llm.model_reasoning_efforts[item.id] = str(
                profile.get("reasoning_effort") or "default"
            )
            runtime.character_engine.llm.model_generation[item.id] = {
                field: profile[field]
                for field in (
                    "temperature",
                    "short_temperature",
                    "max_tokens",
                    "short_max_tokens",
                )
                if field in profile
            }
            runtime.character_engine.llm.model_gateway_timeouts[item.id] = int(
                profile.get("gateway_read_timeout_seconds", 12)
            )
            if "response" in purposes:
                runtime.character_engine.llm.model = item.id
                runtime.character_engine.ADMIN_RESPONSE_INSTRUCTION = (
                    runtime.effective_project_prompt(
                        runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                        profile.get("response_instruction", ""),
                    )
                )
                try:
                    runtime.character_engine.llm.default_temperature = float(
                        profile.get(
                            "temperature",
                            runtime.SETTING_DEFAULTS["default_temperature"],
                        )
                    )
                except (TypeError, ValueError):
                    pass
                try:
                    runtime.character_engine.llm.default_max_tokens = int(
                        profile.get(
                            "max_tokens", runtime.SETTING_DEFAULTS["default_max_tokens"]
                        )
                    )
                except (TypeError, ValueError):
                    pass
                try:
                    runtime.character_engine.llm.short_temperature = float(
                        profile.get(
                            "short_temperature",
                            runtime.SETTING_DEFAULTS["short_temperature"],
                        )
                    )
                except (TypeError, ValueError):
                    pass
                try:
                    runtime.character_engine.llm.short_max_tokens = int(
                        profile.get(
                            "short_max_tokens",
                            runtime.SETTING_DEFAULTS["short_max_tokens"],
                        )
                    )
                except (TypeError, ValueError):
                    pass
            if "fallback" in purposes:
                runtime.character_engine.llm.fallback_model = item.id
                runtime.character_engine.llm.fallback_instruction = (
                    runtime.effective_project_prompt(
                        runtime.character_engine.RESPONSE_SYSTEM_PROMPT,
                        profile.get("response_instruction", ""),
                    )
                )
            if "fallback_2" in purposes:
                runtime.character_engine.llm.fallback_model_2 = item.id
            if "suggestion" in purposes:
                runtime.character_engine.ADMIN_SUGGESTION_INSTRUCTION = (
                    runtime.effective_project_prompt(
                        runtime.character_engine.SUGGESTION_SYSTEM_PROMPT,
                        profile.get("suggestion_instruction", ""),
                    )
                )
                runtime.character_engine.llm.purpose_models["suggestion"] = item.id
            if "suggestion_fallback" in purposes:
                runtime.character_engine.llm.purpose_models["suggestion_fallback"] = (
                    item.id
                )
            if "suggestion_fallback_2" in purposes:
                runtime.character_engine.llm.purpose_models["suggestion_fallback_2"] = (
                    item.id
                )
            if "compiler" in purposes:
                runtime.character_engine.ADMIN_COMPILER_INSTRUCTION = (
                    runtime.effective_project_prompt(
                        runtime.character_engine.CHARACTER_COMPILER_SYSTEM_PROMPT,
                        profile.get("compiler_instruction", ""),
                    )
                )
                runtime.character_engine.llm.purpose_models["compiler"] = item.id
            if "moderation" in purposes:
                runtime.os.environ["ADMIN_MODERATION_MODEL"] = item.model_id
                runtime.os.environ["ADMIN_MODERATION_API_BASE"] = item.api_base
                moderation_key = runtime.character_engine.llm.model_api_keys.get(
                    item.id, ""
                )
                if moderation_key:
                    runtime.os.environ["ADMIN_MODERATION_API_KEY"] = moderation_key
                runtime.os.environ["ADMIN_MODERATION_INSTRUCTION"] = (
                    runtime.effective_project_prompt(
                        runtime.MODERATION_SYSTEM_PROMPT,
                        profile.get("moderation_instruction", ""),
                    )
                )
            if "emotion" in purposes:
                runtime.character_engine.llm.purpose_models["emotion"] = item.id
                runtime.os.environ["ADMIN_EMOTION_INSTRUCTION"] = (
                    runtime.effective_project_prompt(
                        runtime.EMOTION_DETECTION_SYSTEM_PROMPT,
                        profile.get("emotion_instruction", ""),
                    )
                )
            if "emotion_fallback" in purposes:
                runtime.character_engine.llm.purpose_models["emotion_fallback"] = (
                    item.id
                )
                runtime.os.environ["ADMIN_EMOTION_FALLBACK_INSTRUCTION"] = (
                    runtime.effective_project_prompt(
                        runtime.EMOTION_DETECTION_SYSTEM_PROMPT,
                        profile.get("emotion_instruction", ""),
                    )
                )
            if "emotion_fallback_2" in purposes:
                runtime.character_engine.llm.purpose_models["emotion_fallback_2"] = (
                    item.id
                )

    runtime.apply_model_registry = apply_model_registry

    def apply_shared_credentials(db):
        """Use one encrypted AVIBI account key for every model unless a model overrides it."""
        row = db.get(runtime.AppSetting, "credential:avibi")
        if row and row.value:
            runtime.character_engine.llm.api_key = runtime.decrypt_admin_secret(
                row.value
            )
        else:
            runtime.character_engine.llm.api_key = (
                runtime.os.getenv("AIMP_API_KEY")
                or runtime.os.getenv("LLM_API_KEY")
                or runtime.os.getenv("OPENAI_API_KEY")
                or ""
            ).strip()

    runtime.apply_shared_credentials = apply_shared_credentials
