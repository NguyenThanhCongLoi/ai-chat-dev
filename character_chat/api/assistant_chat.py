"""api.assistant_chat: domain-specific application implementation.

Assistant response endpoints, preserving nonstream and SSE behavior.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_send_assistant_message(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.post("/v1/assistant/chats/{room_id}/messages")
    def send_assistant_message(
        room_id: str,
        data: dict,
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        room = runtime.assistant_room(db, user, room_id)
        mode = room.name.split(":", 2)[1]
        text = str(data.get("message") or "").strip()[:12000]
        if not text:
            raise runtime.HTTPException(400, "Message is required")
        try:
            runtime.ensure_safe_content(
                text, allow_crisis_support=mode == "assistant_psychology"
            )
        except ValueError as exc:
            raise runtime.HTTPException(400, str(exc))
        user_message = runtime.Message(
            id=runtime.uid(),
            room_id=room.id,
            sender_type="user",
            character_id=None,
            text=text,
        )
        if not db.query(runtime.Message.id).filter_by(room_id=room.id).first():
            title = " ".join(text.split())[:80]
            room.name = f"{runtime.ASSISTANT_ROOM_PREFIX}{mode}:{title}"
        db.add(user_message)
        db.commit()
        history = (
            db.query(runtime.Message)
            .filter_by(room_id=room.id)
            .order_by(runtime.Message.created_at.desc())
            .limit(10)
            .all()[::-1]
        )
        document_ids = [
            item.document_id
            for item in db.query(runtime.RoomDocument).filter_by(room_id=room.id).all()
        ]
        requested_ids = (
            [str(value) for value in data.get("attachment_ids", [])][:4]
            if isinstance(data.get("attachment_ids", []), list)
            else []
        )
        valid_requested = [value for value in requested_ids if value in document_ids]
        sources, context = (
            runtime.retrieve_room_context(
                db, room.id, text, document_ids=valid_requested, force_include=True
            )
            if valid_requested
            else runtime.retrieve_room_context(db, room.id, text)
        )
        if valid_requested and not sources:
            sources = [
                {
                    "index": index,
                    "document_id": document_id,
                    "filename": db.get(runtime.Document, document_id).filename,
                }
                for index, document_id in enumerate(valid_requested, 1)
                if db.get(runtime.Document, document_id)
            ]
        if valid_requested:
            user_message.sources = runtime.json.dumps(sources, ensure_ascii=False)
            db.commit()
        image_files = (
            db.query(runtime.AssistantFile)
            .filter(
                runtime.AssistantFile.document_id.in_(valid_requested),
                runtime.AssistantFile.mime_type.like("image/%"),
            )
            .order_by(runtime.AssistantFile.created_at.asc())
            .limit(4)
            .all()
            if valid_requested
            else runtime.latest_room_images(db, room.id, user, 4)
        )
        model = db.query(runtime.ModelConfig).filter_by(assistant_enabled=1).all()
        assigned = next(
            (
                item
                for item in model
                if mode in runtime.model_profile(db, item).get("purposes", [])
            ),
            None,
        )
        if not assigned:
            raise runtime.HTTPException(503, "Chưa phân công model cho AI Assistant")
        profile = runtime.model_profile(db, assigned)
        prompt = runtime.effective_project_prompt(
            runtime.ASSISTANT_PROMPTS[mode], profile.get(mode + "_instruction", "")
        )
        system_context = (
            "\n\nTask pipeline rules:\n"
            + runtime.task_guardrail(mode, text)
            + (
                ("\n\nRetrieved file context:\n" + context)
                if context and not valid_requested
                else ""
            )
            + runtime.assistant_memory_context(db, user, mode, room.id)
        )
        messages = [
            {"role": "system", "content": prompt + system_context},
            *runtime.assistant_history_with_images(db, room.id, history, max_images=4),
        ]
        if image_files and valid_requested:
            messages[-1] = {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    *[
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_file.mime_type};base64,{runtime.base64.b64encode(image_file.content).decode('ascii')}"
                            },
                        }
                        for image_file in image_files
                    ],
                ],
            }
        elif valid_requested and context:
            messages[-1] = {
                "role": "user",
                "content": text
                + "\n\nThe user attached the following document content to this exact question:\n\n"
                + context,
            }
        tail_messages = messages[1:]
        try:
            answer, model_meta = runtime.run_assistant_model_chain(
                db,
                model,
                mode,
                runtime.ASSISTANT_PROMPTS[mode],
                tail_messages,
                system_context,
                1000,
                runtime.assistant_preferred_model(db, mode, data.get("model_id")),
            )
        except Exception as exc:
            failed_meta = {
                "primary_model": assigned.assistant_model_id or assigned.model_id,
                "fallback_model": "",
                "fallback_used": False,
                "fallback_reason": str(exc),
            }
            runtime.save_ai_request_log(
                db,
                user,
                room.id,
                user_message.id,
                None,
                "assistant",
                mode,
                failed_meta,
                0,
                str(exc),
            )
            db.commit()
            raise runtime.HTTPException(
                503, f"Các model AI Assistant đều không khả dụng: {str(exc)[:240]}"
            )
        answer = answer.strip()
        suggestions = []
        suggestion_meta = {}
        suggestion_started = runtime.time.monotonic()
        suggestion_error = ""
        try:
            suggestion_raw, suggestion_meta = runtime.run_assistant_model_chain(
                db,
                model,
                "assistant_suggestion",
                runtime.ASSISTANT_SUGGESTION_PROMPT,
                [
                    {
                        "role": "user",
                        "content": runtime.json.dumps(
                            {
                                "mode": mode,
                                "user_message": text,
                                "assistant_answer": answer,
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
                "",
                180,
            )
            suggestions = runtime.parse_suggestions(suggestion_raw)
        except Exception as exc:
            suggestion_error = str(exc)
        suggestions, suggestion_meta = runtime.finalize_suggestions(
            suggestions, text, runtime.preferred_language(db, user)[0], suggestion_meta
        )
        reply = runtime.Message(
            id=runtime.uid(),
            room_id=room.id,
            sender_type="assistant",
            character_id=None,
            text=answer,
            sources=runtime.json.dumps(sources, ensure_ascii=False),
        )
        db.add(reply)
        db.flush()
        runtime.save_suggestions(db, reply.id, suggestions)
        runtime.save_ai_request_log(
            db,
            user,
            room.id,
            user_message.id,
            reply.id,
            "assistant",
            mode,
            model_meta,
            model_meta["latency_ms"],
            output_text=answer,
        )
        runtime.save_ai_request_log(
            db,
            user,
            room.id,
            user_message.id,
            reply.id,
            "assistant",
            "suggestion",
            suggestion_meta,
            int((runtime.time.monotonic() - suggestion_started) * 1000),
            suggestion_error,
            " | ".join(suggestions),
        )
        db.commit()
        return {
            "id": reply.id,
            "role": "assistant",
            "text": reply.text,
            "sources": sources,
            "suggestions": suggestions,
            "created_at": reply.created_at,
        }

    runtime.send_assistant_message = send_assistant_message

    @runtime.app.post("/v1/assistant/chats/{room_id}/messages/stream")
    def stream_assistant_message(
        room_id: str,
        data: dict,
        request: runtime.Request,
        user: str = runtime.Depends(runtime.current_user),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
    ):
        room = runtime.assistant_room(db, user, room_id)
        mode = room.name.split(":", 2)[1]
        text = str(data.get("message") or "").strip()[:12000]
        if not text:
            raise runtime.HTTPException(400, "Message is required")
        try:
            runtime.ensure_safe_content(
                text, allow_crisis_support=mode == "assistant_psychology"
            )
        except ValueError as exc:
            raise runtime.HTTPException(400, str(exc))
        user_message = runtime.Message(
            id=runtime.uid(),
            room_id=room.id,
            sender_type="user",
            character_id=None,
            text=text,
        )
        if not db.query(runtime.Message.id).filter_by(room_id=room.id).first():
            title = " ".join(text.split())[:80]
            room.name = f"{runtime.ASSISTANT_ROOM_PREFIX}{mode}:{title}"
        db.add(user_message)
        db.commit()
        history = (
            db.query(runtime.Message)
            .filter_by(room_id=room.id)
            .order_by(runtime.Message.created_at.desc())
            .limit(10)
            .all()[::-1]
        )
        document_ids = [
            item.document_id
            for item in db.query(runtime.RoomDocument).filter_by(room_id=room.id).all()
        ]
        requested_ids = (
            [str(value) for value in data.get("attachment_ids", [])][:4]
            if isinstance(data.get("attachment_ids", []), list)
            else []
        )
        valid_requested = [value for value in requested_ids if value in document_ids]
        sources, context = (
            runtime.retrieve_room_context(
                db, room.id, text, document_ids=valid_requested, force_include=True
            )
            if valid_requested
            else runtime.retrieve_room_context(db, room.id, text)
        )
        if valid_requested and not sources:
            sources = [
                {
                    "index": index,
                    "document_id": document_id,
                    "filename": db.get(runtime.Document, document_id).filename,
                }
                for index, document_id in enumerate(valid_requested, 1)
                if db.get(runtime.Document, document_id)
            ]
        if valid_requested:
            user_message.sources = runtime.json.dumps(sources, ensure_ascii=False)
            db.commit()
        image_files = (
            db.query(runtime.AssistantFile)
            .filter(
                runtime.AssistantFile.document_id.in_(valid_requested),
                runtime.AssistantFile.mime_type.like("image/%"),
            )
            .order_by(runtime.AssistantFile.created_at.asc())
            .limit(4)
            .all()
            if valid_requested
            else runtime.latest_room_images(db, room.id, user, 4)
        )
        models = db.query(runtime.ModelConfig).filter_by(assistant_enabled=1).all()
        roles = (mode, mode + "_fallback", mode + "_fallback_2")
        configured = [
            next(
                (
                    item
                    for item in models
                    if role in runtime.model_profile(db, item).get("purposes", [])
                ),
                None,
            )
            for role in roles
        ]
        configured_slot = {
            item.id: index for index, item in enumerate(configured) if item
        }
        candidates = list(configured)
        prompt_slots = list(range(3))
        preferred_id = runtime.assistant_preferred_model(db, mode, data.get("model_id"))
        if preferred_id:
            preferred = next((item for item in models if item.id == preferred_id), None)
            if preferred:
                remainder = [
                    item for item in configured if item and item.id != preferred.id
                ]
                candidates = [preferred, *remainder]
                prompt_slots = [0, *[configured_slot[item.id] for item in remainder]]
        candidates = (candidates + [None, None, None])[:3]
        prompt_slots = (prompt_slots + [0, 1, 2])[:3]
        if not candidates[0]:
            raise runtime.HTTPException(503, "Chưa phân công model cho AI Assistant")
        system_context = (
            "\n\nTask pipeline rules:\n"
            + runtime.task_guardrail(mode, text)
            + (
                ("\n\nRetrieved file context:\n" + context)
                if context and not valid_requested
                else ""
            )
            + runtime.assistant_memory_context(db, user, mode, room.id)
        )
        tail_messages = runtime.assistant_history_with_images(
            db, room.id, history, max_images=4
        )
        suggestion_context = [
            {
                "role": "user" if item.sender_type == "user" else "assistant",
                "content": item.text[:1200],
            }
            for item in history[-5:]
        ]
        if (
            image_files
            and valid_requested
            and any(
                image_file.document_id in valid_requested for image_file in image_files
            )
        ):
            tail_messages[-1] = {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    *[
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_file.mime_type};base64,{runtime.base64.b64encode(image_file.content).decode('ascii')}"
                            },
                        }
                        for image_file in image_files
                    ],
                ],
            }
        elif valid_requested and context:
            tail_messages[-1] = {
                "role": "user",
                "content": text
                + "\n\nThe user attached the following document content to this exact question:\n\n"
                + context,
            }
        audit_result = {"status_code": 200, "error": "", "details": {}}
        audit_started = runtime.time.monotonic()
        suggestion_pool = runtime.concurrent.futures.ThreadPoolExecutor(max_workers=1)
        suggestion_cancel = __import__("threading").Event()
        suggestion_future = None

        def event_body():
            nonlocal suggestion_future
            response_waits = [
                int(
                    runtime.model_profile(db, item).get(
                        "gateway_read_timeout_seconds", 12
                    )
                )
                for item in candidates
                if item
            ]
            stream_budget = max(
                20,
                min(
                    90,
                    float(runtime.os.getenv("ASSISTANT_STREAM_BUDGET_SECONDS", "45")),
                ),
                max(response_waits, default=12) + 20,
            )
            started = runtime.time.monotonic()
            deadline = started + stream_budget
            errors = []
            answer = ""
            model_meta = {}
            reply = None
            interrupted = False
            gateway_timing = {}
            reply_id = runtime.uid()
            suggestion_state = {}

            def generate_parallel_suggestions():
                with runtime.Session() as suggestion_db:
                    suggestion_models = (
                        suggestion_db.query(runtime.ModelConfig)
                        .filter_by(assistant_enabled=1)
                        .all()
                    )
                    suggestion_started = runtime.time.monotonic()
                    raw, meta = runtime.run_assistant_model_chain(
                        suggestion_db,
                        suggestion_models,
                        "assistant_suggestion",
                        runtime.ASSISTANT_SUGGESTION_PROMPT,
                        [
                            {
                                "role": "user",
                                "content": runtime.json.dumps(
                                    {
                                        "mode": mode,
                                        "user_message": text,
                                        "recent_conversation": suggestion_context,
                                    },
                                    ensure_ascii=False,
                                ),
                            }
                        ],
                        "",
                        180,
                        cancel_event=suggestion_cancel,
                    )
                    return (
                        runtime.parse_suggestions(raw),
                        meta,
                        int((runtime.time.monotonic() - suggestion_started) * 1000),
                    )

            # Start suggestions before opening the answer stream. This hides their
            # latency behind the model response instead of adding it afterwards.
            suggestion_clock = runtime.time.monotonic()
            suggestion_future = suggestion_pool.submit(generate_parallel_suggestions)

            def resolved_suggestions():
                if "resolved" not in suggestion_state:
                    if "error" in suggestion_state:
                        exc = suggestion_state["error"]
                        raw = []
                        meta = {
                            "fallback_used": True,
                            "actual_model": "local_static",
                            "fallback_reason": f"Suggest error: {type(exc).__name__}: {str(exc)[:500]}",
                        }
                        elapsed = int(
                            (runtime.time.monotonic() - suggestion_clock) * 1000
                        )
                    else:
                        raw, meta, elapsed = suggestion_state["result"]
                    options, meta = runtime.finalize_suggestions(
                        raw, text, runtime.preferred_language(db, user)[0], meta
                    )
                    suggestion_state["resolved"] = (options, meta, elapsed)
                return suggestion_state["resolved"]

            def suggestion_event():
                options, _, _ = resolved_suggestions()
                suggestion_state["published"] = True
                return (
                    "event: suggestions\ndata: "
                    + runtime.json.dumps(
                        {"message_id": reply_id, "suggestions": options},
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )

            model_ids = [
                (item.assistant_model_id or item.model_id) if item else ""
                for item in candidates
            ]
            for index, item in enumerate(candidates):
                if not item:
                    continue
                if runtime.time.monotonic() >= deadline:
                    errors.append("Assistant total response time budget exhausted")
                    break
                profile = runtime.model_profile(db, item)
                slot = prompt_slots[index]
                field = mode + (
                    "_instruction"
                    if slot == 0
                    else (
                        "_fallback_instruction"
                        if slot == 1
                        else "_fallback_2_instruction"
                    )
                )
                prompt = runtime.effective_project_prompt(
                    runtime.ASSISTANT_PROMPTS[mode], profile.get(field, "")
                )
                shared_prompt = str(
                    runtime.runtime_settings(db).get("assistant_system_instruction")
                    or ""
                ).strip()
                shared_context = (
                    ("\n\nSystem-wide AI Assistant instructions:\n" + shared_prompt)
                    if shared_prompt
                    else ""
                )
                messages = [
                    {
                        "role": "system",
                        "content": prompt + shared_context + system_context,
                    },
                    *tail_messages,
                ]
                key = runtime.credential_for_model(db, item)
                actual = item.assistant_model_id or item.model_id
                thinking = item.assistant_thinking_mode or "default"
                effort = item.assistant_reasoning_effort or "default"
                emitted = False
                stream_status = "unknown"
                continuations = 0
                gateway_timing = {}
                try:
                    cooldown = runtime.model_circuit_remaining(item.id)
                    if cooldown:
                        raise RuntimeError(
                            f"circuit breaker active for {cooldown:.1f}s after a recent network failure"
                        )
                    gateway_wait = max(
                        14, int(profile.get("gateway_read_timeout_seconds", 12))
                    )
                    gateway_timing["server_prepare_ms"] = round(
                        (runtime.time.monotonic() - request.state.received_at) * 1000
                    )
                    stream = runtime.chat_stream(
                        messages,
                        actual,
                        item.api_base,
                        key,
                        float(profile.get("temperature", 0.35)),
                        int(profile.get("max_tokens", 1000)),
                        thinking,
                        effort,
                        max(
                            0.1, min(gateway_wait, deadline - runtime.time.monotonic())
                        ),
                    )
                    for chunk in runtime.merge_suggestion_stream(
                        runtime.bounded_remote_chunks(stream, deadline),
                        suggestion_future,
                        suggestion_state,
                    ):
                        if isinstance(chunk, dict) and chunk.get("_suggestions_ready"):
                            yield suggestion_event()
                            continue
                        if runtime.time.monotonic() >= deadline:
                            raise TimeoutError(
                                "Assistant total response time budget exhausted"
                            )
                        if isinstance(chunk, dict) and chunk.get("_gateway_timing"):
                            gateway_timing.update(chunk["_gateway_timing"])
                            continue
                        if isinstance(chunk, dict) and chunk.get("_stream_status"):
                            stream_status = str(chunk["_stream_status"])
                            continue
                        if not isinstance(chunk, str) or not chunk:
                            continue
                        emitted = True
                        answer += chunk
                        yield "event: delta\ndata: " + runtime.json.dumps(
                            {"text": chunk}, ensure_ascii=False
                        ) + "\n\n"
                    if stream_status not in ("complete", "truncated"):
                        raise RuntimeError(
                            f"Stream ended without a completion marker (status={stream_status})"
                        )
                    if not answer.strip():
                        raise RuntimeError("Model returned an empty response")
                    while stream_status == "truncated" and continuations < 2:
                        continuations += 1
                        stream_status = "unknown"
                        continuation_messages = [
                            *messages,
                            {"role": "assistant", "content": answer},
                            {
                                "role": "user",
                                "content": "Continue exactly where the previous answer stopped. Do not repeat earlier text. Finish the answer naturally and concisely.",
                            },
                        ]
                        continuation = runtime.chat_stream(
                            continuation_messages,
                            actual,
                            item.api_base,
                            key,
                            float(profile.get("temperature", 0.35)),
                            int(profile.get("max_tokens", 1000)),
                            thinking,
                            effort,
                            max(
                                0.1,
                                min(gateway_wait, deadline - runtime.time.monotonic()),
                            ),
                        )
                        for chunk in runtime.merge_suggestion_stream(
                            runtime.bounded_remote_chunks(continuation, deadline),
                            suggestion_future,
                            suggestion_state,
                        ):
                            if isinstance(chunk, dict) and chunk.get(
                                "_suggestions_ready"
                            ):
                                yield suggestion_event()
                                continue
                            if runtime.time.monotonic() >= deadline:
                                raise TimeoutError(
                                    "Assistant total response time budget exhausted"
                                )
                            if isinstance(chunk, dict) and chunk.get("_stream_status"):
                                stream_status = str(chunk["_stream_status"])
                                continue
                            if not isinstance(chunk, str) or not chunk:
                                continue
                            answer += chunk
                            yield "event: delta\ndata: " + runtime.json.dumps(
                                {"text": chunk}, ensure_ascii=False
                            ) + "\n\n"
                    if stream_status == "truncated":
                        errors.append(
                            f"{actual}: response still reached token limit after {continuations} continuations"
                        )
                        interrupted = True
                        model_meta = {
                            "primary_model": model_ids[0],
                            "primary_model_config_id": (
                                candidates[0].id if candidates[0] else ""
                            ),
                            "actual_model_config_id": item.id,
                            "fallback_model": model_ids[1],
                            "fallback_model_2": model_ids[2],
                            "fallback_used": index > 0,
                            "fallback_level": index,
                            "fallback_reason": " | ".join(errors),
                            "actual_model": actual,
                            "thinking_mode": thinking,
                            "reasoning_effort": effort,
                            "continuation_count": continuations,
                            "finish_status": "partial",
                        }
                    else:
                        runtime.record_model_success(item.id)
                    if not interrupted:
                        model_meta = {
                            "primary_model": model_ids[0],
                            "primary_model_config_id": (
                                candidates[0].id if candidates[0] else ""
                            ),
                            "actual_model_config_id": item.id,
                            "fallback_model": model_ids[1],
                            "fallback_model_2": model_ids[2],
                            "fallback_used": index > 0,
                            "fallback_level": index,
                            "fallback_reason": " | ".join(errors),
                            "actual_model": actual,
                            "thinking_mode": thinking,
                            "reasoning_effort": effort,
                            "continuation_count": continuations,
                            "finish_status": stream_status,
                        }
                    break
                except Exception as exc:
                    runtime.record_model_failure(item.id, exc)
                    errors.append(f"{actual}: {str(exc)[:500]}")
                    if emitted:
                        interrupted = True
                        model_meta = {
                            "primary_model": model_ids[0],
                            "primary_model_config_id": (
                                candidates[0].id if candidates[0] else ""
                            ),
                            "actual_model_config_id": item.id,
                            "fallback_model": model_ids[1],
                            "fallback_model_2": model_ids[2],
                            "fallback_used": index > 0,
                            "fallback_reason": " | ".join(errors),
                            "actual_model": actual,
                            "thinking_mode": thinking,
                            "reasoning_effort": effort,
                            "finish_status": "partial",
                        }
                        break
                    answer = ""
            model_meta.update(gateway_timing)
            latency = int((runtime.time.monotonic() - started) * 1000)
            if not answer.strip():
                audit_result.update(
                    status_code=502,
                    error=" | ".join(errors),
                    details={"mode": mode, "fallback_used": bool(errors)},
                )
                if suggestion_future:
                    suggestion_future.cancel()
                suggestion_pool.shutdown(wait=False, cancel_futures=True)
                runtime.save_ai_request_log(
                    db,
                    user,
                    room.id,
                    user_message.id,
                    None,
                    "assistant",
                    mode,
                    model_meta
                    or {
                        "primary_model": model_ids[0],
                        "primary_model_config_id": (
                            candidates[0].id if candidates[0] else ""
                        ),
                        "fallback_model": model_ids[1],
                        "fallback_model_2": model_ids[2],
                        "fallback_used": bool(errors),
                        "fallback_reason": " | ".join(errors),
                    },
                    latency,
                    " | ".join(errors),
                )
                db.commit()
                yield "event: error\ndata: " + runtime.json.dumps(
                    {
                        "message": "Các model AI Assistant đều không khả dụng",
                        "detail": " | ".join(errors),
                    },
                    ensure_ascii=False,
                ) + "\n\n"
                return
            if interrupted:
                if suggestion_future:
                    suggestion_cancel.set()
                    suggestion_future.cancel()
                suggestion_pool.shutdown(wait=False, cancel_futures=True)
                reply = runtime.Message(
                    id=reply_id,
                    room_id=room.id,
                    sender_type="assistant",
                    character_id=None,
                    text=answer.strip(),
                    sources=runtime.json.dumps(sources, ensure_ascii=False),
                    finish_status="partial",
                )
                db.add(reply)
                db.flush()
                partial_error = (
                    " | ".join(errors)
                    or "Stream ended before a complete answer was received"
                )
                latency = int((runtime.time.monotonic() - started) * 1000)
                runtime.save_ai_request_log(
                    db,
                    user,
                    room.id,
                    user_message.id,
                    reply.id,
                    "assistant",
                    mode,
                    model_meta,
                    latency,
                    partial_error,
                    reply.text,
                )
                db.commit()
                audit_result.update(
                    status_code=206,
                    error=partial_error,
                    details={"mode": mode, "partial": True, "latency_ms": latency},
                )
                yield "event: partial\ndata: " + runtime.json.dumps(
                    {
                        "id": reply.id,
                        "role": "assistant",
                        "text": reply.text,
                        "sources": sources,
                        "interrupted": True,
                        "created_at": reply.created_at,
                    },
                    ensure_ascii=False,
                ) + "\n\n"
                return
            reply = runtime.Message(
                id=reply_id,
                room_id=room.id,
                sender_type="assistant",
                character_id=None,
                text=answer.strip(),
                sources=runtime.json.dumps(sources, ensure_ascii=False),
            )
            db.add(reply)
            db.flush()
            stream_error = (
                " | ".join(errors)
                if errors and not model_meta.get("fallback_reason")
                else ""
            )
            runtime.save_ai_request_log(
                db,
                user,
                room.id,
                user_message.id,
                reply.id,
                "assistant",
                mode,
                model_meta,
                latency,
                stream_error,
                reply.text,
            )
            db.commit()
            answer_payload = {
                "id": reply.id,
                "role": "assistant",
                "text": reply.text,
                "sources": sources,
                "suggestions": [],
                "created_at": reply.created_at,
            }
            yield "event: answer_done\ndata: " + runtime.json.dumps(
                answer_payload, ensure_ascii=False
            ) + "\n\n"
            if not suggestion_state.get("sent"):
                try:
                    suggestion_state["result"] = suggestion_future.result(
                        timeout=runtime.post_stream_suggestion_wait()
                    )
                except Exception as exc:
                    suggestion_state["error"] = exc
                    suggestion_cancel.set()
                    suggestion_future.cancel()
                suggestion_state["sent"] = True
            suggestions, suggestion_meta, suggestion_latency = resolved_suggestions()
            runtime.save_suggestions(db, reply.id, suggestions)
            runtime.save_ai_request_log(
                db,
                user,
                room.id,
                user_message.id,
                reply.id,
                "assistant",
                "suggestion",
                suggestion_meta,
                suggestion_latency,
                (
                    f"{type(suggestion_state['error']).__name__}: {suggestion_state['error']}"
                    if "error" in suggestion_state
                    else ""
                ),
                " | ".join(suggestions),
            )
            db.commit()
            if not suggestion_state.get("published"):
                yield suggestion_event()
            audit_result.update(
                status_code=200,
                details={
                    "mode": mode,
                    "latency_ms": latency,
                    "fallback_used": bool(model_meta.get("fallback_used")),
                },
            )
            yield "event: done\ndata: " + runtime.json.dumps(
                {**answer_payload, "suggestions": suggestions}, ensure_ascii=False
            ) + "\n\n"

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
                    category="assistant",
                    action="assistant.stream",
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
                    category="assistant",
                    action="assistant.stream",
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
                    category="assistant",
                    action="assistant.stream",
                    status_code=audit_result["status_code"],
                    latency_ms=round((runtime.time.monotonic() - audit_started) * 1000),
                    error=audit_result["error"],
                    details=audit_result["details"],
                )
            finally:
                suggestion_cancel.set()
                if suggestion_future is not None:
                    suggestion_future.cancel()
                suggestion_pool.shutdown(wait=False, cancel_futures=True)

        return runtime.StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    runtime.stream_assistant_message = stream_assistant_message
