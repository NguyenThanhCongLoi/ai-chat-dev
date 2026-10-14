"""Server-owned Tarot draws. Card results are persisted in Message.sources."""
import json
import random
import re
import uuid
from pathlib import Path

DECK = json.loads(Path(__file__).with_name("tarot_deck.json").read_text(encoding="utf-8"))

def draw_cards(count=3, rng=None):
    if not 1 <= count <= 10:
        raise ValueError("A spread must have 1 to 10 cards")
    rng = rng or random.SystemRandom()
    shuffled = list(DECK)
    rng.shuffle(shuffled)
    return [{**card, "position": i + 1, "reversed": bool(rng.randrange(2))} for i, card in enumerate(shuffled[:count])]

def prepare_tarot(mode, text, history, db=None, room_id=None):
    if mode != "assistant_tarot":
        return "", None
    previous = None
    for message in reversed(history):
        if message.sender_type not in ("character", "assistant"):
            continue
        try:
            previous = next((source for source in json.loads(message.sources or "[]") if source.get("kind") == "tarot"), None)
        except (ValueError, TypeError):
            pass
        if previous:
            break
    requested = bool(re.search(r"rút|rut|bốc|boc|trải|trai|lá.*hôm nay|draw|shuffle|spread|pull.*card", text, re.I))
    explaining = bool(re.search(r"giải thích|giai thich|ý nghĩa|y nghia|explain|interpret|meaning", text, re.I))
    explicit_new = bool(re.search(r"rút (?:lại|tiếp|mới)|bốc (?:lại|tiếp|mới)|draw (?:again|another|new)|new spread", text, re.I))
    if previous and explaining and not explicit_new:
        requested = False
    educational = bool(re.search(r"tarot là gì|what is tarot|giải thích.*tarot|explain tarot", text, re.I))
    if (not previous and not educational) or requested:
        count_match = re.search(r"(\d+)\s*(?:lá|la\b|cards?\b)", text, re.I)
        count = max(1, min(10, int(count_match.group(1)))) if count_match else (1 if re.search(r"lá.*hôm nay|card.*today|one card|một lá", text, re.I) else 3)
        spread = {"kind": "tarot", "reading_id": uuid.uuid4().hex, "index": 0, "document_id": "", "filename": "Tarot", "cards": draw_cards(count) if db is None else []}
        if db is not None:
            spread.update(draw_from_session(db, room_id, count))
    else:
        spread = previous
    rule = "\nTAROT MODE ONLY. Do not calculate Bát Tự or Tử Vi. Interpret symbolically, not as certain predictions. "
    if spread:
        rule += "The application shuffled all 78 cards. These are authoritative draws, with actual upright/reversed orientation. Do not invent, replace or redraw cards, claim to shuffle yourself, or interpret a reversed card as upright. Explain each supplied card and synthesize the spread in the user's language. For follow-ups use this same spread unless the application provides a new one. DRAW: " + json.dumps(spread["cards"], ensure_ascii=False)
    return rule, spread

def bootstrap_tuvi_models(db, profile_for):
    """Copy existing Tarot model assignments once; CMS edits afterwards are authoritative."""
    from .models import AppSetting, ModelConfig
    marker = "divination:tuvi_models_initialized"
    if db.get(AppSetting, marker):
        return
    models = db.query(ModelConfig).filter_by(assistant_enabled=1).all()
    profiles = [(model, profile_for(db, model)) for model in models]
    if any("assistant_tuvi" in p.get("purposes", []) for _, p in profiles):
        db.add(AppSetting(key=marker, value="true")); db.commit(); return
    changed = False
    for model, profile in profiles:
        aliases = [role.replace("assistant_tarot", "assistant_tuvi", 1) for role in profile.get("purposes", []) if role in {"assistant_tarot","assistant_tarot_fallback","assistant_tarot_fallback_2"}]
        if not aliases:
            continue
        row = db.get(AppSetting, "model_profile:" + model.id)
        values = json.loads(row.value) if row else dict(profile)
        values["purposes"] = list(dict.fromkeys([*profile.get("purposes", []), *aliases]))
        if row: row.value = json.dumps(values, ensure_ascii=False)
        else: db.add(AppSetting(key="model_profile:" + model.id, value=json.dumps(values,ensure_ascii=False)))
        changed = True
    if changed:
        db.add(AppSetting(key=marker, value="true")); db.commit()


def fresh_session():
    deck = [card["id"] for card in DECK]
    random.SystemRandom().shuffle(deck)
    return {"session_id": uuid.uuid4().hex, "remaining": deck}

def session_state(db, room_id):
    from .models import AppSetting
    row = db.get(AppSetting, "tarot_session:" + room_id)
    return json.loads(row.value) if row else None

def reset_session(db, room_id):
    from .models import AppSetting
    state = fresh_session()
    row = db.get(AppSetting, "tarot_session:" + room_id)
    if row: row.value = json.dumps(state)
    else: db.add(AppSetting(key="tarot_session:" + room_id, value=json.dumps(state)))
    return state

def draw_from_session(db, room_id, count):
    """Atomic compare-and-swap prevents two requests consuming the same cards."""
    from .models import AppSetting
    from sqlalchemy.exc import IntegrityError
    from fastapi import HTTPException
    key = "tarot_session:" + room_id
    for _ in range(5):
        row = db.get(AppSetting, key)
        if row is None:
            state = reset_session(db, room_id)
            try: db.commit()
            except IntegrityError: db.rollback()
            row = db.get(AppSetting, key)
        before = row.value
        state = json.loads(before)
        if len(state["remaining"]) < count:
            raise HTTPException(409, "Không đủ lá bài còn lại. Hãy làm mới lượt rút.")
        picked = state["remaining"][:count]
        state["remaining"] = state["remaining"][count:]
        updated = db.query(AppSetting).filter(AppSetting.key == key, AppSetting.value == before).update({"value":json.dumps(state)}, synchronize_session=False)
        if updated:
            db.commit()
            cards_by_id = {card["id"]:card for card in DECK}
            rng = random.SystemRandom()
            cards = [{**cards_by_id[key], "position":i+1, "reversed":bool(rng.randrange(2))} for i,key in enumerate(picked)]
            return {"session_id":state["session_id"], "remaining":len(state["remaining"]), "cards":cards}
        db.rollback()
    raise HTTPException(409, "Lượt rút đang được xử lý. Vui lòng thử lại.")

def reading_is_current(db, room_id, spread, source_message_id):
    from .models import AppSetting, Message
    # Refresh after the provider call: another tab may have reset this room.
    db.rollback()
    if not db.query(Message.id).filter_by(id=source_message_id,room_id=room_id).first():
        return False
    if not spread:
        return True
    state = session_state(db,room_id)
    return bool(state and state["session_id"] == spread.get("session_id"))
