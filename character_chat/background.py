import json

from .db import (
    CharacterReflection, Message, MoodObservation, RelationshipEvent, Session,
)
from .engine import llm, similarity
from .retrieval import store_memory
from .schemas import TurnAnalysis, uid
from .roleplay_continuity import auto_memory_enabled


TURN_ANALYSIS_PROMPT = """Analyze one user turn in a character companion chat.
Separate the user's emotion from the AI character's emotion. Decide whether the
emotion or conflict is actually directed at the character. Do not treat anger
about work or another person as anger at the character. Detect meaningful
sharing, appreciation, repair, dismissal, conflict, or boundary setting.
Write a short private character reflection only for a meaningful turn. The
reflection may guide future behavior but must never rewrite the character's
core identity or invent events. Mark memory_worthy only for stable preferences,
personal facts, commitments, or important events. Return structured JSON."""


def _store_reflection(db,user_id,room_id,character_id,analysis):
    text=analysis.reflection.strip()
    if not text or analysis.significance<.62 or analysis.confidence<.6:return
    recent=db.query(CharacterReflection).filter_by(user_id=user_id,character_id=character_id).order_by(CharacterReflection.created_at.desc()).limit(12).all()
    if any(similarity(text,item.content)>.86 for item in recent):return
    db.add(CharacterReflection(id=uid(),user_id=user_id,character_id=character_id,room_id=room_id,content=text,importance=analysis.significance,confidence=analysis.confidence))


def analyze_turn(user_id,room_id,message_id,character_ids):
    """Low-cost post-response analysis. Failures never affect chat delivery."""
    try:
        with Session() as db:
            message=db.get(Message,message_id)
            if not message:return
            replies=db.query(Message).filter_by(room_id=room_id,sender_type="character").order_by(Message.created_at.desc()).limit(max(1,len(character_ids))).all()
            payload={"user_message":message.text,"character_replies":[item.text for item in reversed(replies)]}
            from . import jev
            if jev.enabled("emotion"):
                # Decision models cannot write reliable summaries/reflections.
                # Never fall through to a paid prose LLM when JEV is configured.
                result=jev.inspect_text(message.text)
                mood=result["emotion"]; event=result["relationship"]
                label=mood["choice"]
                values={"happy":(.7,.6),"sad":(-.6,.3),"tired":(-.3,.15),"angry":(-.6,.8),"anxious":(-.5,.75),"apologetic":(-.2,.35),"neutral":(0,.3)}
                valence,arousal=values[label]
                event_type=event["choice"] if len(character_ids)==1 and event["confidence"]>=.7 else "none"
                analysis=TurnAnalysis(user_emotion=label,valence=valence,arousal=arousal,
                    confidence=mood["confidence"],relationship_event=event_type,
                    directed_at_character=event_type!="none",event_valence=valence,
                    significance=.5,memory_worthy=False)
            else:
                analysis=llm.json(
                    [{"role":"system","content":TURN_ANALYSIS_PROMPT},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}],
                    TurnAnalysis,model=llm.fallback_model,max_tokens=700,
                )
            # The room may have been deleted while the model was analyzing it.
            # Discard the previous read snapshot before checking the source again.
            db.rollback()
            source=db.query(Message).filter_by(id=message_id,room_id=room_id).first()
            if not source:return
            from .conversation_reset import source_was_reset
            if source_was_reset(db,user_id,character_ids,source.created_at):return
            if analysis.confidence>=.6:
                db.add(MoodObservation(id=uid(),user_id=user_id,room_id=room_id,source_message_id=message_id,emotion=analysis.user_emotion[:50],valence=analysis.valence,arousal=analysis.arousal,confidence=analysis.confidence,directed_at_character=int(analysis.directed_at_character)))
            if analysis.relationship_event!="none" and analysis.confidence>=.6:
                for character_id in character_ids:
                    db.add(RelationshipEvent(id=uid(),user_id=user_id,character_id=character_id,room_id=room_id,source_message_id=message_id,event_type=analysis.relationship_event,valence=analysis.event_valence,confidence=analysis.confidence,deltas="{}"))
            remember=auto_memory_enabled(db,user_id,room_id)
            if remember:
                for character_id in character_ids:_store_reflection(db,user_id,room_id,character_id,analysis)
            if remember and analysis.memory_worthy and analysis.memory_summary.strip() and analysis.confidence>=.68:
                visibility="CHARACTER_PRIVATE" if len(character_ids)==1 else "ROOM_SHARED"
                store_memory(db,user_id=user_id,character_id=character_ids[0] if len(character_ids)==1 else None,room_id=None if len(character_ids)==1 else room_id,visibility=visibility,content=analysis.memory_summary.strip()[:400],importance=max(.55,analysis.significance),confidence=analysis.confidence,type="llm_extracted",source_message_id=message_id)
            db.commit()
    except Exception:
        return
