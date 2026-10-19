"""Continuity for ordinary Roleplay chats: manual canon, scene and memory budget.

Scopes are applied before relevance. No inference calls or GPU dependencies.
All stored state belongs to one private room, even when characters are public.
"""
import json
import unicodedata
from .roleplay_recall import phrase_match
from .db import AppSetting, Room


PREFIX = "roleplay_continuity:"


def defaults():
    return {"revision": 0, "scene": {"location": "", "time": "", "objective": ""},
            "lore": [], "use_memory": True, "auto_memory": True}


def read(db, room_id):
    raw = db.query(AppSetting.value).filter(AppSetting.key == PREFIX + room_id).scalar()
    return json.loads(raw) if raw else defaults()


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold().replace("đ", "d")) if unicodedata.category(c) != "Mn")


def visible_entries(config, character_id):
    return [entry for entry in config["lore"] if entry["scope"] in ("public", "rumor")
            or entry["scope"] in ("private", "witnessed") and character_id in entry["knowers"]
            or entry["scope"] == "discovered" and entry["unlocked"]]


def context(db, user_id, room_id, character_id, query, recent):
    # Ownership is verified here as well as in HTTP handlers: workers use this path.
    room = db.get(Room, room_id)
    if not room or room.user_id != user_id:
        return defaults(), [], {}
    config = read(db, room_id)
    text = fold(query + " " + " ".join(m.text for m in recent[-4:]))
    candidates = []
    from .roleplay_lorebook import entries_for
    for entry in visible_entries(config, character_id) + entries_for(db, character_id):
        matches = sum(phrase_match(key, text) for key in entry["keywords"] if key)
        if entry["always"] or matches:
            candidates.append((matches, entry))
    candidates.sort(key=lambda pair: (-int(pair[1]["canon"]), -pair[1]["priority"], -pair[0], pair[1]["id"]))
    selected = []
    used = 0
    for _, entry in candidates:
        # Actual serialized cost is bounded; entries are never partially truncated.
        item = {k: entry[k] for k in ("id", "title", "text", "scope", "canon")}
        if entry.get("source") == "cms":
            item.update(source="cms", revision=entry["revision"])
        cost = len(json.dumps(item, ensure_ascii=False))
        if used + cost <= 4500:
            selected.append(item)
            used += cost
    scene = {k: v for k, v in config["scene"].items() if v}
    return config, selected, {"scene": scene, "lore_ids": [e["id"] for e in selected],
                              "lore_characters": used, "lore_budget": 4500,
                              "cms_lore_ids": [e["id"] for e in selected if e.get("source") == "cms"]}


def memory_pack(memories, budget=3200):
    selected, payload, used = [], [], 0
    for m in memories:
        item = {"id": m.id, "text": m.content, "scope": m.visibility,
                "confidence": round(m.confidence, 3), "kind":m.type, "pinned": bool(m.pinned),
                "source_message_id": m.source_message_id}
        cost = len(json.dumps(item, ensure_ascii=False))
        if used + cost <= budget:
            selected.append(m)
            payload.append(item)
            used += cost
    return selected, payload, used


def auto_memory_enabled(db, user_id, room_id):
    room = db.get(Room, room_id)
    return bool(room and room.user_id == user_id and read(db, room_id)["auto_memory"])


def remove_character(db, room_id, character_id):
    from .roleplay_episode import key as episode_key
    episode = db.get(AppSetting, episode_key(room_id, character_id))
    if episode:db.delete(episode)
    setting = db.get(AppSetting, PREFIX + room_id)
    if not setting:
        return
    config = json.loads(setting.value)
    updated = []
    for entry in config["lore"]:
        entry = dict(entry)
        entry["knowers"] = [ident for ident in entry["knowers"] if ident != character_id]
        if entry["scope"] in ("private", "witnessed") and not entry["knowers"]:
            continue
        updated.append(entry)
    if updated != config["lore"]:
        config["lore"] = updated
        config["revision"] += 1
        setting.value = json.dumps(config, ensure_ascii=False)
