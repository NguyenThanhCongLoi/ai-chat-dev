"""Shared gateway connection timeout configuration."""
import math
import os


def gateway_connect_timeout(default: float, request_timeout: float) -> float:
    try:
        value = float(os.getenv("GATEWAY_CONNECT_TIMEOUT_SECONDS", str(default)))
        if not math.isfinite(value):
            value = default
    except ValueError:
        value = default
    return min(max(1, value), 30, request_timeout)
