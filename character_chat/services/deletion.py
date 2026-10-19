"""services.deletion: domain-specific application implementation.

Ownership-scoped deletion, archive behavior and relationship-state reset.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_purge_message_dependents(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def purge_message_dependents(db, message_ids):
        db.query(runtime.MessageSpeechPart).filter(
            runtime.MessageSpeechPart.message_id.in_(message_ids)
        ).delete(synchronize_session=False)
        db.query(runtime.MessageSpeechRun).filter(
            runtime.MessageSpeechRun.message_id.in_(message_ids)
        ).delete(synchronize_session=False)
        db.query(runtime.MessageSpeech).filter(
            runtime.MessageSpeech.message_id.in_(message_ids)
        ).delete(synchronize_session=False)
        if not message_ids:
            return
        db.query(runtime.MessageAlternative).filter(
            runtime.MessageAlternative.message_id.in_(message_ids)
        ).delete(synchronize_session=False)
        db.query(runtime.MessageSuggestion).filter(
            runtime.MessageSuggestion.message_id.in_(message_ids)
        ).delete(synchronize_session=False)
        from ..roleplay_episode import PREFIX as EPISODE_PREFIX
        # Recaps quote source dialogue; remove derived notes with deleted sources.
        removed_ids=set(message_ids)
        for note in db.query(runtime.AppSetting).filter(
                runtime.AppSetting.key.startswith(EPISODE_PREFIX,autoescape=True)).all():
            try:
                linked=set(runtime.json.loads(note.value).get("source_ids",[]))
            except (ValueError,TypeError):
                linked=removed_ids
            if linked & removed_ids:db.delete(note)
        db.query(runtime.Memory).filter(
            runtime.Memory.source_message_id.in_(message_ids)
        ).delete(synchronize_session=False)
        db.query(runtime.RelationshipEvent).filter(
            runtime.RelationshipEvent.source_message_id.in_(message_ids)
        ).delete(synchronize_session=False)
        db.query(runtime.MoodObservation).filter(
            runtime.MoodObservation.source_message_id.in_(message_ids)
        ).delete(synchronize_session=False)

    runtime.purge_message_dependents = purge_message_dependents

    def purge_document_record(db, document_id, force=False):
        if not force and (
            db.query(runtime.RoomDocument).filter_by(document_id=document_id).first()
            or db.query(runtime.CharacterKnowledge)
            .filter_by(document_id=document_id)
            .first()
        ):
            return False
        db.query(runtime.ProcessingJob).filter_by(resource_id=document_id).delete()
        db.query(runtime.RoomDocument).filter_by(document_id=document_id).delete()
        db.query(runtime.CharacterKnowledge).filter_by(document_id=document_id).delete()
        db.query(runtime.DocumentChunk).filter_by(document_id=document_id).delete()
        db.query(runtime.AssistantFile).filter_by(document_id=document_id).delete()
        document = db.get(runtime.Document, document_id)
        if document:
            db.delete(document)
        return bool(document)

    runtime.purge_document_record = purge_document_record

    def reset_room_character_feelings(db, user, character_ids):
        """Relationship state is per user/character, not per room."""
        if not character_ids:
            return
        db.query(runtime.Relationship).filter(
            runtime.Relationship.user_id == user,
            (runtime.Relationship.character_id.in_(character_ids))
            | (runtime.Relationship.other_character_id.in_(character_ids)),
        ).delete(synchronize_session=False)
        for model in (
            runtime.CharacterState,
            runtime.RelationshipEvent,
            runtime.CharacterReflection,
        ):
            db.query(model).filter(
                model.user_id == user, model.character_id.in_(character_ids)
            ).delete(synchronize_session=False)

    runtime.reset_room_character_feelings = reset_room_character_feelings

    # Explicit room deletion can reset owner experience; internal archival deletes retain their existing behavior.
    def purge_room_record(db, room, reset_all=False):
        room_id = room.id
        character_ids = [
            item.character_id
            for item in db.query(runtime.RoomMember).filter_by(room_id=room_id).all()
        ]
        runtime.reset_room_character_feelings(db, room.user_id, character_ids)
        if reset_all:
            from ..conversation_reset import reset_character_experience
            reset_character_experience(db, room.user_id, character_ids)
        attached_ids = [
            item.document_id
            for item in db.query(runtime.RoomDocument).filter_by(room_id=room_id).all()
        ]
        message_ids = [
            item.id
            for item in db.query(runtime.Message).filter_by(room_id=room_id).all()
        ]
        if reset_all:
            # Do not retain/materialize a duplicate transcript in CMS logs on full reset.
            db.query(runtime.AIRequestLog).filter_by(user_id=room.user_id,room_id=room_id).delete(synchronize_session=False)
            db.query(runtime.VoiceEvent).filter(runtime.VoiceEvent.user_id==room.user_id,
                runtime.VoiceEvent.message_id.in_(message_ids)).delete(synchronize_session=False)
        else:
            runtime.archive_chat_before_delete(db, room_id)
        runtime.purge_message_dependents(db, message_ids)
        db.query(runtime.Message).filter_by(room_id=room_id).delete()
        db.query(runtime.Memory).filter_by(room_id=room_id).delete()
        db.query(runtime.RelationshipEvent).filter_by(room_id=room_id).delete()
        db.query(runtime.MoodObservation).filter_by(room_id=room_id).delete()
        db.query(runtime.CharacterReflection).filter_by(room_id=room_id).delete()
        db.query(runtime.PromptTrace).filter_by(room_id=room_id).delete()
        db.query(runtime.RoomStoryState).filter_by(room_id=room_id).delete()
        db.query(runtime.RoomDocument).filter_by(room_id=room_id).delete()
        from ..roleplay_episode import PREFIX as EPISODE_PREFIX
        # Exact keys avoid SQL LIKE wildcards in externally supplied identifiers.
        for member_id in character_ids:
            db.query(runtime.AppSetting).filter_by(key=EPISODE_PREFIX+room_id+":"+member_id).delete()
        db.query(runtime.RoomMember).filter_by(room_id=room_id).delete()
        db.query(runtime.AppSetting).filter(
            runtime.AppSetting.key.in_(["room_topic:" + room_id, "tarot_session:" + room_id, "roleplay_continuity:" + room_id])
        ).delete()
        db.delete(room)
        db.flush()
        for document_id in attached_ids:
            runtime.purge_document_record(db, document_id)

    runtime.purge_room_record = purge_room_record


def bind_purge_character_record(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def purge_character_record(db, row):
        character_id = row.id
        user = row.user_id
        from ..character_social import purge_actor
        purge_actor(db,user,character_id)
        db.query(runtime.CharacterReactionReference).filter_by(
            character_id=character_id
        ).delete()
        db.query(runtime.CharacterReactionAsset).filter_by(
            character_id=character_id
        ).delete()
        db.query(runtime.CharacterVoiceSample).filter_by(
            character_id=character_id
        ).delete()
        publication = db.get(runtime.CharacterPublication, character_id)
        was_public = bool(publication and publication.is_public)
        assets = (
            db.query(runtime.CharacterExpressionAsset)
            .filter_by(character_id=character_id)
            .all()
        )
        dependents = (
            db.query(runtime.AppSetting)
            .filter(
                runtime.AppSetting.key.like("expression_source:%"),
                runtime.AppSetting.value == character_id,
            )
            .all()
        )
        identity_owners = (
            db.query(runtime.AppSetting)
            .filter(
                runtime.AppSetting.key.like("expression_identity_owner:%"),
                runtime.AppSetting.value == character_id,
            )
            .all()
        )
        image_owners = (
            db.query(runtime.AppSetting)
            .filter(
                runtime.AppSetting.key.like("expression_image_owner:%"),
                runtime.AppSetting.value == character_id,
            )
            .all()
        )
        if assets and dependents:
            replacement_id = dependents[0].key.removeprefix("expression_source:")
            for asset in assets:
                db.add(
                    runtime.CharacterExpressionAsset(
                        id=runtime.uid(),
                        character_id=replacement_id,
                        emotion=asset.emotion,
                        mime_type=asset.mime_type,
                        content=asset.content,
                    )
                )
            for dependent in dependents:
                dependent.value = replacement_id
                dependent.updated_at = runtime.now()
            for registry in identity_owners:
                registry.value = replacement_id
                registry.updated_at = runtime.now()
            for registry in image_owners:
                registry.value = replacement_id
                registry.updated_at = runtime.now()
            db.delete(dependents[0])
        else:
            for registry in [*identity_owners, *image_owners]:
                db.delete(registry)
        memberships = (
            db.query(runtime.RoomMember).filter_by(character_id=character_id).all()
        )
        for membership in memberships:
            room = db.get(runtime.Room, membership.room_id)
            if not room or room.user_id != user:
                continue
            room_members = db.query(runtime.RoomMember).filter_by(room_id=room.id).all()
            if len(room_members) <= 1:
                runtime.purge_room_record(db, room)
            else:
                message_ids = [
                    item.id
                    for item in db.query(runtime.Message)
                    .filter_by(room_id=room.id, character_id=character_id)
                    .all()
                ]
                runtime.archive_chat_before_delete(db, room.id, message_ids)
                runtime.purge_message_dependents(db, message_ids)
                db.query(runtime.Message).filter_by(
                    room_id=room.id, character_id=character_id
                ).delete()
                db.delete(membership)
                from ..roleplay_continuity import remove_character
                remove_character(db,room.id,character_id)
        db.query(runtime.CharacterKnowledge).filter_by(
            character_id=character_id
        ).delete()
        db.query(runtime.StyleExample).filter_by(character_id=character_id).delete()
        db.query(runtime.CharacterVersion).filter_by(character_id=character_id).delete()
        db.query(runtime.CharacterRating).filter_by(character_id=character_id).delete()
        db.query(runtime.CharacterReaction).filter_by(
            character_id=character_id
        ).delete()
        db.query(runtime.CharacterUsage).filter_by(character_id=character_id).delete()
        db.query(runtime.CharacterAsset).filter_by(character_id=character_id).delete()
        db.query(runtime.CharacterExpressionAsset).filter_by(
            character_id=character_id
        ).delete()
        db.query(runtime.CharacterPublication).filter_by(
            character_id=character_id
        ).delete()
        db.query(runtime.Memory).filter_by(character_id=character_id).delete()
        db.query(runtime.Relationship).filter(
            (runtime.Relationship.character_id == character_id)
            | (runtime.Relationship.other_character_id == character_id)
        ).delete(synchronize_session=False)
        db.query(runtime.CharacterState).filter_by(character_id=character_id).delete()
        db.query(runtime.RelationshipEvent).filter_by(
            character_id=character_id
        ).delete()
        db.query(runtime.CharacterReflection).filter_by(
            character_id=character_id
        ).delete()
        db.query(runtime.PromptTrace).filter_by(character_id=character_id).delete()
        db.query(runtime.ProcessingJob).filter_by(resource_id=character_id).delete()
        for key in (
            "expression_source:",
            "character_expression_identity:",
            "character_expression_image_hash:",
            "avatar_expression_version:",
            "character_clone_source:",
        ):
            setting = db.get(runtime.AppSetting, key + character_id)
            if setting:
                db.delete(setting)
        db.delete(row)
        db.flush()
        return {
            "was_public": was_public,
            "expression_source_preserved": bool(assets and dependents),
        }

    runtime.purge_character_record = purge_character_record
