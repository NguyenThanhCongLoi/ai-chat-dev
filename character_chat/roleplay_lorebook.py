"""CMS lore for ordinary chat only. Resolve source identity, then ACL, then rank.
Nothing here reads/writes Worlds or mutates room-owned continuity settings.
"""
import json
from .db import AppSetting, Character, CharacterPublication

PREFIX = "roleplay_lorebook:"

def character_keys(db, character_id):
    """Never identify a source by name/avatar; custom cards cannot spoof preset_type."""
    keys = {"character:" + character_id}
    row = db.get(Character, character_id)
    if not row:
        return keys
    card = json.loads(row.spec)
    if card.get("creation_type") == "preset" and card.get("preset_type"):
        keys.add("preset:" + card["preset_type"])
    seen = {character_id}
    current = character_id
    for _ in range(8):
        link = db.get(AppSetting, "character_clone_source:" + current)
        if not link or link.value in seen:
            break
        source = link.value
        seen.add(source)
        public = db.get(CharacterPublication, source)
        if not public or not public.is_public or not db.get(Character, source):
            break
        keys.add("character:" + source)
        current = source
    return keys

def entries_for(db, character_id):
    keys = character_keys(db, character_id)
    result = []
    # Filter identity and audience BEFORE exposing text to relevance/context code.
    for row in db.query(AppSetting).filter(AppSetting.key.like(PREFIX + "%")).all():
        entry = json.loads(row.value)
        if not entry["enabled"] or not keys.intersection(entry["targets"]):
            continue
        if entry["scope"] in ("private", "witnessed") and not keys.intersection(entry["knowers"]):
            continue
        result.append({**entry, "id": "cms:" + entry["id"], "source": "cms"})
    return result
