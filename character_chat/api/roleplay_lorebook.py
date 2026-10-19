"""Admin CRUD for ordinary-chat lorebooks; no World feature flag or API dependency."""
import json
import os
import uuid
from ..roleplay_lorebook import PREFIX

def bind_roleplay_lorebook(runtime):
    app = runtime.app

    def catalog(db):
        result = [{"id": "preset:" + (p.preset_type or p.id), "name": p.name, "source": "system"}
                  for p in runtime.effective_presets(db)]
        result += [{"id": "character:" + c.id, "name": c.name, "source": "character", "owner": c.user_id}
                   for c in db.query(runtime.Character).order_by(runtime.Character.name).all()]
        return result

    def get(db, ident):
        row = db.get(runtime.AppSetting, PREFIX + ident)
        if not row:
            raise runtime.HTTPException(404, "Lore entry not found")
        return row, json.loads(row.value)

    def string(value, size):
        if not isinstance(value, str) or len(value) > size:
            raise runtime.HTTPException(422, "Invalid text length")
        return value.strip()

    def validate(db, data):
        clean = {}
        for field in ("title", "text"):
            clean[field] = string(data.get(field, ""), 150 if field == "title" else 1500)
            if not clean[field]:
                raise runtime.HTTPException(422, "Lore title and text are required")
        for field in ("enabled", "canon", "always"):
            value = data.get(field, field == "enabled")
            if type(value) is not bool:
                raise runtime.HTTPException(422, "Expected boolean: " + field)
            clean[field] = value
        scope = data.get("scope", "public")
        if scope not in ("public", "private", "witnessed", "rumor"):
            raise runtime.HTTPException(422, "Invalid scope")
        clean["scope"] = scope
        if scope == "rumor" and clean["canon"]:
            raise runtime.HTTPException(422, "Rumours cannot be locked canon")
        known = {c["id"] for c in catalog(db)}
        for field in ("targets", "knowers"):
            ids = data.get(field, [])
            if not isinstance(ids, list) or len(ids) > 50 or any(not isinstance(i, str) or i not in known for i in ids):
                raise runtime.HTTPException(422, "Select valid characters")
            clean[field] = list(dict.fromkeys(ids))
        if not clean["targets"] or not set(clean["knowers"]).issubset(clean["targets"]):
            raise runtime.HTTPException(422, "Knowledge recipients must be assigned characters")
        if scope == "private" and len(clean["knowers"]) != 1 or scope == "witnessed" and not clean["knowers"]:
            raise runtime.HTTPException(422, "Select who knows this private/witnessed entry")
        if scope in ("public", "rumor"):
            clean["knowers"] = []
        keywords = data.get("keywords", [])
        if not isinstance(keywords, list) or len(keywords) > 12:
            raise runtime.HTTPException(422, "At most 12 keywords")
        clean["keywords"] = list(dict.fromkeys(k for k in (string(k, 60) for k in keywords) if k))
        if not clean["always"] and not clean["keywords"]:
            raise runtime.HTTPException(422, "Add keywords or enable always include")
        priority = data.get("priority", 5)
        if type(priority) is not int or not 0 <= priority <= 10:
            raise runtime.HTTPException(422, "Priority must be 0–10")
        clean["priority"] = priority
        try:
            runtime.ensure_safe_content(clean["title"] + "\n" + clean["text"])
        except ValueError:
            raise runtime.HTTPException(422, "Content requires moderation; revise this entry") from None
        return clean

    def audit(db, action, entry):
        # Metadata only: no private lore text or provider credentials in audit records.
        db.add(runtime.AppSetting(key="roleplay_lorebook_audit:" + uuid.uuid4().hex,
            value=json.dumps({"action": action, "id": entry["id"], "revision": entry["revision"], "at": runtime.now()})))

    @app.get("/roleplay/lorebook/admin", include_in_schema=False)
    def page(_: None = runtime.Depends(runtime.docs_auth)):
        return runtime.FileResponse(os.path.join(os.getenv("FRONTEND_DIST", "frontend/dist"), "index.html"),
                                    headers={"Cache-Control": "no-store"})

    @app.get("/v1/admin/roleplay-lorebook")
    def listing(_: None = runtime.Depends(runtime.docs_auth),
                db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        return {"entries": [json.loads(r.value) for r in db.query(runtime.AppSetting).filter(runtime.AppSetting.key.like(PREFIX + "%")).all()],
                "characters": catalog(db)}

    @app.post("/v1/admin/roleplay-lorebook")
    def create(data: dict, _: None = runtime.Depends(runtime.docs_auth),
               db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        if db.query(runtime.AppSetting).filter(runtime.AppSetting.key.like(PREFIX + "%")).count() >= 1000:
            raise runtime.HTTPException(429, "CMS lore demo limit reached")
        clean = validate(db, data)
        clean.update(id=uuid.uuid4().hex, revision=1, updated_at=runtime.now())
        db.add(runtime.AppSetting(key=PREFIX + clean["id"], value=json.dumps(clean, ensure_ascii=False)))
        audit(db, "create", clean)
        db.commit()
        return clean

    @app.put("/v1/admin/roleplay-lorebook/{ident}")
    def update(ident: str, data: dict, _: None = runtime.Depends(runtime.docs_auth),
               db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        row, old = get(db, ident)
        if type(data.get("revision")) is not int or data["revision"] != old["revision"]:
            raise runtime.HTTPException(409, "Lore changed; reload before saving")
        original = row.value
        clean = validate(db, data)
        clean.update(id=ident, revision=old["revision"] + 1, updated_at=runtime.now())
        count = db.query(runtime.AppSetting).filter_by(key=PREFIX + ident, value=original).update(
            {"value": json.dumps(clean, ensure_ascii=False)}, synchronize_session=False)
        if count != 1:
            db.rollback()
            raise runtime.HTTPException(409, "Lore changed; reload before saving")
        audit(db, "update", clean)
        db.commit()
        return clean

    @app.delete("/v1/admin/roleplay-lorebook/{ident}")
    def delete(ident: str, revision: int, _: None = runtime.Depends(runtime.docs_auth),
               db: runtime.DBSession = runtime.Depends(runtime.db_session)):
        row, old = get(db, ident)
        if revision != old["revision"]:
            raise runtime.HTTPException(409, "Lore changed; reload before deleting")
        count = db.query(runtime.AppSetting).filter_by(key=PREFIX + ident, value=row.value).delete(synchronize_session=False)
        if count != 1:
            db.rollback()
            raise runtime.HTTPException(409, "Lore changed; reload before deleting")
        audit(db, "delete", old)
        db.commit()
        return {"ok": True}
