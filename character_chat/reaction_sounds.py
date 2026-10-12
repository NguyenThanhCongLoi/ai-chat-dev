"""Saved, voice-versioned reaction clips; inference never runs on the chat path."""
import hashlib
import io
import json
import logging
import os
import time
import uuid
import wave
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import defer
from .models import Character, CharacterReactionAsset, CharacterReactionReference, AppSetting, now
from .schemas import CharacterSpec
from .voice_samples import stored_sample, validate_target, assignment_voice

EMOTIONS = ("neutral", "happy", "sad", "angry", "surprised", "shy")
MAX_CLIP_BYTES = 2 * 1024 * 1024
log = logging.getLogger(__name__)

def voice_version(sample):
    return hashlib.sha256(sample.voice_id.encode() + b"\0" + sample.content).hexdigest()

def reaction_reference(db, identifier, target, item):
    voice_id=assignment_voice(item,target)
    if not voice_id: return None
    keys=[identifier]
    if not identifier.startswith("preset:") and item.creation_type=="preset" and item.preset_type:
        keys.append("preset:"+item.preset_type)
    for key in keys:
        sample=db.get(CharacterReactionReference,(key,target))
        if sample and sample.voice_id==voice_id:return sample
    return stored_sample(db,identifier,target,item)

def reaction_voice_for(item, language=None):
    if item.tts_voice_mode=="shared": return item.tts_voice_id
    if language in {"vi","en"}: return getattr(item,"tts_voice_"+language,"")
    return item.tts_voice_en or item.tts_voice_vi

def valid_clip(content):
    if not isinstance(content, bytes) or len(content) > MAX_CLIP_BYTES:
        raise ValueError("Invalid reaction audio size")
    with wave.open(io.BytesIO(content), "rb") as audio:
        duration = audio.getnframes() / audio.getframerate()
        if audio.getnchannels() not in (1, 2) or audio.getsampwidth() != 2 or not .15 <= duration <= 4:
            raise ValueError("Reaction must be PCM16 WAV, 0.15-4 seconds")
        if len(audio.readframes(audio.getnframes())) != audio.getnframes() * audio.getnchannels() * 2:
            raise ValueError("Truncated reaction audio")

def generation_error(exc):
    # Never send raw provider exceptions, credentials or tracebacks to the browser.
    message=str(exc).lower()
    if "reaction generation is disabled" in message:
        return "Reaction generation is disabled. Configure REACTION_GENERATOR_MODE=modal and worker credentials. Saved clips can still play."
    if "too short even after three repeats" in message:
        return "Reference is too short even after three repeats. Upload a sample of at least 2 seconds, preferably 8-15 seconds."
    if "longer than 5 seconds" in message:
        return "Clone reference must be longer than 5 seconds. Upload a longer sample."
    if type(exc).__name__ in {"NotFoundError","NotFound"}:
        return "Reaction worker was not found. Deploy scripts/deploy_reactions.ps1 first."
    if any(value in message for value in ("gated repo","gated repository","401 client error","403 client error","localtokennotfounderror")):
        return "The model download requires Hugging Face access. Configure HF_TOKEN in the worker secret."
    if isinstance(exc, ValueError) and str(exc) in {
        "Incomplete reaction set","Invalid reaction audio size",
        "Reaction must be PCM16 WAV, 0.15-4 seconds","Truncated reaction audio",
        "Model generated silent reaction","Reaction is too long; retry generation",
    }:
        return "Generated clips failed audio validation. Retry generation; inspect the worker logs if it repeats."
    return "Generation failed. Check the character-reactions worker logs and retry."

def setting(db, key, default):
    row = db.get(AppSetting, key)
    return row.value if row else default

def put_setting(db, key, value):
    row = db.get(AppSetting, key)
    if row: row.value = value
    else: db.add(AppSetting(key=key, value=value))

