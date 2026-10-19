"""Probe JEV using synthetic text. Does not print keys or provider response bodies."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from character_chat import jev

if not jev.enabled():
    print("JEV disabled or missing env key. Set JEV_API_KEY in the root .env.")
    raise SystemExit(1)
try:
    result = jev.inspect_text("Hello, I am happy to meet you.")
    print("JEV connected. Decision:", result["decision"], "| emotion:", result["emotion"]["choice"])
except jev.JevUnavailable as exc:
    print("JEV probe failed:", str(exc), "(check key, quota, network and model; no secret was printed)")
    raise SystemExit(2)
