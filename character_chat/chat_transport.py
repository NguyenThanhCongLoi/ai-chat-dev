"""Direct, pooled OpenAI-compatible chat transport with optional Modal rollback."""
import json
import os
import threading
import time
import httpx
from .assistant_pipeline import extract_assistant_text
from .timeouts import gateway_connect_timeout

_client = None
_client_lock = threading.Lock()


def pooled_client():
    global _client
    with _client_lock:
        if _client is None or _client.is_closed:
            _client = httpx.Client(limits=httpx.Limits(
                max_connections=64, max_keepalive_connections=32, keepalive_expiry=120))
        return _client


def close_chat_transport():
    global _client
    with _client_lock:
        client, _client = _client, None
    if client is not None:
        client.close()


def chat_payload(messages, model, temperature, max_tokens, thinking_mode, reasoning_effort, stream=False):
    payload = {"model": model, "messages": messages}
    if stream:
        payload["stream"] = True
    if "gpt-5" in model:
        payload["max_completion_tokens"] = max_tokens
    else:
        payload.update(temperature=temperature, max_tokens=max_tokens)
    if thinking_mode in ("enabled", "disabled"):
        payload["thinking"] = {"type": thinking_mode}
    if thinking_mode != "disabled" and reasoning_effort in ("low", "high", "max"):
        payload["reasoning_effort"] = reasoning_effort
    return payload


def request_timeout(seconds):
    seconds = max(.1, min(float(seconds), 45))
    return httpx.Timeout(seconds, connect=gateway_connect_timeout(8, seconds),
                         read=seconds, write=min(10, seconds), pool=min(5, seconds))


def raise_gateway_error(response):
    if response.is_error:
        body = response.read().decode("utf-8", "replace")
        raise RuntimeError(f"Gateway HTTP {response.status_code}: {body[:1000]}")


def direct_completion(messages, model, api_base, api_key, temperature=.35, max_tokens=1000,
                      thinking_mode="default", reasoning_effort="default", request_timeout_seconds=12):
    response = pooled_client().post(api_base.rstrip("/") + "/chat/completions",
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        json=chat_payload(messages, model, temperature, max_tokens, thinking_mode, reasoning_effort),
        timeout=request_timeout(request_timeout_seconds))
    raise_gateway_error(response)
    return extract_assistant_text(response.json())


def _sse_data(lines):
    parts = []
    for line in lines:
        if line == "":
            if parts:
                yield "\n".join(parts)
                parts = []
        elif line.startswith("data:"):
            parts.append(line[5:].lstrip())
    if parts:
        yield "\n".join(parts)


def direct_stream(messages, model, api_base, api_key, temperature=.35, max_tokens=1000,
                  thinking_mode="default", reasoning_effort="default", request_timeout_seconds=14):
    """Emit content immediately; reasoning and control metadata stay server-side."""
    started = time.monotonic()
    emitted = False
    finish_reason = ""
    with pooled_client().stream("POST", api_base.rstrip("/") + "/chat/completions",
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        json=chat_payload(messages, model, temperature, max_tokens, thinking_mode, reasoning_effort, True),
        timeout=request_timeout(request_timeout_seconds)) as response:
        raise_gateway_error(response)
        headers_ms = round((time.monotonic() - started) * 1000)
        for value in _sse_data(response.iter_lines()):
            if value == "[DONE]":
                break
            try:
                event = json.loads(value)
            except (ValueError, TypeError):
                continue
            if not isinstance(event, dict):
                continue
            if event.get("error"):
                raise RuntimeError("Gateway stream error: " + str(event["error"])[:1000])
            choices = event.get("choices") or []
            if not choices or not isinstance(choices[0], dict):
                continue
            choice = choices[0]
            finish_reason = choice.get("finish_reason") or finish_reason
            delta = choice.get("delta") or {}
            content = delta.get("content") if isinstance(delta, dict) else None
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content
                                  if isinstance(part, dict) and isinstance(part.get("text"), str))
            if isinstance(content, str) and content:
                if not emitted:
                    yield {"_gateway_timing": {
                        "gateway_headers_ms": headers_ms,
                        "gateway_first_chunk_ms": round((time.monotonic() - started) * 1000),
                        "chat_transport": "direct",
                    }}
                    emitted = True
                yield content
    if not emitted:
        raise RuntimeError(f"Model returned an empty response (finish_reason={finish_reason or 'unknown'})")
    status = "complete" if finish_reason in ("stop", "tool_calls", "content_filter") else (
        "truncated" if finish_reason in ("length", "max_tokens") else "unknown")
    yield {"_stream_status": status}


def chat_stream(*args):
    if os.getenv("CHAT_TRANSPORT", "direct").lower() != "direct":
        raise ValueError("Self-hosted chat requires CHAT_TRANSPORT=direct")
    return direct_stream(*args)
