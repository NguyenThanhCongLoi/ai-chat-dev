"""Paste this file into one Google Colab cell (install httpx first).

The probe calls a gateway directly from Colab. It never contacts Modal and
does not print the API key or the model's reply text.
"""

import json
import socket
import ssl
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from getpass import getpass
from urllib.parse import urlsplit

import httpx


# Use the exact API base and model ID assigned in your CMS.
API_BASE = "https://gateway.avibi.ai/v1"
MODEL_ID = "deepseek/deepseek-v4-flash"
ATTEMPTS_PER_MODE = 3
PAUSE_SECONDS = 2  # Set to 45-90 to check stale keep-alive connections.
CONNECT_TIMEOUT_SECONDS = 8
READ_TIMEOUT_SECONDS = 30
MAX_TOKENS = 256

parsed = urlsplit(API_BASE.rstrip("/"))
if parsed.scheme != "https" or not parsed.hostname:
    raise ValueError("API_BASE must be a full HTTPS URL, for example https://gateway.avibi.ai/v1")
api_key = getpass("Gateway API key (input is hidden): ").strip()
if not api_key:
    raise ValueError("An API key is required to test the model")

host = parsed.hostname
started = time.perf_counter()
try:
    addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)})
    print("DNS", host, addresses, round((time.perf_counter() - started) * 1000), "ms")
    started = time.perf_counter()
    with socket.create_connection((host, parsed.port or 443), timeout=CONNECT_TIMEOUT_SECONDS) as tcp:
        tcp_ms = round((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        with ssl.create_default_context().wrap_socket(tcp, server_hostname=host):
            tls_ms = round((time.perf_counter() - started) * 1000)
    print("TCP", tcp_ms, "ms; TLS", tls_ms, "ms")
except Exception as exc:
    print("DNS/TCP/TLS error:", type(exc).__name__, str(exc)[:180])

timeout = httpx.Timeout(connect=CONNECT_TIMEOUT_SECONDS, read=READ_TIMEOUT_SECONDS, write=10, pool=5)
limits = httpx.Limits(max_connections=2, max_keepalive_connections=1, keepalive_expiry=120)
headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
payload = {
    "model": MODEL_ID,
    "messages": [{"role": "user", "content": "Trả lời đúng một từ: OK"}],
    "max_tokens": MAX_TOKENS,
}
results = []


def send_once(client, mode, attempt):
    request_id = uuid.uuid4().hex[:12]
    row = {
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "attempt": attempt,
        "request_id": request_id,
    }
    started = time.perf_counter()
    try:
        response = client.post(
            API_BASE.rstrip("/") + "/chat/completions",
            headers={**headers, "X-Request-ID": request_id},
            json=payload,
        )
        row["http_status"] = response.status_code
        row["gateway_request_id"] = response.headers.get("x-request-id", "")
        row["cf_ray"] = response.headers.get("cf-ray", "")
        try:
            body = response.json()
            choices = body.get("choices") or [] if isinstance(body, dict) else []
            row["finish_reason"] = choices[0].get("finish_reason", "") if choices else ""
            usage = body.get("usage") or {} if isinstance(body, dict) else {}
            row["output_tokens"] = usage.get("completion_tokens", "")
            if response.is_error:
                error = body.get("error") if isinstance(body, dict) else None
                row["error"] = str(error.get("message", "") if isinstance(error, dict) else error or "")[:180]
        except ValueError:
            row["error"] = "Response was not JSON"
    except httpx.HTTPError as exc:
        row["error_type"] = type(exc).__name__
        row["error"] = str(exc)[:180]
    finally:
        row["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
        results.append(row)
        print(json.dumps(row, ensure_ascii=False))


for mode in ("fresh", "reused"):
    if mode == "fresh":
        for attempt in range(1, ATTEMPTS_PER_MODE + 1):
            with httpx.Client(timeout=timeout, limits=limits, trust_env=False) as client:
                send_once(client, mode, attempt)
            if attempt < ATTEMPTS_PER_MODE:
                time.sleep(PAUSE_SECONDS)
    else:
        with httpx.Client(timeout=timeout, limits=limits, trust_env=False) as client:
            for attempt in range(1, ATTEMPTS_PER_MODE + 1):
                send_once(client, mode, attempt)
                if attempt < ATTEMPTS_PER_MODE:
                    time.sleep(PAUSE_SECONDS)

print("SUMMARY", dict(Counter(str(row.get("error_type") or row.get("http_status")) for row in results)))
