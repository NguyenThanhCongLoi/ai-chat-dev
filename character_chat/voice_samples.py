"""Private CMS reference files, independently stored for each voice assignment."""
from fastapi import HTTPException
from sqlalchemy.orm import defer
from .models import CharacterVoiceSample, now

def assignment_voice(spec, target):
    return getattr(spec, "tts_voice_id" if target == "shared" else "tts_voice_" + target, "") or ""

def stored_sample(db, identifier, target, spec, metadata_only=False):
    query = db.query(CharacterVoiceSample)
    if metadata_only:
        query = query.options(defer(CharacterVoiceSample.content))
    voice_id = assignment_voice(spec, target)
    row = query.filter_by(character_id=identifier, target=target).first()
    if not row and not identifier.startswith("preset:") and getattr(spec, "creation_type", "") == "preset" and getattr(spec, "preset_type", ""):
        row = query.filter_by(character_id="preset:" + spec.preset_type, target=target).first()
    # Manual reassignment must never display the reference for a different voice.
    return row if row and row.voice_id == voice_id and voice_id else None

def save_sample(db, identifier, target, voice_id, filename, mime_type, content, language, ref_text):
    row = db.get(CharacterVoiceSample, (identifier, target))
    if not row:
        row = CharacterVoiceSample(character_id=identifier, target=target)
        db.add(row)
    row.voice_id, row.filename, row.mime_type = voice_id, filename, mime_type
    row.content, row.sample_language, row.ref_text = content, language, ref_text
    row.updated_at = now()
    db.commit()

def validate_target(target):
    if target not in {"shared", "vi", "en"}:
        raise HTTPException(400, "Invalid voice assignment")
