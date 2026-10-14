"""services.expressions: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_generate_character_expressions(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def generate_character_expressions(character_id, content):
        # The minimum server must preserve migrated art, even when CMS has an image model.
        if runtime.os.getenv("AVATAR_GENERATOR_MODE", "default").strip().lower() == "default":
            with runtime.Session() as db:
                if not db.query(runtime.CharacterExpressionAsset).filter_by(character_id=character_id).count():
                    runtime.install_default_expressions(db, character_id)
            return
        try:
            with runtime.Session() as status_db:
                version = status_db.get(
                    runtime.AppSetting, "avatar_expression_version:" + character_id
                )
                count = (
                    status_db.query(runtime.CharacterExpressionAsset)
                    .filter_by(character_id=character_id)
                    .count()
                )
                if (
                    version
                    and version.value == runtime.EXPRESSION_VERSION
                    and count >= 6
                ):
                    return
                if version and version.value == "processing":
                    return
                if version:
                    version.value = "processing"
                    version.updated_at = runtime.now()
                else:
                    status_db.add(
                        runtime.AppSetting(
                            key="avatar_expression_version:" + character_id,
                            value="processing",
                        )
                    )
                status_db.commit()
            variants = None
            generated = False
            generation_error = ""
            image_model = ""
            image_base = runtime.os.getenv(
                "LLM_API_BASE", "https://gateway.avibi.ai/v1"
            )
            image_key = ""
            image_model_assigned = False
            with runtime.Session() as config_db:
                for model in (
                    config_db.query(runtime.ModelConfig).filter_by(enabled=1).all()
                ):
                    if "avatar_image" in runtime.model_profile(config_db, model).get(
                        "purposes", []
                    ):
                        image_model_assigned = True
                        image_model = model.model_id
                        image_base = model.api_base or image_base
                        try:
                            image_key = runtime.credential_for_model(config_db, model)
                        except runtime.HTTPException as exc:
                            generation_error = str(exc.detail)
                        break
            if not image_model_assigned:
                with runtime.Session() as db:
                    if character_id.startswith("__preset__:"):
                        db.query(runtime.CharacterExpressionAsset).filter_by(
                            character_id=character_id
                        ).delete()
                        version = db.get(
                            runtime.AppSetting,
                            "avatar_expression_version:" + character_id,
                        )
                        if version:
                            version.value = "no-image-model"
                            version.updated_at = runtime.now()
                        for alias in (
                            db.query(runtime.AppSetting)
                            .filter(
                                runtime.AppSetting.key.like("expression_source:%"),
                                runtime.AppSetting.value == character_id,
                            )
                            .all()
                        ):
                            child_version = db.get(
                                runtime.AppSetting,
                                "avatar_expression_version:"
                                + alias.key.removeprefix("expression_source:"),
                            )
                            if child_version:
                                child_version.value = "no-image-model"
                                child_version.updated_at = runtime.now()
                    else:
                        runtime.install_default_expressions(db, character_id)
                    db.commit()
                return
            if not image_key:
                generation_error = (
                    generation_error or f"Chưa cấu hình API key cho {image_base}"
                )
            # Run the existing image pipeline on this host; never dispatch to Modal.
            # default mode intentionally keeps bundled/user images without paid generation.
            if image_key and runtime.os.getenv("AVATAR_GENERATOR_MODE", "default").strip().lower() == "direct":
                try:
                    from character_chat.avatar_pipeline import build_ai_expression_variants
                    variants = build_ai_expression_variants(content, image_model, image_base, image_key)
                    generated = True
                except Exception as exc:
                    generation_error = str(exc)[:500]
            elif character_id.startswith("__preset__:"):
                generation_error = "Image generation is disabled; use existing or default images"
            if character_id.startswith("__preset__:") and (
                not generated
                or not isinstance(variants, dict)
                or not set(runtime.EMOTIONS).issubset(variants)
            ):
                with runtime.Session() as db:
                    db.query(runtime.CharacterExpressionAsset).filter_by(
                        character_id=character_id
                    ).delete()
                    version = db.get(
                        runtime.AppSetting, "avatar_expression_version:" + character_id
                    )
                    if version:
                        version.value = "failed"
                        version.updated_at = runtime.now()
                    error_key = "avatar_expression_error:" + character_id
                    error = db.get(runtime.AppSetting, error_key)
                    if error:
                        error.value = (
                            generation_error or "Model ảnh không tạo được bộ biểu cảm"
                        )
                        error.updated_at = runtime.now()
                    else:
                        db.add(
                            runtime.AppSetting(
                                key=error_key,
                                value=generation_error
                                or "Model ảnh không tạo được bộ biểu cảm",
                            )
                        )
                    for alias in (
                        db.query(runtime.AppSetting)
                        .filter(
                            runtime.AppSetting.key.like("expression_source:%"),
                            runtime.AppSetting.value == character_id,
                        )
                        .all()
                    ):
                        child_version = db.get(
                            runtime.AppSetting,
                            "avatar_expression_version:"
                            + alias.key.removeprefix("expression_source:"),
                        )
                        if child_version:
                            child_version.value = "failed"
                            child_version.updated_at = runtime.now()
                    db.commit()
                return
            if not variants:
                variants = runtime.build_expression_variants(content)
            with runtime.Session() as db:
                db.query(runtime.CharacterExpressionAsset).filter_by(
                    character_id=character_id
                ).delete()
                alias = db.get(runtime.AppSetting, "expression_source:" + character_id)
                if alias:
                    db.delete(alias)
                for emotion, image in variants.items():
                    db.add(
                        runtime.CharacterExpressionAsset(
                            id=runtime.uid(),
                            character_id=character_id,
                            emotion=emotion,
                            mime_type="image/png",
                            content=image,
                        )
                    )
                key = "avatar_expression_version:" + character_id
                version = db.get(runtime.AppSetting, key)
                saved_version = runtime.EXPRESSION_VERSION if generated else "fallback"
                if version:
                    version.value = saved_version
                    version.updated_at = runtime.now()
                else:
                    db.add(runtime.AppSetting(key=key, value=saved_version))
                error = db.get(
                    runtime.AppSetting, "avatar_expression_error:" + character_id
                )
                if error:
                    db.delete(error)
                if character_id.startswith("__preset__:"):
                    for alias in (
                        db.query(runtime.AppSetting)
                        .filter(
                            runtime.AppSetting.key.like("expression_source:%"),
                            runtime.AppSetting.value == character_id,
                        )
                        .all()
                    ):
                        child_id = alias.key.removeprefix("expression_source:")
                        child_version = db.get(
                            runtime.AppSetting, "avatar_expression_version:" + child_id
                        )
                        if child_version:
                            child_version.value = saved_version
                            child_version.updated_at = runtime.now()
                if not character_id.startswith("__preset__:"):
                    runtime.register_expression_identity(db, character_id)
                    runtime.register_expression_image(db, character_id)
                db.commit()
        except Exception:
            try:
                with runtime.Session() as failed_db:
                    version = failed_db.get(
                        runtime.AppSetting, "avatar_expression_version:" + character_id
                    )
                    if version and version.value == "processing":
                        version.value = "failed"
                        version.updated_at = runtime.now()
                        if character_id.startswith("__preset__:"):
                            for alias in (
                                failed_db.query(runtime.AppSetting)
                                .filter(
                                    runtime.AppSetting.key.like("expression_source:%"),
                                    runtime.AppSetting.value == character_id,
                                )
                                .all()
                            ):
                                child_version = failed_db.get(
                                    runtime.AppSetting,
                                    "avatar_expression_version:"
                                    + alias.key.removeprefix("expression_source:"),
                                )
                                if child_version:
                                    child_version.value = "failed"
                                    child_version.updated_at = runtime.now()
                        failed_db.commit()
            except Exception:
                pass
            return

    runtime.generate_character_expressions = generate_character_expressions

    def install_default_expressions(db, character_id):
        db.query(runtime.CharacterExpressionAsset).filter_by(
            character_id=character_id
        ).delete()
        if (
            db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id="__default__")
            .count()
            < 6
        ):
            db.query(runtime.CharacterExpressionAsset).filter_by(
                character_id="__default__"
            ).delete()
            for emotion, image in runtime.default_expression_variants().items():
                db.add(
                    runtime.CharacterExpressionAsset(
                        id=runtime.uid(),
                        character_id="__default__",
                        emotion=emotion,
                        mime_type="image/png",
                        content=image,
                    )
                )
        row = db.get(runtime.Character, character_id)
        if row:
            item = runtime.spec(row)
            if not item.avatar_url:
                item.avatar_url = "/character-images/default_icons/neutral.png"
                row.spec = item.model_dump_json()
                row.updated_at = runtime.now()
        key = "avatar_expression_version:" + character_id
        version = db.get(runtime.AppSetting, key)
        if version:
            version.value = "default-icons"
            version.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=key, value="default-icons"))
        db.commit()

    runtime.install_default_expressions = install_default_expressions

    def resolve_expression_asset_source(db, source_id):
        """Follow shared-expression aliases until reaching the cached image owner."""
        seen = set()
        for _ in range(12):
            if not source_id or source_id in seen:
                return None
            seen.add(source_id)
            if (
                db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=source_id)
                .count()
            ):
                return source_id
            alias = db.get(runtime.AppSetting, "expression_source:" + source_id)
            if not alias or not alias.value:
                return None
            source_id = alias.value
        return None

    runtime.resolve_expression_asset_source = resolve_expression_asset_source

    def expression_source_id(db, character):
        item = runtime.spec(character)
        bundled = runtime.ensure_bundled_expressions(db, item)
        if bundled:
            return bundled
        if item.preset_type and not db.get(runtime.CharacterAsset, character.id):
            preset_source = "__preset__:" + item.preset_type
            if (
                db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=preset_source)
                .count()
            ):
                return preset_source
        resolved = runtime.resolve_expression_asset_source(db, character.id)
        if resolved and resolved != "__default__":
            return resolved
        if item.preset_type:
            candidates = []
            for sibling in db.query(runtime.Character).all():
                if runtime.spec(sibling).preset_type == item.preset_type:
                    source = runtime.resolve_expression_asset_source(db, sibling.id)
                    if source:
                        candidates.append(source)
            if candidates:
                return next(
                    (source for source in candidates if source != "__default__"),
                    candidates[0],
                )
        if resolved:
            return resolved
        return "__default__"

    runtime.expression_source_id = expression_source_id

    def expression_backfill_plan(db):
        """Estimate model work without counting default icons or duplicate avatars."""
        unique_sources = {}
        characters = 0
        for preset in runtime.effective_presets(db):
            if runtime.ensure_bundled_expressions(db, preset):
                continue
            content = runtime.preset_source_image(db, preset)
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
                content
                and not (
                    set(runtime.EMOTIONS).issubset(available)
                    and version
                    and version.value == runtime.EXPRESSION_VERSION
                )
                and not (version and version.value in {"queued", "processing"})
            ):
                characters += 1
                unique_sources[runtime.hashlib.sha256(content).hexdigest()] = True
        for row in db.query(runtime.Character).all():
            source_id = runtime.expression_source_id(db, row)
            available = {
                asset.emotion
                for asset in db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=source_id)
                .all()
            }
            if set(runtime.EMOTIONS).issubset(available):
                continue
            content = runtime.character_source_image(db, row)
            if not content:
                continue
            characters += 1
            unique_sources[runtime.hashlib.sha256(content).hexdigest()] = True
        source_count = len(unique_sources)
        return {
            "characters": characters,
            "unique_sources": source_count,
            "images": source_count * len(runtime.EMOTIONS),
        }

    runtime.expression_backfill_plan = expression_backfill_plan

    def preset_source_image(db, preset):
        stored = db.get(runtime.AppSetting, "preset_asset:" + preset.preset_type)
        if stored:
            try:
                return runtime.base64.b64decode(
                    runtime.json.loads(stored.value)["content"]
                )
            except Exception:
                return None
        url = preset.avatar_url or ""
        prefix = "/character-images/"
        if not url.startswith(prefix) or url.startswith(prefix + "default_icons/"):
            return None
        try:
            from urllib.parse import unquote

            root = runtime.Path(
                runtime.os.getenv("CHARACTER_IMAGE_DIR", "image")
            ).resolve()
            path = (root / unquote(url.removeprefix(prefix))).resolve()
            if path.is_file() and root in path.parents:
                return path.read_bytes()
        except Exception:
            pass
        return None

    runtime.preset_source_image = preset_source_image

    def backfill_system_preset_expressions():
        with runtime.Session() as db:
            pending = []
            for preset in runtime.effective_presets(db):
                if runtime.ensure_bundled_expressions(db, preset):
                    continue
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
                if content:
                    pending.append((source_id, content))
        for source_id, content in pending:
            runtime.generate_character_expressions(source_id, content)

    runtime.backfill_system_preset_expressions = backfill_system_preset_expressions

    def deduplicate_expression_assets(db):
        """Keep one cached set per preset or identical image set."""
        rows = db.query(runtime.Character).all()
        preset_groups = {}
        for row in rows:
            preset_type = runtime.spec(row).preset_type
            if preset_type:
                preset_groups.setdefault(preset_type, []).append(row)
        for preset_type, members in preset_groups.items():
            preset_source = "__preset__:" + preset_type
            if (
                db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=preset_source)
                .count()
                >= 6
            ):
                for row in members:
                    db.query(runtime.CharacterExpressionAsset).filter_by(
                        character_id=row.id
                    ).delete()
                    runtime.set_expression_alias(db, row.id, preset_source)
                continue
            owners = [
                row
                for row in members
                if db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=row.id)
                .count()
                >= 6
            ]
            if not owners:
                continue
            owner = owners[0]
            for candidate in owners:
                version = db.get(
                    runtime.AppSetting, "avatar_expression_version:" + candidate.id
                )
                if version and version.value == runtime.EXPRESSION_VERSION:
                    owner = candidate
                    break
            for row in members:
                if row.id != owner.id:
                    db.query(runtime.CharacterExpressionAsset).filter_by(
                        character_id=row.id
                    ).delete()
                key = "expression_source:" + row.id
                alias = db.get(runtime.AppSetting, key)
                if alias:
                    alias.value = owner.id
                    alias.updated_at = runtime.now()
                else:
                    db.add(runtime.AppSetting(key=key, value=owner.id))
        # Default icon users all reference one global six-image set.
        for row in rows:
            version = db.get(runtime.AppSetting, "avatar_expression_version:" + row.id)
            if version and version.value == "default-icons":
                db.query(runtime.CharacterExpressionAsset).filter_by(
                    character_id=row.id
                ).delete()
                runtime.set_expression_alias(db, row.id, "__default__")
        if (
            db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id="__default__")
            .count()
            < 6
        ):
            db.query(runtime.CharacterExpressionAsset).filter_by(
                character_id="__default__"
            ).delete()
            for emotion, image in runtime.default_expression_variants().items():
                db.add(
                    runtime.CharacterExpressionAsset(
                        id=runtime.uid(),
                        character_id="__default__",
                        emotion=emotion,
                        mime_type="image/png",
                        content=image,
                    )
                )
        # Share byte-identical custom sets, including public clones made by older builds.
        signatures = {}
        for row in rows:
            assets = (
                db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=row.id)
                .order_by(runtime.CharacterExpressionAsset.emotion)
                .all()
            )
            if len(assets) < 6:
                continue
            signature = runtime.hashlib.sha256(
                b"".join(asset.emotion.encode() + asset.content for asset in assets)
            ).hexdigest()
            owner = signatures.setdefault(signature, row.id)
            if owner != row.id:
                db.query(runtime.CharacterExpressionAsset).filter_by(
                    character_id=row.id
                ).delete()
                key = "expression_source:" + row.id
                alias = db.get(runtime.AppSetting, key)
                if alias:
                    alias.value = owner
                    alias.updated_at = runtime.now()
                else:
                    db.add(runtime.AppSetting(key=key, value=owner))
        # Media identities live independently from user-owned Character rows so
        # deleting the first creator never removes the shared expression source.
        for registry in (
            db.query(runtime.AppSetting)
            .filter(runtime.AppSetting.key.like("expression_identity_owner:%"))
            .all()
        ):
            identity = registry.key.removeprefix("expression_identity_owner:")
            stable_id = "__identity__:" + identity
            if registry.value == stable_id:
                continue
            assets = (
                db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=registry.value)
                .all()
            )
            if len(assets) < 6:
                continue
            db.query(runtime.CharacterExpressionAsset).filter_by(
                character_id=stable_id
            ).delete()
            for asset in assets:
                db.add(
                    runtime.CharacterExpressionAsset(
                        id=runtime.uid(),
                        character_id=stable_id,
                        emotion=asset.emotion,
                        mime_type=asset.mime_type,
                        content=asset.content,
                    )
                )
            old_owner = registry.value
            registry.value = stable_id
            registry.updated_at = runtime.now()
            for alias in (
                db.query(runtime.AppSetting)
                .filter(
                    runtime.AppSetting.key.like("expression_source:%"),
                    runtime.AppSetting.value == old_owner,
                )
                .all()
            ):
                alias.value = stable_id
                alias.updated_at = runtime.now()
            owner_character = db.get(runtime.Character, old_owner)
            if owner_character:
                runtime.set_expression_alias(db, old_owner, stable_id)
                db.query(runtime.CharacterExpressionAsset).filter_by(
                    character_id=old_owner
                ).delete()
        db.commit()

    runtime.deduplicate_expression_assets = deduplicate_expression_assets

    def backfill_character_expressions(target_name="", max_groups=None):
        """Build the cached portrait set once for characters created before this feature."""
        lock_path = (
            runtime.Path(runtime.os.getenv("DATA_DIR", "."))
            / ".avatar-expression-backfill.lock"
        )
        lock_fd = None
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                lock_fd = runtime.os.open(
                    lock_path,
                    runtime.os.O_CREAT | runtime.os.O_EXCL | runtime.os.O_WRONLY,
                )
            except FileExistsError:
                if runtime.time.time() - lock_path.stat().st_mtime < 300:
                    return
                lock_path.unlink(missing_ok=True)
                lock_fd = runtime.os.open(
                    lock_path,
                    runtime.os.O_CREAT | runtime.os.O_EXCL | runtime.os.O_WRONLY,
                )
            runtime.backfill_system_preset_expressions()
            with runtime.Session() as db:
                groups = {}
                rows = db.query(runtime.Character).all()
                rows.sort(
                    key=lambda row: (
                        row.name.casefold() != (target_name or "Duy").casefold(),
                        row.name.casefold(),
                    )
                )
                for row in rows:
                    if target_name and row.name.casefold() != target_name.casefold():
                        continue
                    source_id = runtime.expression_source_id(db, row)
                    available = {
                        asset.emotion
                        for asset in db.query(runtime.CharacterExpressionAsset)
                        .filter_by(character_id=source_id)
                        .all()
                    }
                    # An explicit target is a deliberate regeneration request. It
                    # may replace a complete default-icon set with an AI set built
                    # from that character's real avatar.
                    if not target_name and set(runtime.EMOTIONS).issubset(available):
                        continue
                    content = runtime.character_source_image(db, row)
                    if content:
                        # One job per unique source image, even when many users
                        # created the same character or share the same avatar.
                        groups.setdefault(
                            runtime.hashlib.sha256(content).hexdigest(),
                            {"content": content, "ids": []},
                        )["ids"].append(row.id)
                    else:
                        # No real avatar means no image-model call. Keep the common
                        # default icon set so the chat UI still has six emotions.
                        runtime.install_default_expressions(db, row.id)
            selected = (
                list(groups.values())[:max_groups]
                if max_groups
                else list(groups.values())
            )
            for group in selected:
                source_id = group["ids"][0]
                runtime.generate_character_expressions(source_id, group["content"])
                with runtime.Session() as db:
                    source_assets = (
                        db.query(runtime.CharacterExpressionAsset)
                        .filter_by(character_id=source_id)
                        .all()
                    )
                    source_version = db.get(
                        runtime.AppSetting, "avatar_expression_version:" + source_id
                    )
                    for character_id in group["ids"][1:]:
                        db.query(runtime.CharacterExpressionAsset).filter_by(
                            character_id=character_id
                        ).delete()
                        for asset in source_assets:
                            db.add(
                                runtime.CharacterExpressionAsset(
                                    id=runtime.uid(),
                                    character_id=character_id,
                                    emotion=asset.emotion,
                                    mime_type=asset.mime_type,
                                    content=asset.content,
                                )
                            )
                        key = "avatar_expression_version:" + character_id
                        version = db.get(runtime.AppSetting, key)
                        value = source_version.value if source_version else "fallback"
                        if version:
                            version.value = value
                            version.updated_at = runtime.now()
                        else:
                            db.add(runtime.AppSetting(key=key, value=value))
                    db.commit()
            with runtime.Session() as db:
                runtime.deduplicate_expression_assets(db)
        except Exception:
            return
        finally:
            if lock_fd is not None:
                try:
                    runtime.os.close(lock_fd)
                except Exception:
                    pass
                try:
                    lock_path.unlink(missing_ok=True)
                except Exception:
                    pass

    runtime.backfill_character_expressions = backfill_character_expressions

    def regenerate_character_expression_set(character_id):
        """Force one exact character to rebuild from its real source avatar."""
        with runtime.Session() as db:
            row = db.get(runtime.Character, character_id)
            if not row:
                return {"character_id": character_id, "status": "not_found"}
            content = runtime.character_source_image(db, row)
            if not content:
                return {"character_id": character_id, "status": "no_source_avatar"}
            db.query(runtime.CharacterExpressionAsset).filter_by(
                character_id=character_id
            ).delete()
            alias = db.get(runtime.AppSetting, "expression_source:" + character_id)
            if alias:
                db.delete(alias)
            version = db.get(
                runtime.AppSetting, "avatar_expression_version:" + character_id
            )
            if version:
                db.delete(version)
            db.commit()
        # Manual regeneration follows the same CMS assignment gate as every other
        # image path. An enabled model without the avatar_image purpose must never
        # be called implicitly.
        runtime.generate_character_expressions(character_id, content)
        with runtime.Session() as db:
            row = db.get(runtime.Character, character_id)
            source_id = runtime.expression_source_id(db, row) if row else ""
            emotions = sorted(
                asset.emotion
                for asset in db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=source_id)
                .all()
            )
            version = db.get(
                runtime.AppSetting, "avatar_expression_version:" + character_id
            )
            return {
                "character_id": character_id,
                "status": (
                    "ready" if set(runtime.EMOTIONS).issubset(emotions) else "failed"
                ),
                "source_id": source_id,
                "emotions": emotions,
                "quality": version.value if version else "missing",
            }

    runtime.regenerate_character_expression_set = regenerate_character_expression_set


def bind_normalized_expression(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def normalized_expression(value):
        value = (value or "neutral").strip().lower()
        return (
            value
            if value
            in {"neutral", "happy", "sad", "angry", "surprised", "shy", "thinking"}
            else runtime.EXPRESSION_ALIASES.get(value, "neutral")
        )

    runtime.normalized_expression = normalized_expression

    def reply_expression(answer, fallback="neutral"):
        """Choose the portrait from what the character actually expressed."""
        value = (answer or "").casefold()
        patterns = {
            "happy": r"\b(happy|glad|delighted|excited|smile|smiles|laugh|laughs|grin|grins)\b|vui|hạnh phúc|phấn khích|mỉm cười|cười|rạng rỡ|háo hức",
            "sad": r"\b(sad|hurt|lonely|cry|cries|crying|tearful|disappointed|sorrow|heartbroken|sympathy|sympathetic)\b|buồn|đau lòng|xót lòng|xót xa|nặng lòng|chạnh lòng|cô đơn|khóc|rơi lệ|thất vọng|tủi thân|thương quá|tội nghiệp|an ủi|đồng cảm",
            "angry": r"\b(angry|furious|annoyed|irritated|mad|rage|glares?|scowls?)\b|tức giận|giận|bực|cáu|khó chịu|trừng mắt|lạnh giọng",
            "surprised": r"\b(surprised|shocked|astonished|startled|gasp|gasps|unexpected)\b|bất ngờ|ngạc nhiên|sững sờ|giật mình|há hốc",
            "shy": r"\b(shy|embarrassed|blush|blushes|bashful|flustered)\b|ngại|xấu hổ|đỏ mặt|bối rối|ấp úng",
        }
        scores = {
            emotion: len(runtime.re.findall(pattern, value, runtime.re.I))
            for emotion, pattern in patterns.items()
        }
        # Thinking cues must describe the character's action, not a user's question.
        narration = " ".join(runtime.re.findall(r"\*{1,3}([^*]+)(?:\*{1,3}|$)", value))
        scores["thinking"] = len(
            runtime.re.findall(
                r"\b(thinks?|thinking|ponders?|pondering|contemplates?|contemplating|lost in thought|thoughtfully)\b|suy nghĩ|trầm ngâm|đăm chiêu|思考|沉思|考え込|생각에 잠",
                narration,
                runtime.re.I,
            )
        )

        # Empathetic replies often mention making the user smile after first
        # expressing concern. Give the character's strong emotional cue precedence
        # over that proposed outcome.
        scores["sad"] += 2 * len(
            runtime.re.findall(
                r"đau lòng|xót lòng|xót xa|nặng lòng|chạnh lòng|an ủi|đồng cảm|heartbroken|sympathy|sympathetic",
                value,
                runtime.re.I,
            )
        )
        best = max(scores, key=scores.get)
        # No emotional cue means a neutral portrait for this turn. Keeping the
        # optional argument preserves API compatibility without carrying a stale
        # expression forward from a previous reply or session.
        return best if scores[best] else "neutral"

    runtime.reply_expression = reply_expression
