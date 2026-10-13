"""services.assistant_inference: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_run_assistant_model_chain(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def run_assistant_model_chain(
        db,
        models,
        purpose,
        base_prompt,
        tail_messages,
        system_context,
        max_tokens=1000,
        preferred_model_id="",
        cancel_event=None,
    ):
        roles = (purpose, purpose + "_fallback", purpose + "_fallback_2")
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
        prompt_slots = list(range(len(configured)))
        if preferred_model_id:
            preferred = next(
                (
                    item
                    for item in models
                    if item.id == preferred_model_id and item.assistant_enabled
                ),
                None,
            )
            if preferred:
                remainder = [
                    item for item in configured if item and item.id != preferred.id
                ]
                candidates = [preferred, *remainder]
                prompt_slots = [0, *[configured_slot[item.id] for item in remainder]]
        candidates = (candidates + [None, None, None])[:3]
        prompt_slots = (prompt_slots + [0, 1, 2])[:3]
        if not candidates[0]:
            raise RuntimeError(f"CMS chưa phân công model chính cho {purpose}")
        response_waits = (
            [
                int(
                    runtime.model_profile(db, item).get(
                        "gateway_read_timeout_seconds", 12
                    )
                )
                for item in candidates
                if item
            ]
            if purpose != "assistant_suggestion"
            else [6]
        )
        chain_budget = max(
            8,
            min(
                90,
                float(runtime.os.getenv("ASSISTANT_MODEL_CHAIN_BUDGET_SECONDS", "28")),
            ),
            max(response_waits) + 12,
        )
        if purpose == "assistant_suggestion":
            chain_budget = runtime.suggestion_budget()
        errors = []
        started = runtime.time.monotonic()
        deadline = started + chain_budget
        for index, item in enumerate(candidates):
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError(
                    "Suggestion generation cancelled after instant fallback was selected"
                )
            if not item:
                continue
            if runtime.time.monotonic() >= deadline:
                errors.append("Assistant model chain time budget exhausted")
                break
            profile = runtime.model_profile(db, item)
            slot = prompt_slots[index]
            field = purpose + (
                "_instruction"
                if slot == 0
                else "_fallback_instruction" if slot == 1 else "_fallback_2_instruction"
            )
            prompt = runtime.effective_project_prompt(
                base_prompt, profile.get(field, "")
            )
            shared_prompt = str(
                runtime.runtime_settings(db).get("assistant_system_instruction") or ""
            ).strip()
            shared_context = (
                ("\n\nSystem-wide AI Assistant instructions:\n" + shared_prompt)
                if shared_prompt
                else ""
            )
            messages = [
                {"role": "system", "content": prompt + shared_context + system_context},
                *tail_messages,
            ]
            key = runtime.credential_for_model(db, item)
            try:
                effective_model_id = item.assistant_model_id or item.model_id
                thinking_mode = item.assistant_thinking_mode or "default"
                reasoning_effort = item.assistant_reasoning_effort or "default"
                cooldown = runtime.model_circuit_remaining(item.id)
                if cooldown:
                    raise RuntimeError(
                        f"circuit breaker active for {cooldown:.1f}s after a recent network failure"
                    )
                is_suggestion = purpose == "assistant_suggestion"
                gateway_wait = (
                    6
                    if is_suggestion
                    else int(profile.get("gateway_read_timeout_seconds", 12))
                )
                generation_temperature = float(
                    profile.get("short_temperature", 0.25)
                    if is_suggestion
                    else profile.get("temperature", 0.35)
                )
                generation_tokens = int(
                    profile.get("short_max_tokens", 180)
                    if is_suggestion
                    else profile.get("max_tokens", max_tokens)
                )
                remaining = max(0.1, deadline - runtime.time.monotonic())
                attempts_left = sum(1 for candidate in candidates[index:] if candidate)
                attempt_budget = min(
                    remaining, max(6, gateway_wait + 6), remaining / attempts_left
                )
                args = (
                    messages,
                    effective_model_id,
                    item.api_base,
                    key,
                    generation_temperature,
                    generation_tokens,
                    thinking_mode,
                    reasoning_effort,
                    min(gateway_wait, attempt_budget),
                )
                if runtime.os.getenv("CHAT_TRANSPORT", "direct").lower() == "modal":
                    import modal

                    call = modal.Function.from_name(
                        "character-chat", "assistant_worker"
                    ).spawn(*args)
                    try:
                        answer = call.get(timeout=attempt_budget)
                    except Exception:
                        try:
                            call.cancel()
                        except Exception:
                            pass
                        raise
                else:
                    answer = runtime._within_deadline(
                        lambda args=args: runtime.direct_completion(*args),
                        attempt_budget,
                    )
                if not isinstance(answer, str) or not answer.strip():
                    raise ValueError("Model returned an empty response")
                runtime.record_model_success(item.id)
                model_ids = [
                    (
                        (candidate.assistant_model_id or candidate.model_id)
                        if candidate
                        else ""
                    )
                    for candidate in candidates
                ]
                return answer.strip(), {
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
                    "actual_model": effective_model_id,
                    "thinking_mode": thinking_mode,
                    "reasoning_effort": reasoning_effort,
                    "latency_ms": int((runtime.time.monotonic() - started) * 1000),
                }
            except Exception as exc:
                runtime.record_model_failure(item.id, exc)
                errors.append(
                    f"{item.assistant_model_id or item.model_id}: {str(exc)[:300]}"
                )
        error = RuntimeError("; ".join(errors) or "No configured model available")
        error.model_errors = errors
        raise error

    runtime.run_assistant_model_chain = run_assistant_model_chain
