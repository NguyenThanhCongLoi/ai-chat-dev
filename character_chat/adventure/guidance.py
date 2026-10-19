"""Upgrade shipped exploration copy without replacing CMS edits or story outcomes."""
import json
from pathlib import Path
from functools import lru_cache
from .languages import enrich

@lru_cache(maxsize=1)
def changes():
    return json.loads((Path(__file__).resolve().parents[1]/"story_data/moonfall_arc/guidance_upgrade.json").read_text(encoding="utf-8"))

def upgrade(cfg):
    for row in changes():
        ch=next((c for c in cfg.get("chapters",[]) if c["id"]==row["chapter"]),None)
        if not ch:continue
        current=ch["localization"].get(row["key"],{})
        if any(current.get(k)!=row["old"].get(k) for k in ("vi","en")):continue
        previous=enrich(row["old"])
        custom={k:v for k,v in current.items() if k not in ("vi","en") and v!=previous.get(k)}
        ch["localization"][row["key"]]={**enrich(row["new"]),**custom}
    return cfg

def observation(s,obj):
    from .engine import chapter,text
    # The authored inspection dialogue suggests where/how to look, never the solution.
    raw=None if obj["id"] in {"selene_01_old_gate","selene_01_collapsed_path"} else next((e for e in obj["events"] if e["type"]=="dialogue" and e.get("text_key")),None)
    if raw:return text(chapter(s),raw["text_key"])
    from .languages import observation_hint
    return observation_hint(obj["title"])
