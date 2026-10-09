"""Read-only HTTPS connectivity probe from a Modal container.

Run: python -m modal run tests/modal_gateway_probe.py --url https://gateway.avibi.ai/v1/models
No API key or model request is sent.
"""

import time
from urllib.parse import urlparse

import modal


app = modal.App("character-chat-gateway-probe")
image = modal.Image.debian_slim(python_version="3.12").pip_install("httpx>=0.27,<1")


@app.function(image=image, timeout=90)
def probe(url: str, samples: int) -> dict:
    import httpx
    import socket

    target = urlparse(url)
    if target.scheme != "https" or not target.hostname or target.port not in (None, 443):
        raise ValueError("Probe only accepts HTTPS on port 443")
    host = target.hostname
    started = time.perf_counter()
    try:
        addresses = sorted({address[4][0] for address in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        dns = {"addresses": addresses, "latency_ms": round((time.perf_counter() - started) * 1000)}
    except OSError as exc:
        return {"host": host, "dns": {"error": type(exc).__name__}, "requests": []}

    attempts = []
    for _ in range(max(1, min(samples, 20))):
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=httpx.Timeout(12, connect=8), follow_redirects=False) as client:
                response = client.get(url, headers={"User-Agent": "avibi-modal-connectivity-probe/1"})
            attempts.append({"status": response.status_code, "latency_ms": round((time.perf_counter() - started) * 1000)})
        except httpx.HTTPError as exc:
            attempts.append({"error": type(exc).__name__, "latency_ms": round((time.perf_counter() - started) * 1000)})
    return {"host": host, "dns": dns, "requests": attempts}


@app.local_entrypoint()
def main(url: str = "https://gateway.avibi.ai/v1/models", samples: int = 5):
    print(probe.remote(url, samples))