def build_reaction_router(current_user, db_session, admin_auth, session_factory, spec_for_admin, presets, generator=None):
    router = APIRouter()
    def resolve(db, identifier, target):
        item = spec_for_admin(db, identifier)
        sample = reaction_reference(db, identifier, target, item)
        return item, sample

    def sources(db, character):
        item = CharacterSpec.model_validate_json(character.spec)
        result = [(character.id, item)]
        if item.creation_type == "preset" and item.preset_type:
            result.append(("preset:" + item.preset_type, item))
        clone = db.get(AppSetting, "character_clone_source:" + character.id)
        if clone:
            source = db.get(Character, clone.value)
            if source: result.append((source.id, item))
        return result

    def clips_for(db, identifier, sample):
        return db.query(CharacterReactionAsset).options(defer(CharacterReactionAsset.content)).filter_by(
            character_id=identifier, target=sample.target, voice_version=voice_version(sample)).all()

    def generate(reference, filename, repeat_short=False, slots=None):
        if generator: return generator(reference, filename, slots=slots)
        if os.getenv("REACTION_GENERATOR_MODE", "modal") == "disabled":
            raise ValueError("Reaction generation is disabled for this deployment")
        import modal
        return modal.Function.from_name("character-reactions", "generate_reactions").remote(reference, filename, repeat_short, slots)

    def run_job(identifier, target, version, token, repeat_short=False, slots=None, replace=False):
        key = "reaction_status:" + identifier + ":" + target
        try:
            with session_factory() as db:
                _, sample = resolve(db, identifier, target)
                if not sample or voice_version(sample) != version: raise ValueError("Voice changed before generation")
                reference, filename = sample.content, sample.filename
            generated = generate(reference, filename, repeat_short, slots)
            expected = {tuple(slot) for slot in slots}
            received = {(clip["emotion"], clip["variant"]) for clip in generated}
            if received != expected or len(generated) != len(expected): raise ValueError("Incomplete reaction set")
            for clip in generated: valid_clip(clip["audio"])
            with session_factory() as db:
                _, sample = resolve(db, identifier, target)
                state = json.loads(setting(db, key, "{}"))
                if state.get("token") != token: return
                if not sample or voice_version(sample) != version:
                    put_setting(db, key, json.dumps({"status":"stale"})); db.commit(); return
                if replace:
                    db.query(CharacterReactionAsset).filter_by(character_id=identifier, target=target).delete()
                existing={(clip.emotion,clip.variant) for clip in clips_for(db,identifier,sample)}
                for clip in generated:
                    if (clip["emotion"],clip["variant"]) in existing:continue
                    db.add(CharacterReactionAsset(id=uuid.uuid4().hex, character_id=identifier, target=target,
                        emotion=clip["emotion"], variant=clip["variant"], voice_version=version, content=clip["audio"]))
                put_setting(db, key, json.dumps({"status":"ready","version":version})); db.commit()
        except Exception as exc:
            log.exception("Reaction generation failed for %s/%s", identifier, target)
            with session_factory() as db:
                state = json.loads(setting(db, key, "{}"))
                if state.get("token") == token:
                    put_setting(db, key, json.dumps({"status":"failed","version":version,"error":generation_error(exc)}))
                    db.commit()

    def queue_job(db, background, identifier, target, force=False, repeat_short=False):
        validate_target(target)
        _, sample = resolve(db, identifier, target)
        if not sample: raise HTTPException(400, "No current clone reference sample for this voice assignment")
        version = voice_version(sample)
        existing={(clip.emotion,clip.variant) for clip in clips_for(db,identifier,sample)}
        slots=[(emotion,variant) for emotion in EMOTIONS for variant in range(2) if force or (emotion,variant) not in existing]
        if not slots:return {"status":"ready","missing_count":0}
        key = "reaction_status:" + identifier + ":" + target
        state=json.loads(setting(db,key,"{}"))
        if state.get("status")=="generating" and state.get("version")==version and time.time()-state.get("started",0)<1200:
            return {"status":"generating"}
        token = uuid.uuid4().hex
        put_setting(db, key, json.dumps({"status":"generating","version":version,"token":token,"started":time.time()}))
        db.commit()
        background.add_task(run_job, identifier, target, version, token, repeat_short, slots, force)
        return {"status":"generating"}

    @router.get("/v1/admin/characters/{identifier}/reactions")
    def admin_list(identifier: str, target: str = "shared", _: None = Depends(admin_auth), db=Depends(db_session)):
        validate_target(target)
        _, sample = resolve(db, identifier, target)
        clips = clips_for(db, identifier, sample) if sample else []
        missing=[{"emotion":emotion,"variant":variant} for emotion in EMOTIONS for variant in range(2) if not any(clip.emotion==emotion and clip.variant==variant for clip in clips)]
        state = json.loads(setting(db, "reaction_status:" + identifier + ":" + target, "{}"))
        if state.get("status")=="generating" and time.time()-state.get("started",0)>1200:
            state={"status":"failed","version":state.get("version"),"error":"Generation timed out. Retry."}
        if not sample:
            state = {"status":"no_sample"}
        elif state.get("version") and state["version"] != voice_version(sample):
            state = {"status":"ready" if len(clips)==12 else "stale"}
        elif state.get("status") in {"failed","stale"}:
            pass  # Includes failed jobs saved by older builds without a version.
        elif state.get("status") != "generating":
            state = {"status":"ready" if not missing else "partial" if clips else "missing"}
        return {**state, "missing_count":len(missing),"missing":missing, "volume":float(setting(db,"reaction_volume:"+identifier,"0.65")),
            "clips":[{"id":clip.id,"emotion":clip.emotion,"variant":clip.variant,
                      "url":"/v1/admin/characters/"+identifier+"/reactions/"+clip.id+"/audio"} for clip in clips]}

    @router.get("/v1/admin/characters/{identifier}/reactions/reference")
    def reference_info(identifier: str, target: str="shared", _:None=Depends(admin_auth), db=Depends(db_session)):
        validate_target(target)
        _, sample=resolve(db,identifier,target)
        dedicated=isinstance(sample,CharacterReactionReference)
        return {"available":bool(sample),"source":"separate" if dedicated else "clone" if sample else "none",
            "filename":sample.filename if sample else "",
            "url":"/v1/admin/characters/"+identifier+"/reactions/reference/audio?target="+target if sample else ""}

    @router.get("/v1/admin/characters/{identifier}/reactions/reference/audio")
    def reference_audio(identifier: str, target: str="shared", _:None=Depends(admin_auth), db=Depends(db_session)):
        validate_target(target)
        _,sample=resolve(db,identifier,target)
        if not sample:raise HTTPException(404,"Reaction reference not found")
        return Response(sample.content,media_type=sample.mime_type,headers={"Cache-Control":"private, no-store"})

    @router.post("/v1/admin/characters/{identifier}/reactions/reference")
    async def upload_reference(identifier: str, audio:UploadFile=File(...), target:str="shared",
                               _:None=Depends(admin_auth), db=Depends(db_session)):
        validate_target(target)
        item=spec_for_admin(db,identifier);voice_id=assignment_voice(item,target)
        if not voice_id:raise HTTPException(400,"Assign a voice to this slot before uploading a reaction reference")
        filename=(audio.filename or "").replace(chr(92),"/").split("/")[-1][:180]
        extension=filename.rsplit(".",1)[-1].lower() if "." in filename else ""
        formats={"wav":"audio/wav","mp3":"audio/mpeg","flac":"audio/flac","ogg":"audio/ogg","m4a":"audio/mp4"}
        if extension not in formats:raise HTTPException(400,"Use WAV, MP3, FLAC, OGG or M4A")
        content=await audio.read(20*1024*1024+1)
        if not content or len(content)>20*1024*1024:raise HTTPException(400,"Reference must be nonempty and at most 20 MB")
        if extension=="wav":
            try:
                with wave.open(io.BytesIO(content),"rb") as wav:
                    if wav.getnframes()<=0:
                        raise HTTPException(400,"Reference must contain audio")
            except (wave.Error,EOFError):raise HTTPException(400,"Invalid WAV reference")
        row=db.get(CharacterReactionReference,(identifier,target))
        if not row:row=CharacterReactionReference(character_id=identifier,target=target);db.add(row)
        row.voice_id=voice_id;row.filename=filename;row.mime_type=formats[extension]
        row.content=content;row.updated_at=now()
        # Replacing reference cancels the previous job token and invalidates its clips.
        put_setting(db,"reaction_status:"+identifier+":"+target,'{"status":"missing"}')
        db.commit()
        return {"ok":True,"filename":filename}

    @router.delete("/v1/admin/characters/{identifier}/reactions/reference")
    def delete_reference(identifier:str,target:str="shared",_:None=Depends(admin_auth),db=Depends(db_session)):
        validate_target(target);spec_for_admin(db,identifier)
        db.query(CharacterReactionReference).filter_by(character_id=identifier,target=target).delete()
        put_setting(db,"reaction_status:"+identifier+":"+target,'{"status":"missing"}')
        db.commit();return {"ok":True}

    @router.post("/v1/admin/characters/{identifier}/reactions/generate")
    def admin_generate(identifier: str, background: BackgroundTasks, target: str = "shared", repeat_short:bool=False, missing_only:bool=False,
                       _: None = Depends(admin_auth), db=Depends(db_session)):
        return queue_job(db, background, identifier, target, force=not missing_only, repeat_short=repeat_short)

    @router.post("/v1/admin/system-characters/reactions/backfill")
    def backfill(background: BackgroundTasks, repeat_short:bool=False, _: None = Depends(admin_auth), db=Depends(db_session)):
        queued, missing = [], []
        for item in presets(db):
            identifier = "preset:" + item.preset_type
            for target in ("shared",) if item.tts_voice_mode == "shared" else ("vi","en"):
                try: queued.append({"character":identifier,"target":target,**queue_job(db,background,identifier,target,repeat_short=repeat_short)})
                except HTTPException as exc:
                    if exc.status_code != 400: raise
                    missing.append({"character":identifier,"target":target})
        return {"characters":queued,"missing_samples":missing}

    @router.patch("/v1/admin/characters/{identifier}/reactions")
    def admin_volume(identifier: str, data: dict, _: None = Depends(admin_auth), db=Depends(db_session)):
        spec_for_admin(db, identifier)
        try: volume = float(data["volume"])
        except (KeyError, ValueError, TypeError): raise HTTPException(400,"Invalid volume")
        if not 0 <= volume <= 1: raise HTTPException(400,"Volume must be 0-1")
        put_setting(db,"reaction_volume:"+identifier,str(volume)); db.commit()
        return {"volume":volume}

    @router.delete("/v1/admin/characters/{identifier}/reactions")
    def admin_delete(identifier: str, target: str = "shared", _: None = Depends(admin_auth), db=Depends(db_session)):
        validate_target(target); spec_for_admin(db,identifier)
        db.query(CharacterReactionAsset).filter_by(character_id=identifier,target=target).delete()
        put_setting(db,"reaction_status:"+identifier+":"+target,'{"status":"missing"}')
        db.commit(); return {"ok":True}

    @router.delete("/v1/admin/characters/{identifier}/reactions/{clip_id}")
    def delete_clip(identifier:str,clip_id:str,_:None=Depends(admin_auth),db=Depends(db_session)):
        spec_for_admin(db,identifier)
        clip=db.get(CharacterReactionAsset,clip_id)
        if not clip or clip.character_id!=identifier:raise HTTPException(404,"Reaction not found")
        target=clip.target
        db.delete(clip)
        # Cancel any old generation result so deletion is not undone by a running job.
        put_setting(db,"reaction_status:"+identifier+":"+target,'{"status":"missing"}')
        db.commit();return {"ok":True}

    @router.get("/v1/admin/characters/{identifier}/reactions/{clip_id}/audio")
    def admin_audio(identifier: str, clip_id: str, _: None = Depends(admin_auth), db=Depends(db_session)):
        spec_for_admin(db, identifier)
        clip=db.get(CharacterReactionAsset,clip_id)
        if not clip or clip.character_id != identifier: raise HTTPException(404,"Reaction not found")
        _, sample=resolve(db,identifier,clip.target)
        if not sample or voice_version(sample)!=clip.voice_version: raise HTTPException(404,"Voice changed")
        return Response(clip.content, media_type=clip.mime_type,headers={"Cache-Control":"private, no-store"})

    def user_clip(db, character, clip):
        for identifier,item in sources(db,character):
            sample=reaction_reference(db,identifier,clip.target,item)
            if sample and clip.character_id==identifier and voice_version(sample)==clip.voice_version: return True
        return False

    @router.get("/v1/characters/{character_id}/reactions")
    def user_list(character_id: str, user: str = Depends(current_user), db=Depends(db_session)):
        character=db.get(Character,character_id)
        if not character or character.user_id!=user: raise HTTPException(404,"Character not found")
        result=[]
        for identifier,item in sources(db,character):
            for target in ("shared",) if item.tts_voice_mode=="shared" else ("vi","en"):
                sample=reaction_reference(db,identifier,target,item)
                if not sample: continue
                volume=float(setting(db,"reaction_volume:"+identifier,"0.65"))
                for clip in clips_for(db,identifier,sample):
                    result.append({"id":clip.id,"target":target,"emotion":clip.emotion,"volume":volume,"voice_id":sample.voice_id,
                        "url":"/v1/characters/"+character_id+"/reactions/"+clip.id+"/audio"})
        return {"clips":result}

    @router.get("/v1/characters/{character_id}/reactions/{clip_id}/audio")
    def user_audio(character_id: str, clip_id: str, user: str = Depends(current_user), db=Depends(db_session)):
        character=db.get(Character,character_id); clip=db.get(CharacterReactionAsset,clip_id)
        if not character or character.user_id!=user or not clip or not user_clip(db,character,clip):
            raise HTTPException(404,"Reaction not found")
        return Response(clip.content, media_type=clip.mime_type,headers={"Cache-Control":"private, no-store"})

    return router, queue_job
