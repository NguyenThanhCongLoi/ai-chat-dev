"""api.admin_characters: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_admin_characters(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/v1/admin/characters")
    def admin_characters(
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        catalog = [
            {
                "id": "preset:" + (item.preset_type or item.id),
                "user_id": None,
                "source": "preset",
                "home_section": runtime.preset_home_section(db, item),
                "spec": item.model_dump(),
            }
            for item in runtime.effective_presets(db)
        ]
        publications = {
            item.character_id
            for item in db.query(runtime.CharacterPublication)
            .filter_by(is_public=1)
            .all()
        }
        clone_sources = {
            item.key.removeprefix("character_clone_source:"): item.value
            for item in db.query(runtime.AppSetting)
            .filter(runtime.AppSetting.key.like("character_clone_source:%"))
            .all()
        }
        rows = (
            db.query(runtime.Character)
            .order_by(runtime.Character.updated_at.desc())
            .all()
        )
        public_signatures = {}

        def copy_signature(item):
            # Legacy copies have no source link, but keep the source card and avatar version.
            avatar_match = runtime.re.search(
                r"[?&]v=([0-9a-f]{12})\b", item.avatar_url or ""
            )
            if not avatar_match:
                return None
            return (
                item.name.strip().casefold(),
                item.description.strip(),
                item.system_prompt.strip(),
                avatar_match.group(1),
            )

        for row in rows:
            if row.id in publications and row.id not in clone_sources:
                signature = copy_signature(runtime.spec(row))
                if signature:
                    public_signatures.setdefault(signature, row.id)

        def is_public_copy(character_id):
            seen = {character_id}
            source_id = clone_sources.get(character_id)
            while source_id and source_id not in seen:
                if source_id in publications:
                    return True
                seen.add(source_id)
                source_id = clone_sources.get(source_id)
            return False

        user_characters = []
        for row in rows:
            item = runtime.spec(row)
            signature = copy_signature(item)
            if (
                item.creation_type != "preset"
                and not is_public_copy(row.id)
                and (
                    not signature or public_signatures.get(signature, row.id) == row.id
                )
            ):
                user_characters.append(
                    {
                        "id": row.id,
                        "user_id": row.user_id,
                        "source": "user",
                        "is_public": row.id in publications,
                        "spec": item.model_dump(),
                    }
                )
        return {"preset_catalog": catalog, "user_characters": user_characters}

    runtime.admin_characters = admin_characters

    @runtime.app.post("/v1/admin/presets")
    def admin_create_preset(
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        name = str(data.get("name") or "").strip()
        if not name:
            raise runtime.HTTPException(400, "Character name is required")
        preset_type = "admin_" + runtime.uid().replace("-", "")[:12]
        category = (
            "entertainment" if data.get("category") == "entertainment" else "utility"
        )
        role = str(data.get("role") or "companion").strip()[:120]
        item = runtime.CharacterSpec(
            id="preset-" + preset_type,
            preset_type=preset_type,
            creation_type="preset",
            name=name,
            display_name=name,
            category=category,
            description=str(data.get("description") or "").strip(),
            avatar_url=str(data.get("avatar_url") or "").strip() or None,
            system_prompt=str(data.get("system_prompt") or "").strip(),
            initial_greeting=str(data.get("initial_greeting") or "").strip(),
            tts_voice_id=str(data.get("tts_voice_id") or "").strip(),
            tts_languages=data.get("tts_languages", {}),
            tts_voice_mode=str(data.get("tts_voice_mode") or "shared"),
            tts_voice_vi=str(data.get("tts_voice_vi") or "").strip(),
            tts_voice_en=str(data.get("tts_voice_en") or "").strip(),
            tts_voice_source=data.get("tts_voice_source", "auto"),
            tts_voice_source_vi=data.get("tts_voice_source_vi", "auto"),
            tts_voice_source_en=data.get("tts_voice_source_en", "auto"),
            tts_volume=data.get("tts_volume", 0.8),
            tts_gender=str(data.get("tts_gender") or "unspecified"),
            tts_emotion_enabled=bool(data.get("tts_emotion_enabled", True)),
            identity={"role": role},
            support={
                "primary_role": (
                    role
                    if role in {"study", "work", "health", "lifestyle", "companion"}
                    else "companion"
                ),
                "strengths": (
                    [role]
                    if role in {"study", "work", "health", "lifestyle", "companion"}
                    else ["companion"]
                ),
                "introduction": str(data.get("description") or "").strip()
                or f"Đồng hành cùng {name}.",
            },
        )
        if not item.system_prompt:
            item.system_prompt = (
                f"Roleplay consistently as {name}. Role: {role}. {item.description}"
            )
        runtime.enforce_character_policy(item)
        db.add(
            runtime.AppSetting(
                key="admin_preset:" + preset_type, value=item.model_dump_json()
            )
        )
        db.add(
            runtime.AppSetting(
                key="preset_home_section:" + preset_type,
                value="hidden" if category == "entertainment" else "auto",
            )
        )
        db.commit()
        return {
            "id": "preset:" + preset_type,
            "user_id": None,
            "source": "preset",
            "home_section": "hidden" if category == "entertainment" else "auto",
            "spec": item.model_dump(),
        }

    runtime.admin_create_preset = admin_create_preset

    @runtime.app.put("/v1/admin/presets/{preset_type}/avatar")
    def admin_upload_preset_avatar(
        preset_type: str,
        background: runtime.BackgroundTasks,
        file: runtime.UploadFile = runtime.File(...),
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        item = next(
            (
                value
                for value in runtime.effective_presets(db)
                if value.preset_type == preset_type
            ),
            None,
        )
        if not item:
            raise runtime.HTTPException(404, "Preset not found")
        mime = (file.content_type or "").lower()
        content = file.file.read(5 * 1024 * 1024 + 1)
        if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            raise runtime.HTTPException(400, "Chỉ hỗ trợ JPG, PNG, WEBP hoặc GIF")
        if len(content) > 5 * 1024 * 1024:
            raise runtime.HTTPException(413, "Ảnh không được vượt quá 5 MB")
        try:
            card_content, card_mime = runtime.optimize_card_avatar(content)
        except Exception as exc:
            raise runtime.HTTPException(400, f"Ảnh không hợp lệ: {exc}")
        version = runtime.hashlib.sha256(card_content).hexdigest()[:12]
        asset_key = "preset_asset:" + preset_type
        asset_value = runtime.json.dumps(
            {
                "mime_type": card_mime,
                "content": runtime.base64.b64encode(card_content).decode("ascii"),
            }
        )
        asset = db.get(runtime.AppSetting, asset_key)
        if asset:
            asset.value = asset_value
            asset.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=asset_key, value=asset_value))
        item.avatar_url = f"/v1/system-characters/{preset_type}/avatar?v={version}"
        override_key = "preset_override:" + preset_type
        override = db.get(runtime.AppSetting, override_key)
        source = db.get(runtime.AppSetting, "admin_preset:" + preset_type)
        active = override or source
        if active:
            active.value = item.model_dump_json()
            active.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=override_key, value=item.model_dump_json()))
        for character in db.query(runtime.Character).all():
            current = runtime.spec(character)
            if current.preset_type != preset_type or db.get(
                runtime.CharacterAsset, character.id
            ):
                continue
            current.avatar_url = item.avatar_url
            character.spec = current.model_dump_json()
            character.updated_at = runtime.now()
        db.commit()
        preset_source = "__preset__:" + preset_type
        db.query(runtime.CharacterExpressionAsset).filter_by(
            character_id=preset_source
        ).delete()
        source_version = db.get(
            runtime.AppSetting, "avatar_expression_version:" + preset_source
        )
        if source_version:
            source_version.value = "queued"
            source_version.updated_at = runtime.now()
        else:
            db.add(
                runtime.AppSetting(
                    key="avatar_expression_version:" + preset_source, value="queued"
                )
            )
        old_error = db.get(
            runtime.AppSetting, "avatar_expression_error:" + preset_source
        )
        if old_error:
            db.delete(old_error)
        character_ids = [
            row.id
            for row in db.query(runtime.Character).all()
            if runtime.spec(row).preset_type == preset_type
            and not db.get(runtime.CharacterAsset, row.id)
        ]
        for character_id in character_ids:
            db.query(runtime.CharacterExpressionAsset).filter_by(
                character_id=character_id
            ).delete()
            runtime.set_expression_alias(db, character_id, preset_source)
            child_version = db.get(
                runtime.AppSetting, "avatar_expression_version:" + character_id
            )
            if child_version:
                child_version.value = "queued"
                child_version.updated_at = runtime.now()
            else:
                db.add(
                    runtime.AppSetting(
                        key="avatar_expression_version:" + character_id, value="queued"
                    )
                )
        db.commit()
        background.add_task(
            runtime.generate_character_expressions, preset_source, content
        )
        return {
            "avatar_url": item.avatar_url,
            "expression_status": "queued",
            "characters_queued": len(character_ids),
            "images_queued": len(runtime.EMOTIONS),
        }

    runtime.admin_upload_preset_avatar = admin_upload_preset_avatar

    @runtime.app.get("/v1/system-characters/{preset_type}/avatar")
    def system_character_avatar(
        preset_type: str, db: runtime.DBSession = runtime.Depends(runtime.db_session)
    ):
        row = db.get(runtime.AppSetting, "preset_asset:" + preset_type)
        if not row:
            raise runtime.HTTPException(404, "Avatar not found")
        try:
            data = runtime.json.loads(row.value)
            content = runtime.base64.b64decode(data["content"])
        except Exception:
            raise runtime.HTTPException(404, "Avatar not found")
        etag = '"' + runtime.hashlib.sha256(content).hexdigest() + '"'
        return runtime.Response(
            content=content,
            media_type=data.get("mime_type") or "image/jpeg",
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "ETag": etag,
            },
        )

    runtime.system_character_avatar = system_character_avatar

    @runtime.app.put("/v1/admin/presets/{preset_type}/home-section")
    def admin_preset_home_section(
        preset_type: str,
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        template = next(
            (
                item
                for item in runtime.effective_presets(db)
                if item.preset_type == preset_type
            ),
            None,
        )
        if not template:
            raise runtime.HTTPException(404, "Preset not found")
        section = str(data.get("home_section") or "auto")
        if section not in {"auto", "featured", "popular", "top_rated", "hidden"}:
            raise runtime.HTTPException(400, "Invalid home section")
        key = "preset_home_section:" + preset_type
        row = db.get(runtime.AppSetting, key)
        if row:
            row.value = section
            row.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=key, value=section))
        db.commit()
        return {"preset_type": preset_type, "home_section": section}

    runtime.admin_preset_home_section = admin_preset_home_section

    @runtime.app.put("/v1/admin/presets/{preset_type}")
    def admin_update_preset(
        preset_type: str,
        changes: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        template = next(
            (
                item
                for item in runtime.effective_presets(db)
                if item.preset_type == preset_type
            ),
            None,
        )
        if not template:
            raise runtime.HTTPException(404, "Preset not found")
        allowed = {
            "name",
            "display_name",
            "description",
            "identity",
            "personality",
            "speech",
            "support",
            "system_prompt",
            "scenario",
            "initial_greeting",
            "sample_dialogues",
            "goals",
            "behavior_rules",
            "persona_knowledge",
            "tts_voice_id",
            "tts_gender",
            "tts_emotion_enabled",
            "tts_voice_mode",
            "tts_languages",
            "tts_voice_vi",
            "tts_voice_en",
            "tts_volume",
            "tts_voice_source",
            "tts_voice_source_vi",
            "tts_voice_source_en",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise runtime.HTTPException(
                400, "Unsupported preset fields: " + ", ".join(sorted(unknown))
            )
        data = template.model_dump()
        data.update(changes)
        try:
            updated = runtime.CharacterSpec.model_validate(data)
        except Exception as exc:
            raise runtime.HTTPException(400, str(exc))
        runtime.enforce_character_policy(updated, previous=template)
        updated.id = "preset-" + preset_type
        updated.preset_type = preset_type
        updated.creation_type = "preset"
        key = "preset_override:" + preset_type
        row = db.get(runtime.AppSetting, key)
        if row:
            row.value = updated.model_dump_json()
            row.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=key, value=updated.model_dump_json()))
        synced = 0
        for character in db.query(runtime.Character).all():
            current = runtime.spec(character)
            if current.creation_type == "preset" and current.preset_type == preset_type:
                copy = updated.model_copy(deep=True)
                copy.id = character.id
                character.name = copy.name
                character.spec = copy.model_dump_json()
                character.updated_at = runtime.now()
                db.add(
                    runtime.CharacterVersion(
                        id=runtime.uid(), character_id=character.id, spec=character.spec
                    )
                )
                synced += 1
        db.commit()
        return {
            "id": "preset:" + preset_type,
            "user_id": None,
            "source": "preset",
            "synced_characters": synced,
            "spec": updated.model_dump(),
        }

    runtime.admin_update_preset = admin_update_preset

    @runtime.app.put("/v1/admin/characters/{character_id}")
    def admin_update_character(
        character_id: str,
        changes: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        row = db.get(runtime.Character, character_id)
        if not row:
            raise runtime.HTTPException(404, "Character not found")
        allowed = {
            "name",
            "display_name",
            "description",
            "identity",
            "personality",
            "speech",
            "support",
            "system_prompt",
            "scenario",
            "initial_greeting",
            "sample_dialogues",
            "goals",
            "behavior_rules",
            "persona_knowledge",
            "tts_voice_id",
            "tts_gender",
            "tts_emotion_enabled",
            "tts_voice_mode",
            "tts_languages",
            "tts_voice_vi",
            "tts_voice_en",
            "tts_volume",
            "tts_voice_source",
            "tts_voice_source_vi",
            "tts_voice_source_en",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise runtime.HTTPException(
                400, "Unsupported character fields: " + ", ".join(sorted(unknown))
            )
        data = runtime.spec(row).model_dump()
        for key, value in changes.items():
            data[key] = value
        try:
            updated = runtime.CharacterSpec.model_validate(data)
        except Exception as exc:
            raise runtime.HTTPException(400, str(exc))
        runtime.enforce_character_policy(updated, previous=runtime.spec(row))
        row.name = updated.name
        row.spec = updated.model_dump_json()
        row.updated_at = runtime.now()
        override_key = "character_override:" + row.id
        override = db.get(runtime.AppSetting, override_key)
        if override:
            override.value = row.spec
            override.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=override_key, value=row.spec))
        db.add(
            runtime.CharacterVersion(
                id=runtime.uid(), character_id=row.id, spec=row.spec
            )
        )
        db.commit()
        return {"id": row.id, "user_id": row.user_id, "spec": updated.model_dump()}

    runtime.admin_update_character = admin_update_character

    @runtime.app.put("/v1/admin/characters/{character_id}/avatar")
    def admin_upload_character_avatar(
        character_id: str,
        background: runtime.BackgroundTasks,
        file: runtime.UploadFile = runtime.File(...),
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        row = db.get(runtime.Character, character_id)
        if not row:
            raise runtime.HTTPException(404, "Character not found")
        mime = (file.content_type or "").lower()
        content = file.file.read(5 * 1024 * 1024 + 1)
        if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            raise runtime.HTTPException(400, "Chỉ hỗ trợ JPG, PNG, WEBP hoặc GIF")
        if len(content) > 5 * 1024 * 1024:
            raise runtime.HTTPException(413, "Ảnh không được vượt quá 5 MB")
        try:
            card_content, card_mime = runtime.optimize_card_avatar(content)
        except Exception as exc:
            raise runtime.HTTPException(400, f"Ảnh không hợp lệ: {exc}")
        asset = db.get(runtime.CharacterAsset, character_id)
        if asset:
            asset.mime_type = card_mime
            asset.content = card_content
            asset.updated_at = runtime.now()
        else:
            db.add(
                runtime.CharacterAsset(
                    character_id=character_id, mime_type=card_mime, content=card_content
                )
            )
        card_version = runtime.hashlib.sha256(card_content).hexdigest()[:12]
        item = runtime.spec(row)
        item.avatar_url = (
            f"/v1/public/characters/{character_id}/avatar?v={card_version}"
        )
        row.spec = item.model_dump_json()
        row.updated_at = runtime.now()
        db.query(runtime.CharacterExpressionAsset).filter_by(
            character_id=character_id
        ).delete()
        version = db.get(
            runtime.AppSetting, "avatar_expression_version:" + character_id
        )
        if version:
            db.delete(version)
        db.commit()
        background.add_task(
            runtime.generate_character_expressions, character_id, content
        )
        return {"avatar_url": item.avatar_url, "expression_status": "processing"}

    runtime.admin_upload_character_avatar = admin_upload_character_avatar

    def admin_expression_character(identifier, db):
        row = db.get(runtime.Character, identifier)
        if row:
            return row
        preset_type = identifier.removeprefix("preset:").removeprefix("preset-")
        for candidate in (
            db.query(runtime.Character)
            .order_by(runtime.Character.updated_at.desc())
            .all()
        ):
            if runtime.spec(candidate).preset_type == preset_type:
                return candidate
        raise runtime.HTTPException(404, "Character expression set not found")

    runtime.admin_expression_character = admin_expression_character

    @runtime.app.get("/v1/admin/characters/{identifier}/expressions")
    def admin_character_expressions(
        identifier: str,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        preset_type = identifier.removeprefix("preset:").removeprefix("preset-")
        if identifier.startswith("preset:") and any(
            item.preset_type == preset_type for item in runtime.effective_presets(db)
        ):
            template = next(
                item
                for item in runtime.effective_presets(db)
                if item.preset_type == preset_type
            )
            source_id = (
                runtime.ensure_bundled_expressions(db, template)
                or "__preset__:" + preset_type
            )
            version = db.get(
                runtime.AppSetting, "avatar_expression_version:" + source_id
            )
        else:
            row = runtime.admin_expression_character(identifier, db)
            source_id = runtime.expression_source_id(db, row)
            version = db.get(
                runtime.AppSetting, "avatar_expression_version:" + source_id
            ) or db.get(runtime.AppSetting, "avatar_expression_version:" + row.id)
        assets = (
            db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id=source_id)
            .all()
        )
        available = {asset.emotion for asset in assets}
        quality = version.value if version else "missing"
        status = (
            "ready"
            if set(runtime.EMOTIONS).issubset(available)
            else (
                quality
                if quality in {"queued", "processing", "failed", "no-image-model"}
                else "missing"
            )
        )
        error = db.get(runtime.AppSetting, "avatar_expression_error:" + source_id)
        return {
            "character_id": source_id,
            "status": status,
            "quality": quality,
            "error": error.value if error else "",
            "images": {
                emotion: f"/v1/admin/characters/{source_id}/expressions/{emotion}/image"
                for emotion in sorted(available)
            },
        }

    runtime.admin_character_expressions = admin_character_expressions

    @runtime.app.post("/v1/admin/system-characters/expressions/backfill")
    def admin_backfill_system_expressions(
        background: runtime.BackgroundTasks,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        assigned = any(
            "avatar_image" in runtime.model_profile(db, model).get("purposes", [])
            for model in db.query(runtime.ModelConfig).filter_by(enabled=1).all()
        )
        if not assigned:
            raise runtime.HTTPException(
                400, "Hãy gắn một model cho tác vụ Tạo avatar biểu cảm trong CMS"
            )
        pending = []
        for preset in runtime.effective_presets(db):
            source_id = "__preset__:" + preset.preset_type
            available = {
                asset.emotion
                for asset in db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=source_id)
                .all()
            }
            version = db.get(
                runtime.AppSetting, "avatar_expression_version:" + source_id
            )
            if (
                set(runtime.EMOTIONS).issubset(available)
                and version
                and version.value == runtime.EXPRESSION_VERSION
            ) or (version and version.value in {"queued", "processing"}):
                continue
            content = runtime.preset_source_image(db, preset)
            if not content:
                continue
            pending.append((source_id, content))
            db.query(runtime.CharacterExpressionAsset).filter_by(
                character_id=source_id
            ).delete()
            if version:
                version.value = "queued"
                version.updated_at = runtime.now()
            else:
                db.add(
                    runtime.AppSetting(
                        key="avatar_expression_version:" + source_id, value="queued"
                    )
                )
        db.commit()
        for source_id, content in pending:
            background.add_task(
                runtime.generate_character_expressions, source_id, content
            )
        return {
            "characters_queued": len(pending),
            "images_queued": len(pending) * len(runtime.EMOTIONS),
        }

    runtime.admin_backfill_system_expressions = admin_backfill_system_expressions

    @runtime.app.get("/v1/admin/characters/{character_id}/expressions/{emotion}/image")
    def admin_character_expression_image(
        character_id: str,
        emotion: str,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        asset = (
            db.query(runtime.CharacterExpressionAsset)
            .filter_by(
                character_id=character_id,
                emotion=(
                    emotion
                    if emotion
                    in {"laughing", "crying", "winking", "playful", "thinking"}
                    else runtime.normalized_expression(emotion)
                ),
            )
            .first()
        )
        if not asset:
            raise runtime.HTTPException(404, "Expression image not found")
        return runtime.Response(
            asset.content,
            media_type=asset.mime_type,
            headers={"Cache-Control": "no-store"},
        )

    runtime.admin_character_expression_image = admin_character_expression_image
