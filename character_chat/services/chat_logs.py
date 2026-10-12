"""services.chat_logs: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_save_ai_request_log(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def save_ai_request_log(
        db,
        user_id,
        room_id,
        user_message_id,
        response_message_id,
        product,
        task,
        meta,
        latency_ms,
        error="",
        output_text="",
        character_id=None,
    ):
        actual = str(
            meta.get("actual_model")
            or (
                meta.get("fallback_model")
                if meta.get("fallback_used")
                else meta.get("primary_model")
            )
            or ""
        )
        thinking_mode = str(
            meta.get("thinking_mode")
            or runtime.character_engine.llm.model_thinking_modes.get(actual, "default")
        )
        reasoning_effort = str(
            meta.get("reasoning_effort")
            or runtime.character_engine.llm.model_reasoning_efforts.get(
                actual, "default"
            )
        )
        primary_name, primary_base = runtime.model_log_snapshot(
            db,
            str(meta.get("primary_model_config_id") or ""),
            str(meta.get("primary_model") or ""),
            product,
        )
        actual_name, actual_base = runtime.model_log_snapshot(
            db, str(meta.get("actual_model_config_id") or ""), actual, product
        )
        log = runtime.AIRequestLog(
            id=runtime.uid(),
            user_id=user_id,
            room_id=room_id,
            user_message_id=user_message_id,
            response_message_id=response_message_id,
            product=product,
            task=task,
            primary_model=str(meta.get("primary_model") or ""),
            primary_model_config_id=str(meta.get("primary_model_config_id") or ""),
            primary_model_name=primary_name,
            primary_api_base=primary_base,
            actual_model_config_id=str(meta.get("actual_model_config_id") or ""),
            actual_model_name=actual_name,
            actual_api_base=actual_base,
            gateway_snapshot_source=(
                "captured" if primary_base or actual_base else "unknown"
            ),
            fallback_model=str(meta.get("fallback_model") or ""),
            fallback_model_2=str(meta.get("fallback_model_2") or ""),
            fallback_used=int(bool(meta.get("fallback_used"))),
            fallback_reason=str(meta.get("fallback_reason") or "")[:2000],
            actual_model=actual,
            thinking_mode=thinking_mode,
            reasoning_effort=reasoning_effort,
            output_text=str(output_text)[:12000],
            continuation_count=max(0, int(meta.get("continuation_count") or 0)),
            finish_status=str(meta.get("finish_status") or ""),
            latency_ms=max(0, int(latency_ms)),
            error=str(error)[:1000],
        )
        for field in (
            "server_prepare_ms",
            "gateway_headers_ms",
            "gateway_first_chunk_ms",
        ):
            value = meta.get(field)
            if value is not None:
                setattr(log, field, max(0, int(value)))
        db.add(log)
        runtime.capture_log_conversation(db, log, character_id=character_id)
        if meta.get("group_routing"):
            snapshot = runtime.json.loads(log.conversation_snapshot or "{}")
            snapshot["group_routing"] = meta["group_routing"]
            log.conversation_snapshot = runtime.json.dumps(snapshot, ensure_ascii=False)

    runtime.save_ai_request_log = save_ai_request_log

    def roleplay_model_options(db, model_id, short=False):
        item = (
            (
                db.get(runtime.ModelConfig, model_id)
                or db.query(runtime.ModelConfig)
                .filter_by(model_id=model_id, enabled=1)
                .first()
            )
            if model_id
            else None
        )
        profile = runtime.model_profile(db, item) if item and item.enabled else {}
        temperature_key = "short_temperature" if short else "temperature"
        tokens_key = "short_max_tokens" if short else "max_tokens"
        default_temperature = (
            runtime.llm.short_temperature if short else runtime.llm.default_temperature
        )
        default_tokens = (
            runtime.llm.short_max_tokens if short else runtime.llm.default_max_tokens
        )
        return float(profile.get(temperature_key, default_temperature)), max(
            1, int(profile.get(tokens_key, default_tokens))
        )

    runtime.roleplay_model_options = roleplay_model_options
