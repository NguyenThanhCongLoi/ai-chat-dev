"""api.roleplay_chat: domain-specific application implementation.

Single/group roleplay responses, regeneration and the original SSE/TTS sequencing.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_send_message(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.post("/v1/rooms/{room_id}/messages")
    def send_message(
        room_id: str,
        data: runtime.MessageIn,
        background: runtime.BackgroundTasks,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        try:
            runtime.ensure_safe_content(data.message)
        except ValueError as exc:
            raise runtime.HTTPException(400, str(exc))
        runtime.owned(db, runtime.Room, room_id, user)
        ids = [
            m.character_id
            for m in db.query(runtime.RoomMember).filter_by(room_id=room_id).all()
        ]
        chars = [
            runtime.spec(runtime.owned(db, runtime.Character, id, user)) for id in ids
        ]
        try:
            group_plan = runtime.plan_room(
                db, room_id, data.message, chars, data.speaker_mode
            )
            selected = group_plan.speakers
        except ValueError as exc:
            raise runtime.HTTPException(400, str(exc))
        user_msg = runtime.Message(
            id=runtime.uid(), room_id=room_id, sender_type="user", text=data.message
        )
        db.add(user_msg)
        db.commit()
        results = []
        for speaker_index, c in enumerate(selected):
            suggest_enabled = speaker_index == len(selected) - 1
            started = runtime.time.monotonic()
            model_meta = {
                "primary_model": runtime.llm.model,
                "primary_model_config_id": (
                    runtime.llm.model
                    if runtime.llm.model in runtime.llm.model_wire_ids
                    else ""
                ),
                "fallback_model": runtime.llm.fallback_model,
                "fallback_used": False,
            }
            try:
                prompt, sources = runtime.assemble(db, user, room_id, c, data.message)
                if instruction := group_plan.instruction(c.id):
                    prompt.append({"role": "system", "content": instruction})
                db.commit()
                temperature, max_tokens = runtime.roleplay_model_options(
                    db, runtime.llm.model, c.speech.verbosity == "short"
                )
                suggest_temperature, suggest_tokens = runtime.roleplay_model_options(
                    db, runtime.llm.purpose_models.get("suggestion"), True
                )
                pool = runtime.concurrent.futures.ThreadPoolExecutor(max_workers=2)
                try:
                    answer_future = pool.submit(
                        runtime.llm.chat_with_meta,
                        runtime.roleplay_output_prompt(prompt),
                        temperature,
                        max_tokens,
                        profile_mode=(
                            "short" if c.speech.verbosity == "short" else "normal"
                        ),
                    )
                    suggestion_started = runtime.time.monotonic()
                    if suggest_enabled:
                        suggestion_future = pool.submit(
                            runtime.llm.chat_with_meta,
                            runtime.suggestion_prompt(
                                prompt,
                                c,
                                data.message,
                                runtime.previous_roleplay_suggestions(db, room_id),
                            ),
                            suggest_temperature,
                            suggest_tokens,
                            runtime.llm.purpose_models.get("suggestion"),
                            runtime.llm.purpose_models.get("suggestion_fallback") or "",
                            runtime.llm.purpose_models.get("suggestion_fallback_2")
                            or "",
                            profile_mode="short",
                            gateway_timeout_cap_seconds=8,
                        )
                    else:
                        suggestion_future = runtime.concurrent.futures.Future()
                        suggestion_future.set_result(("", {}))
                    answer, model_meta = answer_future.result()
                    answer, speech_parts = runtime.parse_language_reply(answer)
                    answer = runtime.format_roleplay_reply(answer)
                    answer_latency_ms = int((runtime.time.monotonic() - started) * 1000)
                    suggestion_meta = runtime.roleplay_suggestion_initial_meta()
                    suggestion_error = ""
                    try:
                        suggestion_raw, suggestion_meta = suggestion_future.result(
                            timeout=runtime.post_stream_suggestion_wait()
                        )
                        suggestions = runtime.parse_suggestions(suggestion_raw)
                    except Exception as exc:
                        suggestions = []
                        suggestion_error = runtime.roleplay_suggestion_error(exc)
                        suggestion_meta["fallback_reason"] = suggestion_error
                        suggestion_future.cancel()
                finally:
                    pool.shutdown(wait=False, cancel_futures=True)
                if suggest_enabled:
                    suggestions, suggestion_meta = runtime.finalize_suggestions(
                        suggestions,
                        data.message,
                        runtime.preferred_language(db, user)[0],
                        suggestion_meta,
                    )
                else:
                    suggestions = []
                if (
                    not db.query(runtime.Message.id)
                    .filter_by(id=user_msg.id, room_id=room_id)
                    .first()
                ):
                    raise runtime.HTTPException(404, "Room was deleted")
                emotion = runtime.reply_expression(answer)
                msg = runtime.Message(
                    id=runtime.uid(),
                    room_id=room_id,
                    sender_type="character",
                    character_id=c.id,
                    text=answer,
                    reply_to_message_id=user_msg.id,
                    sources=runtime.json.dumps(sources),
                    emotion=emotion,
                    speech_segments=runtime.json.dumps(
                        speech_parts, ensure_ascii=False
                    ),
                )
                db.add(msg)
                runtime.save_suggestions(db, msg.id, suggestions)
                runtime.update_relationship(
                    runtime.relationship(db, user, c.id), data.message
                )
                from ..character_social import record_turn
                record_turn(db,user,room_id,user_msg.id)
                db.commit()
                runtime.save_ai_request_log(
                    db,
                    user,
                    room_id,
                    user_msg.id,
                    msg.id,
                    "roleplay",
                    "response",
                    {**model_meta, "group_routing": group_plan.metadata()},
                    answer_latency_ms,
                    output_text=answer,
                )
                if suggest_enabled:
                    runtime.save_ai_request_log(
                        db,
                        user,
                        room_id,
                        user_msg.id,
                        msg.id,
                        "roleplay",
                        "suggestion",
                        suggestion_meta,
                        int((runtime.time.monotonic() - suggestion_started) * 1000),
                        suggestion_error,
                        " | ".join(suggestions),
                    )
                db.commit()
                speech_ready = False
                speech_error = ""
                results.append(
                    {
                        "id": msg.id,
                        "sender_type": "character",
                        "character_id": c.id,
                        "character_name": c.name,
                        "text": answer,
                        "sources": sources,
                        "suggestions": suggestions,
                        "emotion": emotion,
                        "model_used": model_meta.get(
                            "actual_model", model_meta.get("primary_model", "")
                        ),
                        "latency_ms": answer_latency_ms,
                        "speech_ready": speech_ready,
                        "speech_error": speech_error,
                        **runtime.message_speech_info(
                            msg,
                            answer,
                            db,
                            runtime.owned(db, runtime.Character, c.id, user),
                        ),
                    }
                )
            except Exception as exc:
                runtime.save_ai_request_log(
                    db,
                    user,
                    room_id,
                    user_msg.id,
                    None,
                    "roleplay",
                    "response",
                    {**model_meta, "group_routing": group_plan.metadata()},
                    int((runtime.time.monotonic() - started) * 1000),
                    str(exc),
                    character_id=c.id,
                )
                db.commit()
                if not results:
                    raise runtime.HTTPException(503, f"Chat model unavailable: {exc}")
                break
        try:
            runtime.extract_memory(db, user, room_id, user_msg.id, data.message, ids)
        except Exception:
            pass
        background.add_task(
            runtime.analyze_turn, user, room_id, user_msg.id, [c.id for c in selected]
        )
        return {
            "user_message": {"id": user_msg.id, "text": data.message},
            "responses": results,
        }

    runtime.send_message = send_message

    @runtime.app.post("/v1/rooms/{room_id}/messages/stream")
    # SSE ordering and incremental TTS feed intentionally match the original handler.
    def stream_message(
        room_id: str,
        data: runtime.MessageIn,
        background: runtime.BackgroundTasks,
        request: runtime.Request,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        try:
            runtime.ensure_safe_content(data.message)
        except ValueError as exc:
            raise runtime.HTTPException(400, str(exc))
        audit_result = {"status_code": 200, "error": "", "details": {}}
        audit_started = runtime.time.monotonic()
        suggestion_pool = runtime.concurrent.futures.ThreadPoolExecutor(max_workers=3)
        suggestion_jobs = []
        speech_jobs = []

        def event_body():
            runtime.owned(db, runtime.Room, room_id, user)
            ids = [
                m.character_id
                for m in db.query(runtime.RoomMember).filter_by(room_id=room_id).all()
            ]
            chars = [
                runtime.spec(runtime.owned(db, runtime.Character, id, user))
                for id in ids
            ]
            user_msg = runtime.Message(
                id=runtime.uid(), room_id=room_id, sender_type="user", text=data.message
            )
            db.add(user_msg)
            db.commit()
            yield "event: user_message\ndata: " + runtime.json.dumps(
                {
                    "id": user_msg.id,
                    "sender_type": "user",
                    "character_id": None,
                    "text": data.message,
                },
                ensure_ascii=False,
            ) + "\n\n"
            try:
                group_plan = runtime.plan_room(
                    db,
                    room_id,
                    data.message,
                    chars,
                    data.speaker_mode,
                    exclude_message_id=user_msg.id,
                )
                selected = group_plan.speakers
            except ValueError as exc:
                yield "event: error\ndata: " + runtime.json.dumps(
                    {"message": str(exc)}, ensure_ascii=False
                ) + "\n\n"
                return

            def resolve_job(job):
                state = job["state"]
                if "resolved" not in state:
                    if job.get("partial") or not job.get("enabled", True):
                        options = []
                        meta = runtime.roleplay_suggestion_initial_meta()
                        elapsed = 0
                    elif "error" in state:
                        meta = runtime.roleplay_suggestion_initial_meta()
                        meta["fallback_reason"] = runtime.roleplay_suggestion_error(
                            state["error"]
                        )
                        options = []
                        elapsed = int((runtime.time.monotonic() - job["clock"]) * 1000)
                    else:
                        options, meta, elapsed = state["result"]
                    if not job.get("partial") and job.get("enabled", True):
                        options, meta = runtime.finalize_suggestions(
                            options,
                            data.message,
                            runtime.preferred_language(db, user)[0],
                            meta,
                        )
                    try:
                        runtime.ensure_safe_content(*options)
                    except ValueError:
                        options = []
                    state["resolved"] = (options, meta, elapsed)
                return state["resolved"]

            def suggestion_event(job):
                options, _, _ = resolve_job(job)
                job["published"] = True
                return (
                    "event: suggestions\ndata: "
                    + runtime.json.dumps(
                        {
                            "message_id": job["message_id"],
                            "character_id": job["character_id"],
                            "suggestions": options,
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )

            for speaker_index, c in enumerate(selected):
                suggest_enabled = speaker_index == len(selected) - 1
                sentence_voice = None
                reply_id = None
                msg = None
                answer = ""
                active_language = None
                language_text = ""
                language_parts = []
                yield "event: typing\ndata: " + runtime.json.dumps(
                    {"character_id": c.id, "character_name": c.name}, ensure_ascii=False
                ) + "\n\n"
                started = runtime.time.monotonic()
                model_meta = {
                    "primary_model": runtime.llm.model,
                    "primary_model_config_id": (
                        runtime.llm.model
                        if runtime.llm.model in runtime.llm.model_wire_ids
                        else ""
                    ),
                    "fallback_model": runtime.llm.fallback_model,
                    "fallback_used": False,
                }
                try:
                    prompt, sources = runtime.assemble(
                        db, user, room_id, c, data.message
                    )
                    if instruction := group_plan.instruction(c.id):
                        prompt.append({"role": "system", "content": instruction})
                    db.commit()
                    temperature, max_tokens = runtime.roleplay_model_options(
                        db, runtime.llm.model, c.speech.verbosity == "short"
                    )
                    suggest_temperature, suggest_tokens = (
                        runtime.roleplay_model_options(
                            db, runtime.llm.purpose_models.get("suggestion"), True
                        )
                    )
                    reply_id = runtime.uid()
                    sentence_voice = None
                    # A durable reply ID makes early playback possible before text finishes.
                    msg = runtime.Message(
                        id=reply_id,
                        room_id=room_id,
                        sender_type="character",
                        character_id=c.id,
                        text="",
                        finish_status="generating",
                        reply_to_message_id=user_msg.id,
                    )
                    db.add(msg)
                    db.commit()
                    if True:  # Voice follows content, independently of UI language.
                        try:
                            voice_signature = runtime.speech_cache_signature(
                                db, runtime.owned(db, runtime.Character, c.id, user), ""
                            )
                            db.add(
                                runtime.MessageSpeechRun(
                                    message_id=reply_id, signature=voice_signature
                                )
                            )
                            db.commit()
                            sentence_voice = runtime.SentenceSpeech(
                                runtime.sys.modules[runtime.__name__],
                                reply_id,
                                user,
                                voice_signature,
                            )
                            speech_jobs.append(sentence_voice)
                        except Exception:
                            db.rollback()  # Text replies remain available without configured TTS.
                            failed_run = db.get(runtime.MessageSpeechRun, reply_id)
                            if failed_run:
                                db.delete(failed_run)
                                db.commit()
                    if suggest_enabled:
                        future = suggestion_pool.submit(
                            runtime.generate_roleplay_suggestions,
                            prompt,
                            c,
                            data.message,
                            runtime.previous_roleplay_suggestions(db, room_id),
                            suggest_temperature,
                            suggest_tokens,
                        )
                    else:
                        future = runtime.concurrent.futures.Future()
                        future.set_result(([], {}, 0))
                    job = {
                        "enabled": suggest_enabled,
                        "future": future,
                        "state": {},
                        "clock": runtime.time.monotonic(),
                        "message_id": reply_id,
                        "character_id": c.id,
                    }
                    suggestion_jobs.append(job)
                    prepare_ms = round(
                        (runtime.time.monotonic() - request.state.received_at) * 1000
                    )
                    answer = ""
                    reaction_sent = False
                    for chunk in runtime.merge_suggestion_stream(
                        runtime.stream_roleplay_answer(
                            prompt,
                            temperature,
                            max_tokens,
                            "short" if c.speech.verbosity == "short" else "normal",
                        ),
                        future,
                        job["state"],
                    ):
                        if isinstance(chunk, dict) and chunk.get("_suggestions_ready"):
                            if suggest_enabled:
                                yield suggestion_event(job)
                            continue
                        event, value = chunk
                        if event == "language":
                            if language_text:
                                language_parts.append(
                                    {"text": language_text, "language": active_language}
                                )
                                language_text = ""
                            active_language = value
                            if sentence_voice:
                                sentence_voice.change_language(value)
                            continue
                        if event == "delta":
                            answer += value
                            language_text += value
                            if sentence_voice:
                                sentence_voice.feed(value, language=active_language)
                            yield "event: delta\ndata: " + runtime.json.dumps(
                                {
                                    "character_id": c.id,
                                    "message_id": reply_id,
                                    "text": value,
                                    "speech_incremental": bool(sentence_voice),
                                    **runtime.speech_info(
                                        answer,
                                        language_parts
                                        + [
                                            {
                                                "text": language_text,
                                                "language": active_language,
                                            }
                                        ],
                                        c,
                                    ),
                                },
                                ensure_ascii=False,
                            ) + "\n\n"
                            if not reaction_sent:
                                expression = runtime.reply_expression(answer[:800])
                                if expression != "neutral":
                                    reaction_sent = True
                                    yield "event: reaction\ndata: " + runtime.json.dumps(
                                        {
                                            "message_id": reply_id,
                                            "character_id": c.id,
                                            "emotion": expression,
                                            "language": active_language,
                                            "voice_id": runtime.reaction_voice_for(
                                                c, active_language
                                            ),
                                        },
                                        ensure_ascii=False,
                                    ) + "\n\n"
                        else:
                            model_meta = {**value, "server_prepare_ms": prepare_ms}
                    if not answer.strip():
                        raise RuntimeError("Model returned an empty response")
                    partial = model_meta.get("finish_status") == "partial"
                    job["partial"] = partial
                    answer = (
                        answer.strip()
                        if partial
                        else runtime.format_roleplay_reply(answer)
                    )
                    answer_latency_ms = int((runtime.time.monotonic() - started) * 1000)
                    suggestions = (
                        resolve_job(job)[0]
                        if job["state"].get("sent") and not partial
                        else []
                    )
                    if (
                        not db.query(runtime.Message.id)
                        .filter_by(id=user_msg.id, room_id=room_id)
                        .first()
                    ):
                        if sentence_voice:
                            sentence_voice.cancel()
                        raise runtime.HTTPException(404, "Room was deleted")
                    emotion = runtime.reply_expression(answer)
                    msg.text = answer
                    msg.sources = runtime.json.dumps(sources)
                    msg.emotion = emotion
                    msg.finish_status = "partial" if partial else ""
                    msg.speech_segments = runtime.json.dumps(
                        language_parts
                        + [{"text": language_text, "language": active_language}],
                        ensure_ascii=False,
                    )
                    db.add(msg)
                    runtime.save_suggestions(db, msg.id, suggestions)
                    runtime.update_relationship(
                        runtime.relationship(db, user, c.id), data.message
                    )
                    from ..character_social import record_turn
                    record_turn(db,user,room_id,user_msg.id)
                    db.commit()
                    if sentence_voice:
                        if partial:
                            sentence_voice.cancel()
                        else:
                            sentence_voice.finish(answer)
                    runtime.save_ai_request_log(
                        db,
                        user,
                        room_id,
                        user_msg.id,
                        msg.id,
                        "roleplay",
                        "response",
                        {**model_meta, "group_routing": group_plan.metadata()},
                        answer_latency_ms,
                        model_meta.get("fallback_reason", "") if partial else "",
                        answer,
                    )
                    db.commit()
                    job["saved"] = True
                    speech_ready = False
                    speech_error = ""
                    audit_result["details"].update(
                        llm_latency_ms=answer_latency_ms,
                        voice_latency_ms=0,
                        total_latency_ms=int(
                            (runtime.time.monotonic() - audit_started) * 1000
                        ),
                    )
                    payload = {
                        "id": msg.id,
                        "sender_type": "character",
                        "character_id": c.id,
                        "character_name": c.name,
                        "text": answer,
                        "sources": sources,
                        "suggestions": suggestions,
                        "emotion": emotion,
                        "interrupted": partial,
                        "model_used": model_meta.get("actual_model", ""),
                        "latency_ms": answer_latency_ms,
                        "speech_ready": speech_ready,
                        "speech_error": speech_error,
                        **runtime.message_speech_info(
                            msg,
                            answer,
                            db,
                            runtime.owned(db, runtime.Character, c.id, user),
                        ),
                    }
                    payload["reaction_voice_id"] = runtime.reaction_voice_for(
                        c, active_language
                    )
                    payload["reaction_language"] = active_language
                    yield "event: character_message\ndata: " + runtime.json.dumps(
                        payload, ensure_ascii=False
                    ) + "\n\n"
                except Exception as exc:
                    if sentence_voice:
                        sentence_voice.cancel()
                    db.rollback()
                    if msg is not None and msg.id == reply_id:
                        msg.text = answer if "answer" in locals() else ""
                        msg.finish_status = "partial"
                        db.add(msg)
                        db.commit()
                    audit_result.update(
                        status_code=206 if selected else 502,
                        error=str(exc)[:1000],
                        details={"room_id": room_id, "character_id": c.id},
                    )
                    runtime.save_ai_request_log(
                        db,
                        user,
                        room_id,
                        user_msg.id,
                        None,
                        "roleplay",
                        "response",
                        {**model_meta, "group_routing": group_plan.metadata()},
                        int((runtime.time.monotonic() - started) * 1000),
                        str(exc),
                        character_id=c.id,
                    )
                    db.commit()
                    yield "event: character_error\ndata: " + runtime.json.dumps(
                        {"character_id": c.id, "message": str(exc)}, ensure_ascii=False
                    ) + "\n\n"
                    break
            suggestion_deadline = (
                runtime.time.monotonic() + runtime.post_stream_suggestion_wait()
            )
            yield "event: answer_done\ndata: {}\n\n"
            pending = [
                job
                for job in suggestion_jobs
                if job.get("saved") and job.get("enabled", True)
            ]
            while pending:
                progressed = False
                for job in list(pending):
                    future = job["future"]
                    state = job["state"]
                    if not state.get("sent"):
                        if job.get("partial"):
                            future.cancel()
                            state["sent"] = True
                        elif not runtime.capture_suggestion(future, state):
                            if runtime.time.monotonic() < suggestion_deadline:
                                continue
                            state["error"] = TimeoutError(
                                "Suggestion deadline exceeded"
                            )
                            state["sent"] = True
                            future.cancel()
                    options, meta, elapsed = resolve_job(job)
                    runtime.save_suggestions(db, job["message_id"], options)
                    runtime.save_ai_request_log(
                        db,
                        user,
                        room_id,
                        user_msg.id,
                        job["message_id"],
                        "roleplay",
                        "suggestion",
                        meta,
                        elapsed,
                        (
                            f"{type(state['error']).__name__}: {state['error']}"
                            if "error" in state
                            else ""
                        ),
                        " | ".join(options),
                    )
                    db.commit()
                    if not job.get("published") and not job.get("partial"):
                        yield suggestion_event(job)
                    pending.remove(job)
                    progressed = True
                if pending and not progressed:
                    runtime.concurrent.futures.wait(
                        [job["future"] for job in pending],
                        timeout=0.1,
                        return_when=runtime.concurrent.futures.FIRST_COMPLETED,
                    )
            try:
                runtime.extract_memory(
                    db, user, room_id, user_msg.id, data.message, ids
                )
            except Exception:
                pass
            background.add_task(
                runtime.analyze_turn,
                user,
                room_id,
                user_msg.id,
                [c.id for c in selected],
            )
            yield "event: done\ndata: {}\n\n"

        def events():
            try:
                yield from event_body()
            except GeneratorExit:
                audit_result.update(
                    status_code=499, error="Client disconnected before stream completed"
                )
                runtime.write_audit_event(
                    request=request,
                    user_id=user,
                    category="roleplay",
                    action="roleplay.stream",
                    status_code=499,
                    latency_ms=round((runtime.time.monotonic() - audit_started) * 1000),
                    error=audit_result["error"],
                    details=audit_result["details"],
                )
                raise
            except Exception as exc:
                audit_result.update(
                    status_code=500, error=f"{type(exc).__name__}: {exc}"
                )
                runtime.write_audit_event(
                    request=request,
                    user_id=user,
                    category="roleplay",
                    action="roleplay.stream",
                    status_code=500,
                    latency_ms=round((runtime.time.monotonic() - audit_started) * 1000),
                    error=audit_result["error"],
                    details=audit_result["details"],
                )
                raise
            else:
                runtime.write_audit_event(
                    request=request,
                    user_id=user,
                    category="roleplay",
                    action="roleplay.stream",
                    status_code=audit_result["status_code"],
                    latency_ms=round((runtime.time.monotonic() - audit_started) * 1000),
                    error=audit_result["error"],
                    details=audit_result["details"],
                )
            finally:
                for voice_job in speech_jobs:
                    if voice_job.final_text is None:
                        voice_job.cancel()
                for job in suggestion_jobs:
                    job["future"].cancel()
                suggestion_pool.shutdown(wait=False, cancel_futures=True)

        return runtime.StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    runtime.stream_message = stream_message


def bind_regenerate_message(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.post("/v1/rooms/{room_id}/messages/{message_id}/regenerate")
    def regenerate_message(
        room_id: str,
        message_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        runtime.owned(db, runtime.Room, room_id, user)
        message = db.get(runtime.Message, message_id)
        if (
            not message
            or message.room_id != room_id
            or message.sender_type != "character"
            or not message.character_id
        ):
            raise runtime.HTTPException(404, "Character message not found")
        character = runtime.owned(db, runtime.Character, message.character_id, user)
        history = (
            db.query(runtime.Message)
            .filter_by(room_id=room_id)
            .order_by(runtime.Message.created_at, runtime.Message.id)
            .all()
        )
        position = next(
            (i for i, item in enumerate(history) if item.id == message_id), -1
        )
        prompt_message = next(
            (
                item
                for item in reversed(history[:position])
                if item.sender_type == "user"
            ),
            None,
        )
        if not prompt_message:
            raise runtime.HTTPException(409, "No user message to regenerate from")
        character_data = runtime.CharacterSpec.model_validate_json(character.spec)
        prompts, sources = runtime.assemble(
            db, user, room_id, character_data, prompt_message.text
        )
        db.commit()
        for item in reversed(prompts):
            if item["role"] == "assistant" and item["content"] == message.text:
                prompts.remove(item)
                break
        temperature, max_tokens = runtime.roleplay_model_options(
            db, runtime.llm.model, character_data.speech.verbosity == "short"
        )
        suggest_temperature, suggest_tokens = runtime.roleplay_model_options(
            db, runtime.llm.purpose_models.get("suggestion"), True
        )
        started = runtime.time.monotonic()
        pool = runtime.concurrent.futures.ThreadPoolExecutor(max_workers=2)
        try:
            answer_future = pool.submit(
                runtime.llm.chat_with_meta,
                runtime.roleplay_output_prompt(prompts),
                temperature,
                max_tokens,
                profile_mode=(
                    "short" if character_data.speech.verbosity == "short" else "normal"
                ),
            )
            suggestion_started = runtime.time.monotonic()
            suggestion_future = pool.submit(
                runtime.llm.chat_with_meta,
                runtime.suggestion_prompt(
                    prompts,
                    character_data,
                    prompt_message.text,
                    runtime.previous_roleplay_suggestions(db, room_id),
                ),
                suggest_temperature,
                suggest_tokens,
                runtime.llm.purpose_models.get("suggestion"),
                runtime.llm.purpose_models.get("suggestion_fallback") or "",
                runtime.llm.purpose_models.get("suggestion_fallback_2") or "",
                profile_mode="short",
                gateway_timeout_cap_seconds=8,
            )
            try:
                answer, model_meta = answer_future.result()
                answer, speech_parts = runtime.parse_language_reply(answer)
                answer = runtime.format_roleplay_reply(answer)
                answer_latency_ms = int((runtime.time.monotonic() - started) * 1000)
            except Exception as exc:
                raise runtime.HTTPException(503, f"Regeneration unavailable: {exc}")
            suggestion_meta = runtime.roleplay_suggestion_initial_meta()
            suggestion_error = ""
            try:
                suggestion_raw, suggestion_meta = suggestion_future.result(
                    timeout=runtime.post_stream_suggestion_wait()
                )
                suggestions = runtime.parse_suggestions(suggestion_raw)
            except Exception as exc:
                suggestions = []
                suggestion_error = runtime.roleplay_suggestion_error(exc)
                suggestion_meta["fallback_reason"] = suggestion_error
                suggestion_future.cancel()
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        suggestions, suggestion_meta = runtime.finalize_suggestions(
            suggestions,
            prompt_message.text,
            runtime.preferred_language(db, user)[0],
            suggestion_meta,
        )
        try:
            runtime.ensure_safe_content(answer)
        except ValueError as exc:
            raise runtime.HTTPException(400, str(exc))
        existing = (
            db.query(runtime.MessageAlternative)
            .filter_by(message_id=message.id, text=message.text)
            .first()
        )
        if not existing:
            db.add(
                runtime.MessageAlternative(
                    id=runtime.uid(), message_id=message.id, text=message.text
                )
            )
        db.add(
            runtime.MessageAlternative(
                id=runtime.uid(), message_id=message.id, text=answer
            )
        )
        message.speech_segments = runtime.json.dumps(speech_parts, ensure_ascii=False)
        db.query(runtime.MessageSpeechPart).filter_by(message_id=message.id).delete(
            synchronize_session=False
        )
        db.query(runtime.MessageSpeechRun).filter_by(message_id=message.id).delete(
            synchronize_session=False
        )
        db.query(runtime.MessageSpeech).filter_by(message_id=message.id).delete(
            synchronize_session=False
        )
        message.text = answer
        message.sources = runtime.json.dumps(sources, ensure_ascii=False)
        message.emotion = runtime.reply_expression(answer)
        runtime.save_suggestions(db, message.id, suggestions)
        runtime.save_ai_request_log(
            db,
            user,
            room_id,
            prompt_message.id,
            message.id,
            "roleplay",
            "regenerate",
            model_meta,
            answer_latency_ms,
            output_text=answer,
        )
        runtime.save_ai_request_log(
            db,
            user,
            room_id,
            prompt_message.id,
            message.id,
            "roleplay",
            "suggestion",
            suggestion_meta,
            int((runtime.time.monotonic() - suggestion_started) * 1000),
            suggestion_error,
            " | ".join(suggestions),
        )
        db.commit()
        speech_ready = False
        speech_error = ""
        return {
            "id": message.id,
            "sender_type": "character",
            "character_id": message.character_id,
            "text": message.text,
            "sources": sources,
            "suggestions": suggestions,
            "emotion": message.emotion,
            "speech_ready": speech_ready,
            "speech_error": speech_error,
            **runtime.message_speech_info(message, message.text, db, character),
        }

    runtime.regenerate_message = regenerate_message

    @runtime.app.get("/v1/characters/{character_id}/memories")
    def character_memories(
        character_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        runtime.owned(db, runtime.Character, character_id, user)
        return [
            runtime.memory_out(x)
            for x in db.query(runtime.Memory)
            .filter_by(user_id=user, character_id=character_id)
            .all()
        ]

    runtime.character_memories = character_memories
