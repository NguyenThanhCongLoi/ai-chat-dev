"""api.characters: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_health(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/health")
    def health():
        return {
            "status": "ok",
            "build_version": runtime.os.getenv("BUILD_VERSION", "local"),
        }

    runtime.health = health

    @runtime.app.get("/v1/presets")
    def list_presets(
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        return {
            "characters": [
                {
                    **c.model_dump(),
                    **runtime.preset_social_stats(db, c.preset_type),
                    "home_section": runtime.preset_home_section(db, c),
                }
                for c in runtime.effective_presets(db)
            ],
            "groups": runtime.GROUP_PRESETS,
        }

    runtime.list_presets = list_presets

    @runtime.app.get("/v1/home-sections")
    def home_sections(
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        result = [
            {"id": "favorites", "name": "Yêu thích", "rule": "favorites", "tags": []},
            {"id": "trending", "name": "Trending", "rule": "trending", "tags": []},
            {
                "id": "popular",
                "name": "Phổ biến",
                "rule": "tags",
                "tags": [
                    "movie",
                    "film",
                    "anime",
                    "cartoon",
                    "manga",
                    "comic",
                    "cinema",
                    "hoạt hình",
                    "phim",
                    "truyện",
                ],
            },
            {
                "id": "top_rated",
                "name": "Đánh giá cao",
                "rule": "top_rated",
                "tags": [],
            },
            {
                "id": "entertainment",
                "name": "Giải trí",
                "rule": "tags",
                "tags": [
                    "entertainment",
                    "roleplay",
                    "role play",
                    "romance",
                    "fantasy",
                    "anime",
                    "giải trí",
                ],
            },
        ]
        for row in (
            db.query(runtime.AppSetting)
            .filter(runtime.AppSetting.key.like("home_section_config:%"))
            .order_by(runtime.AppSetting.key)
            .all()
        ):
            try:
                result.append(runtime.json.loads(row.value))
            except Exception:
                continue
        return result

    runtime.home_sections = home_sections

    @runtime.app.post("/v1/admin/home-sections")
    def admin_create_home_section(
        data: dict,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        name = str(data.get("name") or "").strip()
        tags = [str(x).strip().lower() for x in data.get("tags", []) if str(x).strip()]
        if not name or not tags:
            raise runtime.HTTPException(400, "Tên mục và ít nhất một tag là bắt buộc")
        section = {
            "id": "custom_" + runtime.uid().replace("-", "")[:10],
            "name": name[:60],
            "rule": "tags",
            "tags": tags[:20],
        }
        db.add(
            runtime.AppSetting(
                key="home_section_config:" + section["id"],
                value=runtime.json.dumps(section, ensure_ascii=False),
            )
        )
        db.commit()
        return section

    runtime.admin_create_home_section = admin_create_home_section

    @runtime.app.get("/v1/characters")
    def characters(
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        rows = db.query(runtime.Character).filter_by(user_id=user).all()
        overridden = {
            item.key.removeprefix("character_override:")
            for item in db.query(runtime.AppSetting)
            .filter(runtime.AppSetting.key.like("character_override:%"))
            .all()
        }
        current = {item.preset_type: item for item in runtime.effective_presets(db)}
        changed = False
        for row in rows:
            if row.id in overridden:
                continue
            saved = runtime.spec(row)
            source = current.get(saved.preset_type)
            if saved.creation_type == "preset" and source:
                refreshed = source.model_copy(deep=True)
                refreshed.id = row.id
                refreshed_spec = refreshed.model_dump_json()
                if (
                    row.name != refreshed.name
                    or saved.model_dump() != refreshed.model_dump()
                ):
                    row.name = refreshed.name
                    row.spec = refreshed_spec
                    row.updated_at = runtime.now()
                    changed = True
        if changed:
            db.commit()
        return [runtime.character_out(x, db) for x in rows]

    runtime.characters = characters

    @runtime.app.post("/v1/characters")
    def create_character(
        data: dict,
        background: runtime.BackgroundTasks,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        # Catalog cards intentionally contain presentation and social fields. Keep
        # the public API forward compatible by accepting only CharacterSpec fields;
        # the canonical preset is loaded from the server below and never trusted
        # from the card payload.
        clean = {
            key: value
            for key, value in data.items()
            if key in runtime.CharacterSpec.model_fields
        }
        try:
            c = runtime.CharacterSpec.model_validate(clean)
        except Exception as exc:
            raise runtime.HTTPException(422, str(exc))
        reuse_catalog = False
        if c.creation_type == "preset":
            source = next(
                (
                    p
                    for p in runtime.effective_presets(db)
                    if p.id == c.id
                    or (c.preset_type and p.preset_type == c.preset_type)
                ),
                None,
            )
            if source is None:
                raise runtime.HTTPException(400, "Unknown preset")
            for existing in db.query(runtime.Character).filter_by(user_id=user).all():
                saved = runtime.spec(existing)
                if (
                    saved.creation_type == "preset"
                    and saved.preset_type == source.preset_type
                ):
                    return saved
            c = source.model_copy(deep=True)
            c.id = runtime.uid()
            reuse_catalog = True
        elif c.id.startswith("preset-"):
            c.id = runtime.uid()
        saved = (
            runtime._persist_character(db, user, c)
            if reuse_catalog
            else runtime.save_character(db, user, c)
        )
        row = db.get(runtime.Character, saved.id)
        source_image = runtime.character_source_image(db, row) if row else None
        identity_row = db.get(
            runtime.AppSetting, "character_expression_identity:" + saved.id
        )
        shared = (
            runtime.registered_expression_source(db, identity_row.value)
            if identity_row
            else None
        )
        if row and runtime.spec(row).preset_type:
            preset_source = "__preset__:" + runtime.spec(row).preset_type
            if (
                db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=preset_source)
                .count()
                >= 6
            ):
                shared = preset_source
            for sibling in db.query(runtime.Character).all():
                if shared:
                    break
                if (
                    sibling.id == row.id
                    or runtime.spec(sibling).preset_type
                    != runtime.spec(row).preset_type
                ):
                    continue
                source_id = runtime.expression_source_id(db, sibling)
                if (
                    db.query(runtime.CharacterExpressionAsset)
                    .filter_by(character_id=source_id)
                    .count()
                    >= 6
                ):
                    shared = source_id
                    break
        if shared:
            db.add(
                runtime.AppSetting(key="expression_source:" + saved.id, value=shared)
            )
            db.commit()
        elif (
            row
            and runtime.spec(row).preset_type
            and (
                version := db.get(
                    runtime.AppSetting,
                    "avatar_expression_version:__preset__:"
                    + runtime.spec(row).preset_type,
                )
            )
            and version.value in {"queued", "processing"}
        ):
            db.add(
                runtime.AppSetting(
                    key="expression_source:" + saved.id,
                    value="__preset__:" + runtime.spec(row).preset_type,
                )
            )
            db.commit()
        elif source_image:
            background.add_task(
                runtime.generate_character_expressions, saved.id, source_image
            )
        else:
            runtime.install_default_expressions(db, saved.id)
        return runtime.spec(db.get(runtime.Character, saved.id))

    runtime.create_character = create_character

    @runtime.app.post("/v1/characters/generate")
    def generate_character(
        data: runtime.GenerateIn,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        runtime.enforce_character_policy(data)
        research = {"brief": "", "sources": []}
        if data.existing_media_character:
            if not data.media_character_name.strip():
                raise runtime.HTTPException(
                    400, "Hãy nhập tên nhân vật phim hoặc hoạt hình"
                )
            research = runtime.research_media_character(
                data.media_character_name, data.media_title
            )
        source = data.description
        if research["brief"]:
            source = (
                f"Create a faithful role-play interpretation of the existing fictional character {data.media_character_name}. "
                f"The user's description has priority for this product version. Do not claim facts absent from the supplied research.\n\n"
                f"USER DESCRIPTION:\n{data.description}\n\nRESEARCH EXCERPTS:\n{research['brief']}"
            )
        try:
            _, language_name = runtime.preferred_language(db, user)
            source = (
                f"Write every user-facing field, description and initial greeting in {language_name}.\n"
                + source
            )
            character = runtime.compile_character(
                source,
                data.name or data.media_character_name,
                role=data.role,
                scenario=data.scenario,
                initial_greeting=data.initial_greeting,
                dialogue_examples=data.dialogue_examples,
            )
            if research["sources"]:
                character.persona_knowledge = list(
                    dict.fromkeys(
                        [
                            *character.persona_knowledge,
                            *[
                                f"Research source: {x['title']} — {x['url']}"
                                for x in research["sources"]
                            ],
                        ]
                    )
                )[:12]
            saved = runtime.save_character(db, user, character)
            if data.existing_media_character:
                identity = runtime.set_character_expression_identity(
                    db, saved.id, data.media_character_name, data.media_title
                )
                db.commit()
                owner = runtime.registered_expression_source(db, identity)
                if not owner:
                    wanted = runtime.expression_identity(data.media_character_name)
                    for candidate in db.query(runtime.Character).all():
                        if (
                            candidate.id == saved.id
                            or runtime.expression_identity(runtime.spec(candidate).name)
                            != wanted
                        ):
                            continue
                        source_id = runtime.expression_source_id(db, candidate)
                        if (
                            source_id != "__default__"
                            and db.query(runtime.CharacterExpressionAsset)
                            .filter_by(character_id=source_id)
                            .count()
                            >= 6
                        ):
                            owner = source_id
                            break
                    if owner:
                        key = "expression_identity_owner:" + identity
                        db.add(runtime.AppSetting(key=key, value=owner))
                        db.commit()
                runtime.install_default_expressions(db, saved.id)
                if owner:
                    runtime.set_expression_alias(db, saved.id, owner)
                    db.commit()
            else:
                runtime.install_default_expressions(db, saved.id)
            return runtime.spec(db.get(runtime.Character, saved.id))
        except runtime.HTTPException:
            raise
        except Exception as exc:
            raise runtime.HTTPException(503, f"Character generation unavailable: {exc}")

    runtime.generate_character = generate_character


def bind_mirror_character(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.post("/v1/characters/mirror")
    def mirror_character(
        data: runtime.MirrorIn,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        runtime.enforce_character_policy(data)
        from character_chat.zodiac import zodiac_context

        zodiac_knowledge = None
        birth_context = "Không cung cấp ngày sinh; không suy đoán cung hoàng đạo."
        if data.birth_date:
            sign, zodiac_knowledge = zodiac_context(data.birth_date)
            birth_context = (
                f"Ngày sinh: {data.birth_date.isoformat()}. Cung hoàng đạo: {sign}."
            )
        source_description = (
            f"Tên: {data.name}. {birth_context} Mô tả nhân vật: {data.description}. "
            f"Lời giới thiệu do người dùng cung cấp: {data.introduction or 'không có'}. "
            "Đây là phiên bản AI mô phỏng, không phải con người thật."
        )
        knowledge = [zodiac_knowledge] if zodiac_knowledge else []
        _, language_name = runtime.preferred_language(db, user)
        source_description = (
            f"Write every user-facing field, description and initial greeting in {language_name}.\n"
            + source_description
        )
        try:
            c = runtime.compile_character(
                source_description, data.name, "mirror", knowledge
            )
        except Exception as exc:
            raise runtime.HTTPException(503, f"Mirror generation unavailable: {exc}")
        c.simulation_label = True
        c.persona_knowledge = list(dict.fromkeys([*c.persona_knowledge, *knowledge]))
        if data.birth_date:
            c.identity.age_description = (
                f"Sinh ngày {data.birth_date.strftime('%d/%m/%Y')}"
            )
        if data.introduction.strip():
            c.initial_greeting = data.introduction.strip()
        saved = runtime.save_character(db, user, c)
        runtime.install_default_expressions(db, saved.id)
        return runtime.spec(db.get(runtime.Character, saved.id))

    runtime.mirror_character = mirror_character

    @runtime.app.get("/v1/characters/{character_id}")
    def get_character(
        character_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        return runtime.character_out(
            runtime.owned(db, runtime.Character, character_id, user), db
        )

    runtime.get_character = get_character

    @runtime.app.patch("/v1/characters/{character_id}")
    def patch_character(
        character_id: str,
        changes: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        row = runtime.owned(db, runtime.Character, character_id, user)
        data = runtime.spec(row).model_dump()
        data.update(changes)
        data["id"] = character_id
        c = runtime.CharacterSpec.model_validate(data)
        runtime.enforce_character_policy(c, previous=runtime.spec(row))
        from ..publication_review import withdraw_on_edit
        withdraw_on_edit(db, character_id)
        row.name = c.name
        row.spec = c.model_dump_json()
        row.updated_at = runtime.now()
        db.add(
            runtime.CharacterVersion(
                id=runtime.uid(), character_id=character_id, spec=row.spec
            )
        )
        db.commit()
        return c

    runtime.patch_character = patch_character

    @runtime.app.patch("/v1/characters/{character_id}/publication")
    def update_character_publication(
        character_id: str,
        data: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        if data.get("is_public") and runtime.os.getenv("COMMUNITY_CHARACTER_PUBLICATION_ENABLED","false").lower()!="true":
            raise runtime.HTTPException(403, "Hiện chỉ nhân vật hệ thống được công khai. Nhân vật của bạn được lưu riêng tư.")
        character = runtime.owned(db, runtime.Character, character_id, user)
        row = db.get(runtime.CharacterPublication, character_id)
        tags = runtime.json.loads(row.tags) if row else []
        character_type = row.character_type if row else "companion"
        if "tags" in data:
            if not isinstance(data["tags"], list):
                raise runtime.HTTPException(400, "Tags must be a list")
            tags = [str(x).strip()[:30] for x in data["tags"] if str(x).strip()][:8]
        if "character_type" in data:
            character_type = str(data["character_type"]).strip()[:60] or "companion"
        if "tags" in data or "character_type" in data or bool(data.get("is_public")):
            runtime.enforce_character_policy(
                {
                    **runtime.spec(character).model_dump(),
                    "tags": tags,
                    "character_type": character_type,
                }
            )
        if not row:
            row = runtime.CharacterPublication(
                character_id=character_id, creator_user_id=user
            )
            db.add(row)
        from ..publication_review import record, review
        if "is_public" in data and type(data["is_public"]) is not bool:
            raise runtime.HTTPException(422, "Expected boolean is_public")
        if "is_public" in data:
            if data["is_public"] and runtime.spec(character).creation_type == "preset":
                raise runtime.HTTPException(422, "System characters cannot be republished")
            if data["is_public"] and db.get(runtime.AppSetting, "character_clone_source:" + character_id):
                raise runtime.HTTPException(422, "Publish your own characters, not library copies")
            row.is_public = 0
            record(db, character_id, "pending" if data["is_public"] else "private")
        elif "tags" in data or "character_type" in data:
            row.is_public = 0
            record(db, character_id, "private")
        row.character_type = character_type
        row.tags = runtime.json.dumps(tags, ensure_ascii=False)
        row.updated_at = runtime.now()
        db.commit()
        return {
            "character_id": character_id,
            "is_public": bool(row.is_public),
            "publication_status": review(db, character_id)["status"],
            "character_type": row.character_type,
            "tags": tags,
        }

    runtime.update_character_publication = update_character_publication

    @runtime.app.post("/v1/characters/{character_id}/avatar")
    def upload_character_avatar(
        character_id: str,
        background: runtime.BackgroundTasks,
        file: runtime.UploadFile = runtime.File(...),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        character = runtime.owned(db, runtime.Character, character_id, user)
        content = file.file.read(5 * 1024 * 1024 + 1)
        if len(content) > 5 * 1024 * 1024:
            raise runtime.HTTPException(413, "Ảnh avatar tối đa 5 MB")
        mime = (file.content_type or "").lower()
        if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            raise runtime.HTTPException(400, "Chỉ hỗ trợ JPG, PNG, WEBP hoặc GIF")
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
        item = runtime.spec(character)
        item.avatar_url = (
            f"/v1/public/characters/{character_id}/avatar?v={card_version}"
        )
        from ..publication_review import withdraw_on_edit
        withdraw_on_edit(db, character_id)
        character.spec = item.model_dump_json()
        character.updated_at = runtime.now()
        db.commit()
        image_hash = runtime.hashlib.sha256(content).hexdigest()
        hash_key = "character_expression_image_hash:" + character_id
        hash_row = db.get(runtime.AppSetting, hash_key)
        if hash_row:
            hash_row.value = image_hash
            hash_row.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=hash_key, value=image_hash))
        identity_row = db.get(
            runtime.AppSetting, "character_expression_identity:" + character_id
        )
        shared = (
            runtime.registered_expression_source(db, identity_row.value)
            if identity_row
            else None
        ) or runtime.registered_image_source(db, image_hash)
        if shared:
            db.query(runtime.CharacterExpressionAsset).filter_by(
                character_id=character_id
            ).delete()
            runtime.set_expression_alias(db, character_id, shared)
            version = db.get(
                runtime.AppSetting, "avatar_expression_version:" + character_id
            )
            if version:
                version.value = "shared"
                version.updated_at = runtime.now()
            else:
                db.add(
                    runtime.AppSetting(
                        key="avatar_expression_version:" + character_id, value="shared"
                    )
                )
            db.commit()
            return {
                "avatar_url": item.avatar_url,
                "expression_status": "ready",
                "expression_source": shared,
            }
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
        background.add_task(
            runtime.generate_character_expressions, character_id, content
        )
        return {"avatar_url": item.avatar_url, "expression_status": "processing"}

    runtime.upload_character_avatar = upload_character_avatar


def bind_delete_character(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.delete("/v1/characters/{character_id}")
    def delete_character(
        character_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        row = runtime.owned(db, runtime.Character, character_id, user)
        publication = db.get(runtime.CharacterPublication, character_id)
        was_public = bool(publication and publication.is_public)
        cascade = []
        if was_public:
            cascade_by_id = {}
            clone_settings = (
                db.query(runtime.AppSetting)
                .filter(
                    runtime.AppSetting.key.like("character_clone_source:%"),
                    runtime.AppSetting.value == character_id,
                )
                .all()
            )
            for item in clone_settings:
                clone = db.get(
                    runtime.Character, item.key.removeprefix("character_clone_source:")
                )
                if clone:
                    cascade_by_id[clone.id] = clone
            identity = db.get(
                runtime.AppSetting, "character_expression_identity:" + character_id
            )
            if identity:
                identity_links = (
                    db.query(runtime.AppSetting)
                    .filter(
                        runtime.AppSetting.key.like("character_expression_identity:%"),
                        runtime.AppSetting.value == identity.value,
                    )
                    .all()
                )
                for item in identity_links:
                    candidate_id = item.key.removeprefix(
                        "character_expression_identity:"
                    )
                    if candidate_id != character_id:
                        candidate = db.get(runtime.Character, candidate_id)
                        if candidate:
                            cascade_by_id[candidate.id] = candidate
            cascade = list(cascade_by_id.values())
            for clone in cascade:
                runtime.purge_character_record(db, clone)
            for setting in clone_settings:
                if db.get(runtime.AppSetting, setting.key):
                    db.delete(setting)
        result = runtime.purge_character_record(db, row)
        db.commit()
        return {
            "deleted": True,
            "was_public": was_public,
            "deleted_clones": len(cascade),
            "expression_source_preserved": result["expression_source_preserved"],
        }

    runtime.delete_character = delete_character
