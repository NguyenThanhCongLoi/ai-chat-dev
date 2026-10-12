"""api.voice_admin: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_admin_voice_sample(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.get("/v1/admin/characters/{identifier}/voice/sample/{target}")
    def admin_voice_sample(
        identifier: str,
        target: str,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        from character_chat.voice_samples import (
            validate_target,
            stored_sample,
            assignment_voice,
        )

        validate_target(target)
        character_spec = runtime.cms_voice_sample_spec(db, identifier)
        row = stored_sample(db, identifier, target, character_spec, metadata_only=True)
        return {
            "target": target,
            "voice_id": assignment_voice(character_spec, target),
            "available": bool(row),
            "filename": row.filename if row else "",
            "sample_language": row.sample_language if row else "",
            "ref_text": row.ref_text if row else "",
            "updated_at": row.updated_at if row else "",
        }

    runtime.admin_voice_sample = admin_voice_sample

    @runtime.app.get("/v1/admin/characters/{identifier}/voice/sample/{target}/audio")
    def admin_voice_sample_audio(
        identifier: str,
        target: str,
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        from character_chat.voice_samples import validate_target, stored_sample

        validate_target(target)
        row = stored_sample(
            db, identifier, target, runtime.cms_voice_sample_spec(db, identifier)
        )
        if not row:
            raise runtime.HTTPException(404, "Voice reference sample not found")
        return runtime.Response(
            content=row.content,
            media_type=row.mime_type,
            headers={
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    runtime.admin_voice_sample_audio = admin_voice_sample_audio

    @runtime.app.post("/v1/admin/characters/{identifier}/voice/clone")
    async def admin_clone_character_voice(
        identifier: str,
        background: runtime.BackgroundTasks,
        audio: runtime.UploadFile = runtime.File(...),
        name: str = runtime.Form(...),
        gender: str = runtime.Form("unspecified"),
        language: str = runtime.Form("vi"),
        ref_text: str = runtime.Form(""),
        enhance_audio: bool = runtime.Form(False),
        target: str = runtime.Form("shared"),
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        if identifier.startswith("preset:"):
            preset_type = identifier.removeprefix("preset:")
            if not any(
                item.preset_type == preset_type
                for item in runtime.effective_presets(db)
            ):
                raise runtime.HTTPException(404, "Preset not found")
        elif not db.get(runtime.Character, identifier):
            raise runtime.HTTPException(404, "Character not found")
        if target not in {"shared", "vi", "en"}:
            raise runtime.HTTPException(400, "Invalid voice assignment")
        name = name.strip()
        if not name or len(name) > 120:
            raise runtime.HTTPException(400, "Tên giọng phải từ 1 đến 120 ký tự.")
        if gender not in ("male", "female", "unspecified") or language not in (
            "vi",
            "en",
        ):
            raise runtime.HTTPException(
                400, "Giới tính hoặc ngôn ngữ giọng không hợp lệ."
            )
        if len(ref_text) > 20000:
            raise runtime.HTTPException(400, "Nội dung mẫu tối đa 20000 ký tự.")
        filename = runtime.Path((audio.filename or "").replace(chr(92), "/")).name
        extension = runtime.Path(filename).suffix.lower()
        formats = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }
        content = await audio.read(20 * 1024 * 1024 + 1)
        if not content or len(content) > 20 * 1024 * 1024:
            raise runtime.HTTPException(
                413, "Mẫu giọng phải có nội dung và không vượt quá 20 MB."
            )
        valid = (
            (
                extension == ".wav"
                and content.startswith(b"RIFF")
                and content[8:12] == b"WAVE"
            )
            or (
                extension == ".mp3"
                and (
                    content.startswith(b"ID3")
                    or len(content) > 1
                    and content[0] == 255
                    and content[1] & 224 == 224
                )
            )
            or (extension == ".flac" and content.startswith(b"fLaC"))
            or (extension == ".ogg" and content.startswith(b"OggS"))
            or (extension == ".m4a" and content[4:8] == b"ftyp")
        )
        if extension not in formats or not valid:
            raise runtime.HTTPException(
                400, "Hãy chọn file âm thanh WAV, MP3, FLAC, OGG hoặc M4A hợp lệ."
            )
        assigned = next(
            (
                item
                for item in db.query(runtime.ModelConfig).filter_by(enabled=1).all()
                if "tts" in runtime.model_profile(db, item).get("purposes", [])
            ),
            None,
        )
        if not assigned:
            raise runtime.HTTPException(503, "Hãy phân công model TTS trong CMS trước.")
        api_base = runtime.normalized_api_base(assigned.api_base)
        api_key = runtime.credential_for_model(db, assigned)
        if not api_key:
            raise runtime.HTTPException(503, "Model TTS chưa có API key.")
        db.commit()
        from character_chat.voice_clone import upload_voice

        voice_id = await upload_voice(
            api_base,
            api_key,
            name,
            content,
            filename,
            formats[extension],
            gender,
            language,
            ref_text,
            enhance_audio,
        )
        changes = {
            "tts_gender": gender,
            "tts_voice_mode": "shared" if target == "shared" else "separate",
        }
        changes["tts_voice_id" if target == "shared" else "tts_voice_" + target] = (
            voice_id
        )
        changes[
            "tts_voice_source" if target == "shared" else "tts_voice_source_" + target
        ] = "clone"
        if identifier.startswith("preset:"):
            updated = runtime.admin_update_preset(preset_type, changes, None, db)
        else:
            updated = runtime.admin_update_character(identifier, changes, None, db)
        from character_chat.voice_samples import save_sample

        save_sample(
            db,
            identifier,
            target,
            voice_id,
            filename,
            formats[extension],
            content,
            language,
            ref_text,
        )
        runtime._vbee_voice_cache.clear()
        runtime.queue_reaction_generation(db, background, identifier, target)
        return {"voice_id": voice_id, "character": updated}

    runtime.admin_clone_character_voice = admin_clone_character_voice

    @runtime.app.get("/v1/admin/tts/voices")
    async def admin_tts_voices(
        _: None = runtime.Depends(runtime.docs_auth),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        assigned = next(
            (
                item
                for item in db.query(runtime.ModelConfig).filter_by(enabled=1).all()
                if "tts" in runtime.model_profile(db, item).get("purposes", [])
            ),
            None,
        )
        if not assigned:
            raise runtime.HTTPException(503, "Hãy phân công model TTS trong CMS trước")
        api_base = runtime.normalized_api_base(assigned.api_base)
        api_key = runtime.credential_for_model(db, assigned)
        if not api_key:
            raise runtime.HTTPException(
                503, "Hãy cấu hình API key Vbee cho model TTS trong CMS"
            )
        return {
            "model": assigned.model_id,
            "voices": await runtime.vbee_voices(api_base, api_key),
        }

    runtime.admin_tts_voices = admin_tts_voices
