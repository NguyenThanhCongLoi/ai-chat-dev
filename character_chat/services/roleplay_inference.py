"""services.roleplay_inference: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_stream_roleplay_answer(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def stream_roleplay_answer(prompt, temperature, max_tokens, profile_mode):
        """Stream a roleplay reply through the configured model chain."""
        prompt = runtime.roleplay_output_prompt(prompt)
        candidates = list(
            dict.fromkeys(
                model
                for model in (
                    runtime.llm.model,
                    runtime.llm.fallback_model,
                    runtime.llm.fallback_model_2,
                )
                if model
            )
        )
        if not candidates:
            raise RuntimeError("No roleplay model assigned in CMS")
        waits = [
            max(4, min(45, float(runtime.llm.model_gateway_timeouts.get(model, 12))))
            for model in candidates
        ]
        budget = max(
            8,
            min(90, float(runtime.os.getenv("LLM_FALLBACK_BUDGET_SECONDS", "28"))),
            max(waits) + (12 if len(candidates) > 1 else 0),
        )
        deadline = runtime.time.monotonic() + budget
        errors = []
        for index, model in enumerate(candidates):
            remaining = deadline - runtime.time.monotonic()
            if remaining <= 0:
                errors.append("total fallback budget exhausted")
                break
            settings = runtime.llm.model_generation.get(model, {})
            prefix = "short_" if profile_mode == "short" else ""
            model_temperature = float(settings.get(prefix + "temperature", temperature))
            model_tokens = max(1, int(settings.get(prefix + "max_tokens", max_tokens)))
            messages = (
                prompt
                if index == 0 or not runtime.llm.fallback_instruction.strip()
                else [
                    {"role": "system", "content": runtime.llm.fallback_instruction},
                    *prompt,
                ]
            )
            wire = lambda value: (
                runtime.llm.model_wire_ids.get(value, value) if value else ""
            )
            meta = {
                "primary_model": wire(runtime.llm.model),
                "primary_model_config_id": (
                    runtime.llm.model
                    if runtime.llm.model in runtime.llm.model_wire_ids
                    else ""
                ),
                "fallback_model": wire(runtime.llm.fallback_model),
                "fallback_model_2": wire(runtime.llm.fallback_model_2),
                "fallback_used": index > 0,
                "fallback_level": index,
                "fallback_reason": " | ".join(errors),
                "actual_model": wire(model),
                "actual_model_config_id": (
                    model if model in runtime.llm.model_wire_ids else ""
                ),
                "thinking_mode": runtime.llm.model_thinking_modes.get(model, "default"),
                "reasoning_effort": runtime.llm.model_reasoning_efforts.get(
                    model, "default"
                ),
            }
            emitted = False
            status = "unknown"
            language_stream = runtime.LanguageStream()
            try:
                cooldown = runtime.model_circuit_remaining(model)
                if cooldown:
                    raise RuntimeError(
                        f"circuit breaker active for {cooldown:.1f}s after a recent network failure"
                    )
                key = runtime.llm.model_api_keys.get(model, runtime.llm.api_key)
                if not key:
                    raise RuntimeError(
                        f"No API key configured for {runtime.llm.model_api_bases.get(model,runtime.llm.url)}"
                    )
                stream = runtime.chat_stream(
                    messages,
                    runtime.llm.model_wire_ids.get(model, model),
                    runtime.llm.model_api_bases.get(model, runtime.llm.url),
                    key,
                    model_temperature,
                    model_tokens,
                    meta["thinking_mode"],
                    meta["reasoning_effort"],
                    max(0.1, min(waits[index], remaining)),
                )
                for chunk in runtime.bounded_remote_chunks(stream, deadline):
                    if isinstance(chunk, dict) and chunk.get("_gateway_timing"):
                        meta.update(chunk["_gateway_timing"])
                        continue
                    if isinstance(chunk, dict) and chunk.get("_stream_status"):
                        status = str(chunk["_stream_status"])
                        continue
                    if not isinstance(chunk, str) or not chunk:
                        continue
                    for event, value in language_stream.feed(chunk):
                        if event == "delta":
                            emitted = True
                        yield event, value
                for event, value in language_stream.feed("", final=True):
                    if event == "delta":
                        emitted = True
                    yield event, value
                if status not in ("complete", "truncated"):
                    raise RuntimeError(
                        f"Stream ended without a completion marker (status={status})"
                    )
                if status == "truncated":
                    meta["finish_status"] = "partial"
                    meta["fallback_reason"] = (
                        meta["fallback_reason"] + " | "
                        if meta["fallback_reason"]
                        else ""
                    ) + f"{model}: token limit reached"
                else:
                    meta["finish_status"] = "complete"
                    runtime.record_model_success(model)
                yield "complete", meta
                return
            except Exception as exc:
                runtime.record_model_failure(model, exc)
                reason = f"{model}: {type(exc).__name__}: {str(exc)[:400]}"
                if emitted:
                    meta["finish_status"] = "partial"
                    meta["fallback_reason"] = (
                        meta["fallback_reason"] + " | "
                        if meta["fallback_reason"]
                        else ""
                    ) + reason
                    yield "complete", meta
                    return
                errors.append(reason)
        raise RuntimeError("; ".join(errors) or "No configured model available")

    runtime.stream_roleplay_answer = stream_roleplay_answer

    def generate_roleplay_suggestions(
        prompt, character, message, previous, temperature, max_tokens
    ):
        started = runtime.time.monotonic()
        raw, meta = runtime.llm.chat_with_meta(
            runtime.suggestion_prompt(prompt, character, message, previous),
            temperature,
            max_tokens,
            runtime.llm.purpose_models.get("suggestion"),
            runtime.llm.purpose_models.get("suggestion_fallback") or "",
            runtime.llm.purpose_models.get("suggestion_fallback_2") or "",
            profile_mode="short",
            gateway_timeout_cap_seconds=8,
            total_budget_seconds=runtime.suggestion_budget(),
        )
        return (
            runtime.parse_suggestions(raw),
            meta,
            int((runtime.time.monotonic() - started) * 1000),
        )

    runtime.generate_roleplay_suggestions = generate_roleplay_suggestions

    def roleplay_suggestion_initial_meta():
        # Preserve the CMS assignment when the model raises before returning metadata.
        wire = lambda value: (
            runtime.llm.model_wire_ids.get(value, value) if value else ""
        )
        return {
            "primary_model": wire(runtime.llm.purpose_models.get("suggestion")),
            "primary_model_config_id": (
                runtime.llm.purpose_models.get("suggestion")
                if runtime.llm.purpose_models.get("suggestion")
                in runtime.llm.model_wire_ids
                else ""
            ),
            "fallback_model": wire(
                runtime.llm.purpose_models.get("suggestion_fallback")
            ),
            "fallback_model_2": wire(
                runtime.llm.purpose_models.get("suggestion_fallback_2")
            ),
            "fallback_used": False,
        }

    runtime.roleplay_suggestion_initial_meta = roleplay_suggestion_initial_meta

    def roleplay_suggestion_error(exc):
        if isinstance(exc, runtime.concurrent.futures.TimeoutError):
            return "Suggestion was not ready within 1 second after the main reply"
        return f"{type(exc).__name__}: {exc}"[:500]

    runtime.roleplay_suggestion_error = roleplay_suggestion_error
