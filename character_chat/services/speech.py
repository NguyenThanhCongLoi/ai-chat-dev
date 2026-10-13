"""services.speech: domain-specific application implementation.

Voice selection, provider requests and durable audio cache behavior.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind__stream_with_connect_retry(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.asynccontextmanager
    async def _stream_with_connect_retry(
        client, method, url, timeout, retry_timeout, **kwargs
    ):
        connected = False
        try:
            async with client.stream(
                method, url, timeout=timeout, **kwargs
            ) as response:
                connected = True
                yield response
                return
        except runtime.httpx.ConnectTimeout:
            if connected:
                raise
        async with client.stream(
            method, url, timeout=retry_timeout, **kwargs
        ) as response:
            yield response

    runtime._stream_with_connect_retry = _stream_with_connect_retry

    async def vbee_voices(api_base: str, api_key: str):
        cache_key = (api_base, runtime.hashlib.sha256(api_key.encode()).hexdigest())
        cached = runtime._vbee_voice_cache.get(cache_key)
        if cached and runtime.time.monotonic() - cached[0] < 600:
            return cached[1]
        try:
            timeout = runtime.httpx.Timeout(
                12, connect=runtime.voice_connect_timeout(5, 12)
            )
            retry_timeout = runtime.httpx.Timeout(12, connect=3)
            async with runtime.httpx.AsyncClient(
                timeout=timeout, follow_redirects=False
            ) as client:
                try:
                    response = await client.get(
                        runtime.vbee_voice_url(api_base),
                        headers={"Authorization": "Bearer " + api_key},
                        timeout=timeout,
                    )
                except runtime.httpx.ConnectTimeout:
                    response = await client.get(
                        runtime.vbee_voice_url(api_base),
                        headers={"Authorization": "Bearer " + api_key},
                        timeout=retry_timeout,
                    )
                if response.status_code == 401:
                    raise runtime.HTTPException(
                        502,
                        "API key TTS không hợp lệ; kiểm tra key của model TTS trong CMS",
                    )
                if response.status_code in (404, 405):
                    voices = []
                elif response.status_code >= 400:
                    raise runtime.HTTPException(
                        502,
                        f"Không tải được danh sách giọng TTS (HTTP {response.status_code})",
                    )
                else:
                    voices = runtime.normalize_voices(response.json())
        except runtime.httpx.TimeoutException:
            raise runtime.HTTPException(
                504, "API TTS phản hồi quá lâu khi tải danh sách giọng"
            )
        except runtime.httpx.RequestError as exc:
            raise runtime.HTTPException(
                502, f"Không kết nối được API TTS: {type(exc).__name__}"
            )
        except ValueError:
            raise runtime.HTTPException(
                502, "API TTS trả về danh sách giọng không hợp lệ"
            )
        runtime._vbee_voice_cache[cache_key] = (runtime.time.monotonic(), voices)
        return voices

    runtime.vbee_voices = vbee_voices

    def cms_voice_sample_spec(db, identifier):
        if identifier.startswith("preset:"):
            item = next(
                (
                    item
                    for item in runtime.effective_presets(db)
                    if item.preset_type == identifier.removeprefix("preset:")
                ),
                None,
            )
            if not item:
                raise runtime.HTTPException(404, "Preset not found")
            return item
        item = db.get(runtime.Character, identifier)
        if not item:
            raise runtime.HTTPException(404, "Character not found")
        return runtime.spec(item)

    runtime.cms_voice_sample_spec = cms_voice_sample_spec


def bind_message_speech_segments(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def message_speech_segments(message, text, db=None, character=None):
        try:
            metadata = runtime.json.loads(
                getattr(message, "speech_segments", "[]") or "[]"
            )
        except (ValueError, TypeError):
            metadata = []
        parts = runtime.sentence_segments(text, metadata)
        if text == message.text and not any(
            part["language"] == "unknown" for part in parts
        ):
            return parts
        # A translated opening may be too short for heuristic language detection.
        # Reuse the language of its stored translation, never the UI locale alone.
        if (
            db is not None
            and character is not None
            and (not metadata or text != message.text)
        ):
            item = runtime.spec(character)
            source = (
                item.initial_greeting.strip()
                or f"Hello, I'm {item.name}. It's nice to meet you."
            )
            code, _ = runtime.preferred_language(db, character.user_id)
            digest = runtime.hashlib.sha256(source.encode("utf-8")).hexdigest()
            cached = db.get(
                runtime.AppSetting,
                f"character_translation:v3:{character.user_id}:{code}:{digest}",
            )
            if cached and cached.value.strip() == text.strip():
                metadata = [{"text": text, "language": code}]
        return runtime.sentence_segments(text, metadata)

    runtime.message_speech_segments = message_speech_segments

    def message_speech_info(message, text, db=None, character=None):
        if character is None and db is not None:
            character = db.get(runtime.Character, message.character_id)
        item = (
            character
            if isinstance(character, runtime.CharacterSpec)
            else runtime.spec(character) if character else None
        )
        return runtime.speech_info(
            text, runtime.message_speech_segments(message, text, db, character), item
        )

    runtime.message_speech_info = message_speech_info

    def require_supported_voice_language(
        db, user, text=None, metadata=None, character_spec=None
    ):
        if text is None:
            return
        if not runtime.speech_info(text, metadata, character_spec)["speech_supported"]:
            raise runtime.HTTPException(
                422, "Voice is disabled or not configured for this spoken language."
            )

    runtime.require_supported_voice_language = require_supported_voice_language

    async def selected_speech_voice(
        db, item, gender, language, profile, api_base, api_key
    ):
        voice = runtime.configured_voice(item, language)
        if voice:
            return voice
        default = str(profile.get("tts_default_voice") or "").strip()
        strict = item.tts_voice_mode == "separate"
        if strict or gender != "unspecified" or not default:
            db.commit()
            try:
                voices = await runtime.vbee_voices(api_base, api_key)
                voice = runtime.select_voice(
                    voices, gender, language, strict_language=strict
                )
            except (runtime.HTTPException, runtime.httpx.HTTPError):
                if strict or not default:
                    raise
        if not strict:
            voice = voice or default
        if not voice:
            raise runtime.HTTPException(
                503, "No suitable voice configured for " + language
            )
        return voice

    runtime.selected_speech_voice = selected_speech_voice

    def speech_message_text(db, message, character):
        """Read the same greeting variant shown by the message-history endpoint."""
        room = db.get(runtime.Room, message.room_id)
        if (
            room
            and not db.query(runtime.Message.id)
            .filter(
                runtime.Message.room_id == message.room_id,
                runtime.Message.sender_type == "user",
                runtime.Message.created_at <= message.created_at,
            )
            .first()
        ):
            character_spec = runtime.spec(character)
            original = (
                character_spec.initial_greeting.strip()
                or f"Hello, I'm {character_spec.name}. It's nice to meet you."
            )
            digest = runtime.hashlib.sha256(original.encode("utf-8")).hexdigest()
            candidates = [original]
            for code in ("vi", "en", "zh", "ja", "ko", "my", "km"):
                cached = db.get(
                    runtime.AppSetting,
                    f"character_translation:v3:{room.user_id}:{code}:{digest}",
                )
                if cached:
                    candidates.append(cached.value)
            legacy = db.get(
                runtime.AppSetting, f"localized_greeting:v2:{character.id}:en:{digest}"
            )
            if legacy:
                candidates.append(legacy.value)
            if message.text.strip() in candidates:
                return runtime.localized_greeting(db, room.user_id, character_spec)
        return message.text

    runtime.speech_message_text = speech_message_text

    async def _prepare_message_speech(
        db: runtime.DBSession, message: runtime.Message, character: runtime.Character
    ):
        """Generate once per message and voice settings; replay from the stored audio."""
        assigned = next(
            (
                item
                for item in db.query(runtime.ModelConfig).filter_by(enabled=1).all()
                if "tts" in runtime.model_profile(db, item).get("purposes", [])
            ),
            None,
        )
        if not assigned:
            raise runtime.HTTPException(503, "Chưa phân công model TTS trong CMS")
        profile = runtime.model_profile(db, assigned)
        character_spec = runtime.spec(character)
        api_key = runtime.credential_for_model(db, assigned)
        if not api_key:
            raise runtime.HTTPException(
                503, "Model TTS chưa có API key cho API base này"
            )
        api_base = runtime.normalized_api_base(assigned.api_base)
        gender = runtime.character_voice_gender(character_spec)
        speech_text = runtime.speech_message_text(db, message, character)
        segments = runtime.message_speech_segments(message, speech_text, db, character)
        runtime.require_supported_voice_language(
            db, character.user_id, speech_text, segments, character_spec
        )
        speech_base = runtime.speech_api_base(api_base)
        signature = runtime.speech_cache_signature(
            db, character, speech_text, (assigned, profile, api_key)
        )
        cached = db.get(runtime.MessageSpeech, message.id)
        if cached and cached.signature == signature and cached.content:
            return cached.content, cached.mime_type
        dialogue = runtime.re.sub(
            r"\*\*[^*\n]+\*\*|\*[^*\n]+\*",
            " ",
            runtime.format_roleplay_reply(speech_text),
        )
        dialogue = runtime.re.sub(r"\s+", " ", dialogue).strip()
        if not dialogue:
            raise runtime.HTTPException(422, "Câu trả lời không có lời thoại để đọc")
        if len(dialogue) > 4000:
            raise runtime.HTTPException(413, "Câu trả lời quá dài để đọc trong một lần")
        language = segments[0]["language"]
        if len({part["language"] for part in segments}) > 1:
            async for _ in runtime.multilingual_speech_events(
                message.id, character.user_id, segments, speech_text, signature
            ):
                pass
            db.expire_all()
            cached = db.get(runtime.MessageSpeech, message.id)
            if not cached or cached.signature != signature:
                raise runtime.HTTPException(
                    502, "Multilingual voice preparation failed"
                )
            return cached.content, cached.mime_type
        voice = await runtime.selected_speech_voice(
            db, character_spec, gender, language, profile, api_base, api_key
        )
        payload = {
            "model": assigned.model_id,
            "input": dialogue,
            "voice": voice,
            "response_format": "mp3",
        }
        db.commit()
        started = runtime.time.monotonic()
        try:
            timeout = runtime.httpx.Timeout(
                30, connect=runtime.voice_connect_timeout(8, 30)
            )
            retry_timeout = runtime.httpx.Timeout(30, connect=3)
            async with runtime.httpx.AsyncClient(
                timeout=timeout, follow_redirects=False
            ) as client:
                async with runtime._stream_with_connect_retry(
                    client,
                    "POST",
                    speech_base + "/audio/speech",
                    timeout,
                    retry_timeout,
                    headers={
                        "Authorization": "Bearer " + api_key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                    json=payload,
                ) as upstream:
                    if upstream.status_code >= 400:
                        detail = (await upstream.aread()).decode("utf-8", "replace")[
                            :300
                        ]
                        raise runtime.HTTPException(
                            502, f"TTS gateway HTTP {upstream.status_code}: {detail}"
                        )
                    content_type = (
                        upstream.headers.get("content-type", "")
                        .split(";", 1)[0]
                        .lower()
                    )
                    if not (
                        content_type.startswith("audio/")
                        or content_type == "application/octet-stream"
                    ):
                        raise runtime.HTTPException(
                            502, "TTS gateway không trả về audio"
                        )
                    parts = []
                    size = 0
                    async for chunk in upstream.aiter_bytes():
                        size += len(chunk)
                        if size > 12 * 1024 * 1024:
                            raise runtime.HTTPException(
                                502, "Audio TTS vượt giới hạn 12 MB"
                            )
                        parts.append(chunk)
                    if not size:
                        raise runtime.HTTPException(
                            502, "TTS gateway trả về audio rỗng"
                        )
        except runtime.httpx.TimeoutException:
            raise runtime.HTTPException(504, "TTS gateway phản hồi quá lâu")
        except runtime.httpx.RequestError as exc:
            raise runtime.HTTPException(
                502, f"Không kết nối được TTS gateway: {type(exc).__name__}"
            )
        content = b"".join(parts)
        mime_type = content_type if content_type.startswith("audio/") else "audio/mpeg"
        db.merge(
            runtime.MessageSpeech(
                message_id=message.id,
                signature=signature,
                mime_type=mime_type,
                content=content,
            )
        )
        db.add(
            runtime.VoiceEvent(
                id=runtime.uid(),
                message_id=message.id,
                character_id=character.id,
                user_id=character.user_id,
                event_type="generation",
                status="success",
                model_id=assigned.model_id,
                voice_id=voice,
                latency_ms=round((runtime.time.monotonic() - started) * 1000),
                audio_bytes=len(content),
            )
        )
        db.commit()
        return content, mime_type

    runtime._prepare_message_speech = _prepare_message_speech

    async def prepare_message_speech(
        db: runtime.DBSession, message: runtime.Message, character: runtime.Character
    ):
        started = runtime.time.monotonic()
        try:
            return await runtime._prepare_message_speech(db, message, character)
        except Exception as exc:
            # Logging must not replace the original TTS error shown to the user.
            try:
                db.rollback()
                assigned = next(
                    (
                        item
                        for item in db.query(runtime.ModelConfig)
                        .filter_by(enabled=1)
                        .all()
                        if "tts" in runtime.model_profile(db, item).get("purposes", [])
                    ),
                    None,
                )
                detail = (
                    exc.detail if isinstance(exc, runtime.HTTPException) else str(exc)
                )
                db.add(
                    runtime.VoiceEvent(
                        id=runtime.uid(),
                        message_id=message.id,
                        character_id=character.id,
                        user_id=character.user_id,
                        event_type="generation",
                        status="error",
                        model_id=assigned.model_id if assigned else "",
                        voice_id=runtime.spec(character).tts_voice_id,
                        latency_ms=round((runtime.time.monotonic() - started) * 1000),
                        error=str(detail)[:500],
                    )
                )
                db.commit()
            except Exception:
                db.rollback()
            raise

    runtime.prepare_message_speech = prepare_message_speech

    def speech_cache_signature(db, character, speech_text, configuration=None):
        if configuration is not None:
            assigned, profile, api_key = configuration
        else:
            assigned = next(
                (
                    item
                    for item in db.query(runtime.ModelConfig).filter_by(enabled=1).all()
                    if "tts" in runtime.model_profile(db, item).get("purposes", [])
                ),
                None,
            )
            if not assigned:
                raise runtime.HTTPException(503, "TTS model is not assigned")
            profile = runtime.model_profile(db, assigned)
            api_key = runtime.credential_for_model(db, assigned)
        item = runtime.spec(character)
        if not api_key:
            raise runtime.HTTPException(503, "TTS model has no API key")
        return runtime.hashlib.sha256(
            runtime.json.dumps(
                [
                    speech_text,
                    assigned.model_id,
                    runtime.normalized_api_base(assigned.api_base),
                    runtime.hashlib.sha256(api_key.encode()).hexdigest(),
                    item.tts_voice_id,
                    item.tts_voice_mode,
                    item.tts_voice_vi,
                    item.tts_voice_en,
                    {key: val.model_dump() for key, val in item.tts_languages.items()},
                    runtime.character_voice_gender(item),
                    item.speech.preferred_language,
                    profile.get("tts_default_voice"),
                    "content-language-v2-short-pauses",
                ],
                ensure_ascii=False,
            ).encode()
        ).hexdigest()

    runtime.speech_cache_signature = speech_cache_signature


def bind_multilingual_speech_events(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    async def multilingual_speech_events(
        message_id, user, segments, original, signature
    ):
        frames = []
        rate = 0
        try:
            for part in segments:
                with runtime.Session() as db:
                    response = await runtime._roleplay_speech_stream(
                        message_id,
                        db,
                        user,
                        segment_text=part["text"],
                        segment_language=part["language"],
                    )
                    pending = ""
                    complete = False
                    async for chunk in response.body_iterator:
                        pending += chunk.decode() if isinstance(chunk, bytes) else chunk
                        while "\n\n" in pending:
                            block, pending = pending.split("\n\n", 1)
                            data = "\n".join(
                                line[5:].strip()
                                for line in block.splitlines()
                                if line.startswith("data:")
                            )
                            if not data:
                                continue
                            event = runtime.json.loads(data)
                            if event.get("error"):
                                raise RuntimeError("Voice segment failed")
                            if event.get("type") == "speech.audio.delta":
                                next_rate = int(event["sample_rate"])
                                if rate and rate != next_rate:
                                    raise RuntimeError("TTS sample rate changed")
                                rate = next_rate
                                frames.append(runtime.base64.b64decode(event["audio"]))
                                if sum(map(len, frames)) > 12 * 1024 * 1024:
                                    raise RuntimeError("Audio exceeds limit")
                                yield "data: " + runtime.json.dumps(event) + "\n\n"
                            elif event.get("type") == "speech.audio.done":
                                complete = True
                    if not complete:
                        raise RuntimeError("Incomplete voice segment")
            output = runtime.io.BytesIO()
            with runtime.wave.open(output, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(rate)
                wav.writeframes(b"".join(frames))
            with runtime.Session() as db:
                message = db.get(runtime.Message, message_id)
                character = (
                    db.get(runtime.Character, message.character_id) if message else None
                )
                if (
                    message
                    and character
                    and runtime.speech_message_text(db, message, character) == original
                    and runtime.speech_cache_signature(db, character, original)
                    == signature
                ):
                    db.merge(
                        runtime.MessageSpeech(
                            message_id=message_id,
                            signature=signature,
                            mime_type="audio/wav",
                            content=output.getvalue(),
                        )
                    )
                    db.commit()
            yield 'data: {"type":"speech.audio.done"}\n\n'
        except Exception:
            yield 'data: {"error":{"message":"Could not complete multilingual voice"}}\n\n'

    runtime.multilingual_speech_events = multilingual_speech_events


def bind__roleplay_speech_stream(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    async def _roleplay_speech_stream(
        message_id, db, user, segment_text=None, segment_language=None
    ):
        message = db.get(runtime.Message, message_id)
        if (
            not message
            or message.sender_type != "character"
            or not message.character_id
        ):
            raise runtime.HTTPException(404, "No character reply found")
        room = db.get(runtime.Room, message.room_id)
        character = db.get(runtime.Character, message.character_id)
        if (
            not room
            or room.user_id != user
            or not character
            or character.user_id != user
        ):
            raise runtime.HTTPException(404, "No character reply found")
        speech_text = (
            segment_text
            if segment_text is not None
            else runtime.speech_message_text(db, message, character)
        )
        segments = (
            [
                {
                    "text": speech_text,
                    "language": runtime.detect_speech_language(
                        speech_text, segment_language
                    ),
                }
            ]
            if segment_text is not None
            else runtime.message_speech_segments(message, speech_text, db, character)
        )
        if segment_text is not None or message.finish_status != "generating":
            runtime.require_supported_voice_language(
                db, user, speech_text, segments, runtime.spec(character)
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
            raise runtime.HTTPException(503, "TTS model is not assigned")
        profile = runtime.model_profile(db, assigned)
        character_spec = runtime.spec(character)
        api_key = runtime.credential_for_model(db, assigned)
        if not api_key:
            raise runtime.HTTPException(503, "TTS model has no API key")
        api_base = runtime.normalized_api_base(assigned.api_base)
        gender = runtime.character_voice_gender(character_spec)
        speech_text = (
            segment_text
            if segment_text is not None
            else runtime.speech_message_text(db, message, character)
        )
        segments = (
            [
                {
                    "text": speech_text,
                    "language": runtime.detect_speech_language(
                        speech_text, segment_language
                    ),
                }
            ]
            if segment_text is not None
            else runtime.message_speech_segments(message, speech_text, db, character)
        )
        if segment_text is not None or message.finish_status != "generating":
            runtime.require_supported_voice_language(
                db, user, speech_text, segments, runtime.spec(character)
            )
        signature = runtime.speech_cache_signature(
            db, character, speech_text, (assigned, profile, api_key)
        )
        cached = db.get(runtime.MessageSpeech, message.id)
        if (
            segment_text is None
            and cached
            and cached.signature == signature
            and cached.content
        ):
            return runtime.Response(
                content=cached.content,
                media_type=cached.mime_type,
                headers={"Cache-Control": "private, no-store"},
            )
        if segment_text is None:
            run = db.get(runtime.MessageSpeechRun, message_id)
            if (
                run
                and run.signature
                == runtime.speech_cache_signature(
                    db, character, "", (assigned, profile, api_key)
                )
                and run.status == "generating"
            ):
                db.commit()
                return runtime.StreamingResponse(
                    runtime.replay_parts(
                        runtime.sys.modules[runtime.__name__], message_id, run.signature
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache, no-transform",
                        "X-Accel-Buffering": "no",
                    },
                )
            if message.finish_status == "generating":
                raise runtime.HTTPException(409, "Voice is not ready for this response")
        if len(runtime.spoken_text(speech_text)) > 4000:
            raise runtime.HTTPException(413, "Voice text exceeds 4000 characters")
        if segment_text is None and len({part["language"] for part in segments}) > 1:
            return runtime.StreamingResponse(
                runtime.multilingual_speech_events(
                    message_id, user, segments, speech_text, signature
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache, no-transform",
                    "X-Accel-Buffering": "no",
                },
            )
        dialogue = runtime.re.sub(
            r"\*\*[^*\n]+\*\*|\*[^*\n]+\*",
            " ",
            runtime.format_roleplay_reply(speech_text),
        )
        dialogue = runtime.re.sub(r"\s+", " ", dialogue).strip()
        if not dialogue:
            raise runtime.HTTPException(422, "Character reply has no spoken dialogue")
        if len(dialogue) > 4000:
            raise runtime.HTTPException(
                413, "Character reply is too long for one speech request"
            )
        language = segments[0]["language"]
        voice = await runtime.selected_speech_voice(
            db, character_spec, gender, language, profile, api_base, api_key
        )
        payload = {
            "model": assigned.model_id,
            "input": dialogue,
            "voice": voice,
            "response_format": "pcm",
            "stream_format": "sse",
            "speed": 1.0,
            "pitch": 1.0,
        }
        model_id = assigned.model_id
        character_id = character.id
        original_message_text = message.text
        db.commit()

        async def events():
            started = runtime.time.monotonic()
            frames = []
            size = 0
            sample_rate = 0
            pause_compactor = None
            try:
                timeout = runtime.httpx.Timeout(
                    30, connect=runtime.voice_connect_timeout(8, 30)
                )
                retry_timeout = runtime.httpx.Timeout(30, connect=3)
                async with runtime.httpx.AsyncClient(
                    timeout=timeout, follow_redirects=False
                ) as client:
                    async with runtime._stream_with_connect_retry(
                        client,
                        "POST",
                        runtime.speech_api_base(api_base) + "/audio/speech",
                        timeout,
                        retry_timeout,
                        headers={
                            "Authorization": "Bearer " + api_key,
                            "Content-Type": "application/json",
                            "Accept": "text/event-stream",
                        },
                        json=payload,
                    ) as upstream:
                        if upstream.status_code >= 400:
                            detail = (await upstream.aread()).decode(
                                "utf-8", "replace"
                            )[:300]
                            raise RuntimeError(
                                f"TTS gateway HTTP {upstream.status_code}: {detail}"
                            )
                        if (
                            not upstream.headers.get("content-type", "")
                            .lower()
                            .startswith("text/event-stream")
                        ):
                            raise RuntimeError(
                                "TTS gateway did not return an SSE stream"
                            )
                        data_lines = []
                        async for line in upstream.aiter_lines():
                            if line:
                                if line.startswith("data:"):
                                    data_lines.append(line[5:].strip())
                                continue
                            if not data_lines:
                                continue
                            event = runtime.json.loads("\n".join(data_lines))
                            data_lines = []
                            if not isinstance(event, dict):
                                raise ValueError("Invalid TTS event")
                            if event.get("error"):
                                detail = event["error"]
                                raise RuntimeError(
                                    str(detail.get("message") or detail)
                                    if isinstance(detail, dict)
                                    else str(detail)
                                )
                            kind = event.get("type")
                            if kind == "speech.audio.delta":
                                if event.get("format") != "pcm":
                                    raise ValueError("TTS stream format must be PCM")
                                rate = int(event.get("sample_rate") or 0)
                                if not 8000 <= rate <= 96000 or (
                                    sample_rate and rate != sample_rate
                                ):
                                    raise ValueError("Invalid TTS sample rate")
                                sample_rate = rate
                                chunk = runtime.base64.b64decode(
                                    event.get("audio") or "", validate=True
                                )
                                if not chunk or len(chunk) % 2:
                                    raise ValueError("Invalid PCM16 audio chunk")
                                size += len(chunk)
                                if size > 12 * 1024 * 1024:
                                    raise ValueError("TTS audio exceeds 12 MB")
                                if pause_compactor is None:
                                    from character_chat.voice_pauses import (
                                        PcmPauseCompactor,
                                    )

                                    pause_compactor = PcmPauseCompactor(rate)
                                chunk = pause_compactor.feed(chunk)
                                if chunk:
                                    frames.append(chunk)
                                    event["audio"] = runtime.base64.b64encode(
                                        chunk
                                    ).decode()
                                    yield "data: " + runtime.json.dumps(
                                        event, separators=(",", ":")
                                    ) + "\n\n"
                            elif kind == "speech.audio.done":
                                if not frames:
                                    raise ValueError(
                                        "TTS stream finished without audio"
                                    )
                                output = runtime.io.BytesIO()
                                with runtime.wave.open(output, "wb") as wav:
                                    wav.setnchannels(1)
                                    wav.setsampwidth(2)
                                    wav.setframerate(sample_rate)
                                    wav.writeframes(b"".join(frames))
                                content = output.getvalue()
                                # A deleted/regenerated message must not acquire old
                                # audio after an in-flight preparation finishes.
                                current_text = (
                                    db.query(runtime.Message.text)
                                    .filter(runtime.Message.id == message_id)
                                    .scalar()
                                )
                                if (
                                    segment_text is None
                                    and current_text == original_message_text
                                ):
                                    db.merge(
                                        runtime.MessageSpeech(
                                            message_id=message_id,
                                            signature=signature,
                                            mime_type="audio/wav",
                                            content=content,
                                        )
                                    )
                                db.add(
                                    runtime.VoiceEvent(
                                        id=runtime.uid(),
                                        message_id=message_id,
                                        character_id=character_id,
                                        user_id=user,
                                        event_type="generation",
                                        status="success",
                                        model_id=model_id,
                                        voice_id=voice,
                                        latency_ms=round(
                                            (runtime.time.monotonic() - started) * 1000
                                        ),
                                        audio_bytes=len(content),
                                    )
                                )
                                db.commit()
                                yield "data: " + runtime.json.dumps(
                                    event, separators=(",", ":")
                                ) + "\n\n"
                                return
                        raise RuntimeError("TTS stream ended without speech.audio.done")
            except runtime.asyncio.CancelledError:
                db.rollback()
                raise
            except Exception as exc:
                db.rollback()
                db.add(
                    runtime.VoiceEvent(
                        id=runtime.uid(),
                        message_id=message_id,
                        character_id=character_id,
                        user_id=user,
                        event_type="generation",
                        status="error",
                        model_id=model_id,
                        voice_id=voice,
                        latency_ms=round((runtime.time.monotonic() - started) * 1000),
                        audio_bytes=size,
                        error=str(exc)[:500],
                    )
                )
                db.commit()
                yield "data: " + runtime.json.dumps(
                    {"error": {"message": str(exc)}}
                ) + "\n\n"

        return runtime.StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    runtime._roleplay_speech_stream = _roleplay_speech_stream
