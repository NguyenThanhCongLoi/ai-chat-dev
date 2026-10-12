"""services.rooms: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_preferred_language(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def preferred_language(db, user):
        profile = db.get(runtime.UserProfile, user)
        code = (
            profile.language
            if profile
            and runtime.re.fullmatch(
                r"[a-z]{2,3}(?:-[A-Z]{2})?", profile.language or ""
            )
            else "vi"
        )
        return code, runtime.SUPPORTED_LANGUAGES.get(code, code)

    runtime.preferred_language = preferred_language

    def localized_greeting(db, user, character):
        """Translate opening speech per account/language; retain authored names/actions."""
        greeting = (
            character.initial_greeting.strip()
            or f"Hello, I'm {character.name}. It's nice to meet you."
        )
        code, _ = runtime.preferred_language(db, user)
        result = runtime.translate_interface_content(
            {"language": code, "texts": [greeting], "kind": "character"}, db, user
        )
        return result["translations"][0] if not result.get("failures") else greeting

    runtime.localized_greeting = localized_greeting

    def room_is_public(db, room_id):
        setting = db.get(runtime.AppSetting, "room_public:" + room_id)
        return bool(setting and setting.value == "true")

    runtime.room_is_public = room_is_public

    def system_room_source(db, character, templates=None):
        """Only an unchanged canonical system card can bypass personal publication."""
        if (
            not character
            or db.get(runtime.AppSetting, "character_override:" + character.id)
            or db.get(runtime.CharacterAsset, character.id)
        ):
            return None
        card = runtime.spec(character)
        if card.creation_type != "preset" or not card.preset_type:
            return None
        source = next(
            (
                item
                for item in (
                    templates
                    if templates is not None
                    else runtime.effective_presets(db)
                )
                if item.preset_type == card.preset_type
                and runtime.preset_home_section(db, item) != "hidden"
            ),
            None,
        )
        if source is None:
            return None
        actual = card.model_dump(exclude={"id"})
        expected = source.model_dump(exclude={"id"})
        if (
            not source.system_prompt.strip()
            and card.system_prompt == runtime.default_character_prompt(source)
        ):
            actual["system_prompt"] = source.system_prompt
        return source if actual == expected else None

    runtime.system_room_source = system_room_source

    def room_member_shareable(db, character, templates=None):
        if not character:
            return False
        publication = db.get(runtime.CharacterPublication, character.id)
        return (
            bool(publication and publication.is_public)
            or runtime.system_room_source(db, character, templates) is not None
        )

    runtime.room_member_shareable = room_member_shareable

    def public_room_members(db, room):
        ids = [
            item.character_id
            for item in db.query(runtime.RoomMember).filter_by(room_id=room.id)
        ]
        templates = runtime.effective_presets(db)
        return len(ids) >= 2 and all(
            runtime.room_member_shareable(db, db.get(runtime.Character, id), templates)
            for id in ids
        )

    runtime.public_room_members = public_room_members
