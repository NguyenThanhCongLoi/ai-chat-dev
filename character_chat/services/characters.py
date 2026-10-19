"""services.characters: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_owned(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def owned(db, model, id, user):
        row = db.get(model, id)
        if not row or row.user_id != user:
            raise runtime.HTTPException(404, "Not found")
        return row

    runtime.owned = owned

    def spec(row):
        return runtime.CharacterSpec.model_validate_json(row.spec)

    runtime.spec = spec

    def expression_identity(name, title=""):
        value = (
            runtime.unicodedata.normalize("NFKD", f"{name}|{title}")
            .encode("ascii", "ignore")
            .decode()
            .casefold()
        )
        value = runtime.re.sub(r"[^a-z0-9]+", "-", value).strip("-")
        return runtime.hashlib.sha256(value.encode()).hexdigest() if value else ""

    runtime.expression_identity = expression_identity

    def registered_expression_source(db, identity):
        if not identity:
            return None
        stable_id = "__identity__:" + identity
        if (
            db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id=stable_id)
            .count()
            >= 6
        ):
            return stable_id
        row = db.get(runtime.AppSetting, "expression_identity_owner:" + identity)
        if (
            row
            and db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id=row.value)
            .count()
            >= 6
        ):
            return row.value
        return None

    runtime.registered_expression_source = registered_expression_source

    def registered_image_source(db, image_hash):
        if not image_hash:
            return None
        row = db.get(runtime.AppSetting, "expression_image_owner:" + image_hash)
        if (
            row
            and db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id=row.value)
            .count()
            >= 6
        ):
            return row.value
        return None

    runtime.registered_image_source = registered_image_source

    def set_expression_alias(db, character_id, source_id):
        key = "expression_source:" + character_id
        row = db.get(runtime.AppSetting, key)
        if row:
            row.value = source_id
            row.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=key, value=source_id))

    runtime.set_expression_alias = set_expression_alias

    def set_character_expression_identity(db, character_id, name, title=""):
        identity = runtime.expression_identity(name, title)
        if not identity:
            return ""
        key = "character_expression_identity:" + character_id
        row = db.get(runtime.AppSetting, key)
        if row:
            row.value = identity
            row.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=key, value=identity))
        return identity

    runtime.set_character_expression_identity = set_character_expression_identity

    def register_expression_identity(db, character_id):
        identity_row = db.get(
            runtime.AppSetting, "character_expression_identity:" + character_id
        )
        if not identity_row:
            return
        stable_id = "__identity__:" + identity_row.value
        assets = (
            db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id=character_id)
            .all()
        )
        if assets:
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
            db.query(runtime.CharacterExpressionAsset).filter_by(
                character_id=character_id
            ).delete()
        runtime.set_expression_alias(db, character_id, stable_id)
        key = "expression_identity_owner:" + identity_row.value
        owner = db.get(runtime.AppSetting, key)
        if owner:
            owner.value = stable_id
            owner.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=key, value=stable_id))

    runtime.register_expression_identity = register_expression_identity

    def register_expression_image(db, character_id):
        hash_row = db.get(
            runtime.AppSetting, "character_expression_image_hash:" + character_id
        )
        if not hash_row:
            return
        source_id = (
            runtime.expression_source_id(db, db.get(runtime.Character, character_id))
            if db.get(runtime.Character, character_id)
            else character_id
        )
        key = "expression_image_owner:" + hash_row.value
        owner = db.get(runtime.AppSetting, key)
        if owner:
            owner.value = source_id
            owner.updated_at = runtime.now()
        else:
            db.add(runtime.AppSetting(key=key, value=source_id))

    runtime.register_expression_image = register_expression_image

    def character_source_image(db, row):
        """Resolve the original card image used to build a separate expression portrait."""
        asset = db.get(runtime.CharacterAsset, row.id)
        if asset:
            return asset.content
        item = runtime.spec(row)
        url = item.avatar_url or ""
        if item.preset_type:
            stored = db.get(runtime.AppSetting, "preset_asset:" + item.preset_type)
            if stored:
                try:
                    return runtime.base64.b64decode(
                        runtime.json.loads(stored.value)["content"]
                    )
                except Exception:
                    pass
            # Older character rows were saved before preset avatar_url was copied
            # into their specs. Resolve the current preset image instead of
            # treating those characters as having no source image.
            if not url:
                template = next(
                    (
                        candidate
                        for candidate in runtime.effective_presets(db)
                        if candidate.preset_type == item.preset_type
                    ),
                    None,
                )
                if template:
                    url = template.avatar_url or ""
        prefix = "/character-images/"
        if url.startswith(prefix + "default_icons/"):
            return None
        if url.startswith(prefix):
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

    runtime.character_source_image = character_source_image

    def character_out(row, db=None):
        result = runtime.spec(row).model_dump()
        if db:
            from ..publication_review import review
            publication = db.get(runtime.CharacterPublication, row.id)
            source = db.get(runtime.AppSetting, "character_clone_source:" + row.id)
            result["source_character_id"] = source.value if source else None
            result["publication_status"] = review(db, row.id)["status"] if publication else "private"
            result.update(
                {
                    "is_public": bool(publication and publication.is_public and runtime.os.getenv("COMMUNITY_CHARACTER_PUBLICATION_ENABLED","false").lower()=="true"),
                    "character_type": (
                        publication.character_type
                        if publication
                        else result.get("category", "companion")
                    ),
                    "tags": runtime.json.loads(publication.tags) if publication else [],
                    "creator_user_id": row.user_id,
                }
            )
            if avatar := runtime.character_avatar_metadata_url(db, row.id):
                result["avatar_url"] = avatar
            result.update(
                runtime.character_social_stats(
                    db, runtime.character_social_family_ids(db, row)
                )
            )
        return result

    runtime.character_out = character_out

    def character_social_family_ids(db, row):
        """Return every stored copy that represents the same public/preset character."""
        try:
            item = runtime.spec(row)
        except Exception:
            item = None
        if item and item.preset_type:
            result = []
            for candidate in db.query(runtime.Character).all():
                try:
                    if runtime.spec(candidate).preset_type == item.preset_type:
                        result.append(candidate.id)
                except Exception:
                    continue
            return result or [row.id]
        root = row.id
        seen = set()
        while root not in seen:
            seen.add(root)
            link = db.get(runtime.AppSetting, "character_clone_source:" + root)
            if not link or not db.get(runtime.Character, link.value):
                break
            root = link.value
        family = {root}
        changed = True
        while changed:
            changed = False
            for link in (
                db.query(runtime.AppSetting)
                .filter(runtime.AppSetting.key.like("character_clone_source:%"))
                .all()
            ):
                clone_id = link.key.removeprefix("character_clone_source:")
                if (
                    link.value in family
                    and db.get(runtime.Character, clone_id)
                    and clone_id not in family
                ):
                    family.add(clone_id)
                    changed = True
        return list(family)

    runtime.character_social_family_ids = character_social_family_ids

    def character_social_stats(db, character_ids):
        if not character_ids:
            return {"usage_count": 0, "trending_score": 0, "reactions": {}}
        usage = (
            db.query(runtime.Room.user_id)
            .join(runtime.RoomMember, runtime.RoomMember.room_id == runtime.Room.id)
            .filter(runtime.RoomMember.character_id.in_(character_ids))
            .distinct()
            .count()
        )
        recent_cutoff = (
            runtime.datetime.now(runtime.timezone.utc) - runtime.timedelta(days=7)
        ).isoformat()
        trending = (
            db.query(runtime.Room.user_id)
            .join(runtime.RoomMember, runtime.RoomMember.room_id == runtime.Room.id)
            .filter(
                runtime.RoomMember.character_id.in_(character_ids),
                runtime.Room.created_at >= recent_cutoff,
            )
            .distinct()
            .count()
        )
        reaction_rows = (
            db.query(runtime.CharacterReaction)
            .filter(runtime.CharacterReaction.character_id.in_(character_ids))
            .order_by(runtime.CharacterReaction.created_at)
            .all()
        )
        counts = {}
        by_user = {}
        for item in reaction_rows:
            by_user[item.user_id] = item.reaction
        for reaction in by_user.values():
            counts[reaction] = counts.get(reaction, 0) + 1
        return {"usage_count": usage, "trending_score": trending, "reactions": counts}

    runtime.character_social_stats = character_social_stats

    def preset_social_stats(db, preset_type):
        ids = []
        for row in db.query(runtime.Character).all():
            try:
                if runtime.spec(row).preset_type == preset_type:
                    ids.append(row.id)
            except Exception:
                continue
        result = runtime.character_social_stats(db, ids)
        ratings = (
            db.query(runtime.CharacterRating)
            .filter(runtime.CharacterRating.character_id.in_(ids))
            .all()
            if ids
            else []
        )
        result.update(
            {
                "rating": (
                    round(sum(x.rating for x in ratings) / len(ratings), 1)
                    if ratings
                    else 0
                ),
                "rating_count": len(ratings),
            }
        )
        return result

    runtime.preset_social_stats = preset_social_stats

    def preset_home_section(db, item):
        row = db.get(
            runtime.AppSetting, "preset_home_section:" + (item.preset_type or "")
        )
        return (
            row.value
            if row
            else ("hidden" if item.category == "entertainment" else "auto")
        )

    runtime.preset_home_section = preset_home_section

    def effective_presets(db):
        result = []
        templates = runtime.presets()
        for saved in (
            db.query(runtime.AppSetting)
            .filter(runtime.AppSetting.key.like("admin_preset:%"))
            .all()
        ):
            try:
                templates.append(runtime.CharacterSpec.model_validate_json(saved.value))
            except Exception:
                continue
        for template in templates:
            override = db.get(
                runtime.AppSetting, "preset_override:" + (template.preset_type or "")
            )
            if override:
                try:
                    template = runtime.CharacterSpec.model_validate_json(override.value)
                except Exception:
                    pass
            result.append(template)
        return result

    runtime.effective_presets = effective_presets

    def suggestion_values(db, message_id):
        values = [
            item.text
            for item in db.query(runtime.MessageSuggestion)
            .filter_by(message_id=message_id)
            .order_by(runtime.MessageSuggestion.position)
            .all()
        ]
        if not values:
            return []
        if runtime.parse_suggestions("@@" + "|".join(values)) == values:
            return values
        message = db.get(runtime.Message, message_id)
        room = db.get(runtime.Room, message.room_id) if message else None
        return (
            runtime.fallback_suggestions(
                message.text, language=runtime.preferred_language(db, room.user_id)[0]
            )
            if message and room
            else []
        )

    runtime.suggestion_values = suggestion_values

    def save_suggestions(db, message_id, values):
        db.query(runtime.MessageSuggestion).filter_by(message_id=message_id).delete()
        for position, value in enumerate(values[:3]):
            db.add(
                runtime.MessageSuggestion(
                    id=runtime.uid(),
                    message_id=message_id,
                    text=value[:90],
                    position=position,
                )
            )

    runtime.save_suggestions = save_suggestions

    def previous_roleplay_suggestions(db, room_id):
        latest = (
            db.query(runtime.Message)
            .filter_by(room_id=room_id, sender_type="character")
            .order_by(runtime.Message.created_at.desc())
            .first()
        )
        return runtime.suggestion_values(db, latest.id) if latest else []

    runtime.previous_roleplay_suggestions = previous_roleplay_suggestions

    def default_character_prompt(c):
        return (
            f"Roleplay consistently as {c.name}. Identity role: {c.identity.role}. Description: {c.description}. "
            f"Scenario: {c.scenario or 'an ongoing conversation with the user'}. "
            "Follow this character's personality, speech settings, goals, boundaries and dialogue examples. "
            "Let closeness grow gradually from relationship state and always reply in the user's language."
        )

    runtime.default_character_prompt = default_character_prompt

    def save_character(db, user, c):
        runtime.enforce_character_policy(c)
        return runtime._persist_character(db, user, c)

    runtime.save_character = save_character

    def _persist_character(db, user, c):
        # Internal persistence only. Catalog reuse loads the canonical source on
        # the server; all new user-authored cards pass through save_character.
        if not c.system_prompt.strip():
            c.system_prompt = runtime.default_character_prompt(c)
        c.id = runtime.uid() if db.get(runtime.Character, c.id) else c.id
        row = runtime.Character(
            id=c.id, user_id=user, name=c.name, spec=c.model_dump_json()
        )
        db.add(row)
        db.add(
            runtime.CharacterVersion(id=runtime.uid(), character_id=c.id, spec=row.spec)
        )
        db.add(
            runtime.CharacterPublication(
                character_id=c.id,
                creator_user_id=user,
                is_public=0,
                character_type=(
                    c.support.primary_role
                    if c.category == "utility"
                    else "entertainment"
                ),
                tags="[]",
            )
        )
        # Image identity belongs to the character, not to the user account. Every
        # creation path can therefore reuse one expression set across all users.
        runtime.set_character_expression_identity(db, c.id, c.name)
        db.commit()
        return c

    runtime._persist_character = _persist_character
