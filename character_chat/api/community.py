"""api.community: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_character_expression(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/v1/characters/{character_id}/expression/{emotion}")
    def character_expression(
        character_id: str,
        emotion: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        character = runtime.owned(db, runtime.Character, character_id, user)
        emotion = runtime.normalized_expression(emotion)
        source_id = runtime.expression_source_id(db, character)
        asset = (
            db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id=source_id, emotion=emotion)
            .first()
        )
        if not asset and emotion == "thinking":
            asset = (
                db.query(runtime.CharacterExpressionAsset)
                .filter_by(character_id=source_id, emotion="neutral")
                .first()
            )
        if not asset:
            asset = (
                db.query(runtime.CharacterExpressionAsset)
                .filter_by(
                    character_id="__default__",
                    emotion="neutral" if emotion == "thinking" else emotion,
                )
                .first()
            )
        if not asset:
            raise runtime.HTTPException(404, "Expression avatar is not ready")
        return runtime.Response(
            asset.content,
            media_type=asset.mime_type,
            headers={"Cache-Control": "no-store, max-age=0"},
        )

    runtime.character_expression = character_expression

    @runtime.app.get("/v1/characters/{character_id}/expressions/status")
    def character_expression_status(
        character_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        character = runtime.owned(db, runtime.Character, character_id, user)
        source_id = runtime.expression_source_id(db, character)
        count = (
            db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id=source_id)
            .count()
        )
        version = db.get(
            runtime.AppSetting, "avatar_expression_version:" + source_id
        ) or db.get(runtime.AppSetting, "avatar_expression_version:" + character_id)
        quality = version.value if version else "processing"
        return {
            "status": (
                "ready"
                if count
                >= len({"neutral", "happy", "sad", "angry", "surprised", "shy"})
                else "processing"
            ),
            "count": count,
            "quality": quality,
        }

    runtime.character_expression_status = character_expression_status

    @runtime.app.get("/v1/public/characters")
    def public_characters(
        q: str = "",
        character_type: str = "",
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        if runtime.os.getenv("COMMUNITY_CHARACTER_PUBLICATION_ENABLED","false").lower()!="true":
            return []
        query = db.query(runtime.CharacterPublication).filter_by(is_public=1)
        if character_type:
            query = query.filter_by(character_type=character_type)
        result = []
        for publication in (
            query.order_by(runtime.CharacterPublication.updated_at.desc())
            .limit(100)
            .all()
        ):
            row = db.get(runtime.Character, publication.character_id)
            if not row:
                continue
            item = runtime.spec(row)
            account = db.get(runtime.UserAccount, publication.creator_user_id)
            tags = runtime.json.loads(publication.tags)
            if (
                q
                and q.lower()
                not in " ".join(
                    [item.name, item.description, publication.character_type, *tags]
                ).lower()
            ):
                continue
            ratings = (
                db.query(runtime.CharacterRating).filter_by(character_id=row.id).all()
            )
            uses = (
                db.query(runtime.CharacterUsage).filter_by(character_id=row.id).count()
            )
            followers = (
                db.query(runtime.CreatorFollow)
                .filter_by(creator_user_id=publication.creator_user_id)
                .count()
            )
            social = runtime.character_social_stats(
                db, runtime.character_social_family_ids(db, row)
            )
            asset = db.get(runtime.CharacterAsset, row.id)
            asset_url = (
                f"/v1/public/characters/{row.id}/avatar?v={runtime.hashlib.sha256(asset.content).hexdigest()[:12]}"
                if asset
                else item.avatar_url
            )
            result.append(
                {
                    **item.model_dump(),
                    "is_public": True,
                    "character_type": publication.character_type,
                    "tags": tags,
                    "creator": {
                        "id": publication.creator_user_id,
                        "name": account.display_name if account else "Người dùng",
                        "followers": followers,
                    },
                    "rating": (
                        round(sum(x.rating for x in ratings) / len(ratings), 1)
                        if ratings
                        else 0
                    ),
                    "rating_count": len(ratings),
                    "usage_count": max(uses, social["usage_count"]),
                    "reactions": social["reactions"],
                    "avatar_url": asset_url,
                }
            )
        return result

    runtime.public_characters = public_characters

    @runtime.app.get("/v1/public/characters/{character_id}/avatar")
    def public_character_avatar(
        character_id: str, db: runtime.DBSession = runtime.Depends(runtime.db_session)
    ):
        asset = db.get(runtime.CharacterAsset, character_id)
        if not asset:
            raise runtime.HTTPException(404, "Avatar not found")
        return runtime.Response(
            asset.content,
            media_type=asset.mime_type,
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "ETag": '"' + runtime.hashlib.sha256(asset.content).hexdigest() + '"',
            },
        )

    runtime.public_character_avatar = public_character_avatar

    @runtime.app.post("/v1/public/characters/{character_id}/clone")
    def clone_public_character(
        character_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        if runtime.os.getenv("COMMUNITY_CHARACTER_PUBLICATION_ENABLED","false").lower()!="true":
            raise runtime.HTTPException(403,"Community characters are temporarily unavailable")
        publication = db.get(runtime.CharacterPublication, character_id)
        source = db.get(runtime.Character, character_id)
        if not publication or not publication.is_public or not source:
            raise runtime.HTTPException(404, "Nhân vật public không tồn tại")
        previous = (
            db.query(runtime.AppSetting)
            .filter(
                runtime.AppSetting.key.like("character_clone_source:%"),
                runtime.AppSetting.value == character_id,
            )
            .all()
        )
        clones = [
            db.get(runtime.Character, item.key.removeprefix("character_clone_source:"))
            for item in previous
        ]
        owned_clones = [item for item in clones if item and item.user_id == user]
        if owned_clones:
            existing = max(owned_clones, key=lambda item: (item.created_at, item.id))
            return runtime.character_out(existing, db)
        if (
            not db.query(runtime.CharacterUsage)
            .filter_by(character_id=character_id, user_id=user)
            .first()
        ):
            db.add(
                runtime.CharacterUsage(
                    id=runtime.uid(), character_id=character_id, user_id=user
                )
            )
        clone = runtime.spec(source).model_copy(deep=True)
        clone.id = runtime.uid()
        clone.creation_type = "custom"
        clone.avatar_url = None
        clone = runtime._persist_character(db, user, clone)
        source_asset = db.get(runtime.CharacterAsset, character_id)
        if source_asset:
            db.add(
                runtime.CharacterAsset(
                    character_id=clone.id,
                    mime_type=source_asset.mime_type,
                    content=source_asset.content,
                )
            )
            clone.avatar_url = f"/v1/public/characters/{clone.id}/avatar?v={runtime.hashlib.sha256(source_asset.content).hexdigest()[:12]}"
            row = db.get(runtime.Character, clone.id)
            row.spec = clone.model_dump_json()
        source_id = runtime.expression_source_id(db, source)
        db.add(runtime.AppSetting(key="expression_source:" + clone.id, value=source_id))
        db.add(
            runtime.AppSetting(
                key="character_clone_source:" + clone.id, value=character_id
            )
        )
        db.commit()
        return runtime.character_out(db.get(runtime.Character, clone.id), db)

    runtime.clone_public_character = clone_public_character

    @runtime.app.put("/v1/public/characters/{character_id}/rating")
    def rate_public_character(
        character_id: str,
        data: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        publication = db.get(runtime.CharacterPublication, character_id)
        rating = int(data.get("rating", 0))
        if not publication or not publication.is_public:
            raise runtime.HTTPException(404, "Nhân vật public không tồn tại")
        if rating < 1 or rating > 5:
            raise runtime.HTTPException(400, "Đánh giá phải từ 1 đến 5 sao")
        row = (
            db.query(runtime.CharacterRating)
            .filter_by(character_id=character_id, user_id=user)
            .first()
        )
        if row:
            row.rating = rating
            row.updated_at = runtime.now()
        else:
            db.add(
                runtime.CharacterRating(
                    id=runtime.uid(),
                    character_id=character_id,
                    user_id=user,
                    rating=rating,
                )
            )
        db.commit()
        return {"rated": True, "rating": rating}

    runtime.rate_public_character = rate_public_character

    @runtime.app.put("/v1/characters/{character_id}/reaction")
    def react_to_character(
        character_id: str,
        data: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        character = db.get(runtime.Character, character_id)
        publication = db.get(runtime.CharacterPublication, character_id)
        if not character or (
            character.user_id != user and not (publication and publication.is_public)
        ):
            raise runtime.HTTPException(404, "Character not found")
        reaction = str(data.get("reaction") or "")
        if reaction not in ("❤️", "😂", "🔥", "👍", "😮"):
            raise runtime.HTTPException(400, "Biểu cảm không hợp lệ")
        family_ids = runtime.character_social_family_ids(db, character)
        rows = (
            db.query(runtime.CharacterReaction)
            .filter(
                runtime.CharacterReaction.character_id.in_(family_ids),
                runtime.CharacterReaction.user_id == user,
            )
            .all()
        )
        if rows and rows[-1].reaction == reaction:
            for row in rows:
                db.delete(row)
            selected = None
        elif rows:
            rows[0].reaction = reaction
            for row in rows[1:]:
                db.delete(row)
            selected = reaction
        else:
            db.add(
                runtime.CharacterReaction(
                    id=runtime.uid(),
                    character_id=character_id,
                    user_id=user,
                    reaction=reaction,
                )
            )
            selected = reaction
        db.commit()
        return {"selected": selected, **runtime.character_social_stats(db, family_ids)}

    runtime.react_to_character = react_to_character

    @runtime.app.put("/v1/public/creators/{creator_id}/follow")
    def follow_creator(
        creator_id: str,
        data: dict,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        if creator_id == user:
            raise runtime.HTTPException(400, "Bạn không cần theo dõi chính mình")
        if not db.get(runtime.User, creator_id):
            raise runtime.HTTPException(404, "Người tạo không tồn tại")
        row = (
            db.query(runtime.CreatorFollow)
            .filter_by(follower_user_id=user, creator_user_id=creator_id)
            .first()
        )
        following = bool(data.get("following", True))
        if following and not row:
            db.add(
                runtime.CreatorFollow(
                    id=runtime.uid(), follower_user_id=user, creator_user_id=creator_id
                )
            )
        if not following and row:
            db.delete(row)
        db.commit()
        return {
            "following": following,
            "followers": db.query(runtime.CreatorFollow)
            .filter_by(creator_user_id=creator_id)
            .count(),
        }

    runtime.follow_creator = follow_creator
