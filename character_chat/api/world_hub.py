"""Public presentation manifest and private, read-only memory atlas."""
import json
import os
from pathlib import Path
from .. import moonfall_store as storage
from ..models import Character

MANIFEST = Path(__file__).resolve().parents[1] / "story_data/world_hub.json"

def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))

def bind_world_hub(runtime, chapter_list_for_user):
    app=runtime.app
    @app.get("/v1/moonfall/hub/assets/{ident}")
    def hub_asset(ident:str):
        item=next((a for a in manifest()["assets"] if a["id"]==ident),None)
        if not item:raise runtime.HTTPException(404,"Asset not found")
        root=Path(os.getenv("CHARACTER_IMAGE_DIR","image")).resolve()
        target=(root/item["path"]).resolve()
        if not target.is_relative_to(root) or not target.is_file() or target.suffix not in {".webm",".webp",".png",".jpg",".jpeg"}:
            raise runtime.HTTPException(404,"Asset unavailable")
        return runtime.FileResponse(str(target),headers={"Cache-Control":"public, max-age=300"})

    @app.get("/v1/moonfall/hub/presentation")
    def presentation():
        # Only public media metadata. No user state, gates, or memories.
        data=manifest()
        assets={a["id"]:"/v1/moonfall/hub/assets/"+a["id"] for a in data["assets"]}
        return dict(background=assets.get(data.get("background")),
                    standard_intro=[dict(id=i,url=assets[i]) for i in data.get("standard_intro",[]) if i in assets],
                    intro=[dict(id=i,url=assets[i]) for i in data["intro"] if i in assets])

    @app.get("/v1/moonfall/hub")
    def hub(user:str=runtime.Depends(runtime.current_user),db=runtime.Depends(runtime.db_session)):
        cfg=storage.config(db)
        own=[c for c in db.query(Character).filter_by(user_id=user) if storage.owned_selene(db,user,c.id,cfg)]
        characters=[];seen=set()
        for source in runtime.effective_presets(db):
            if runtime.preset_home_section(db,source)=="hidden":continue
            key=source.preset_type
            name=source.name.strip()
            if not key or name.casefold() in seen:continue
            seen.add(name.casefold())
            matches=own if name.casefold()=="selene moonbrook" else []
            # Prefer the user's playable/resumable instance; never expose another user's card.
            choice=None;chapters=None
            for row in matches:
                status=chapter_list_for_user(db,user,row.id)
                if choice is None or any(c["available"] for c in status["chapters"]):
                    choice=row;chapters=status
                if any(c["available"] for c in status["chapters"]):break
            unlocked=bool(chapters and any(c["available"] for c in chapters["chapters"]))
            characters.append(dict(id="preset:"+key,name=name,avatar_url=source.avatar_url,
                character_id=choice.id if choice else None,unlocked=unlocked,
                reason="" if unlocked else "continue_chat" if name.casefold()=="selene moonbrook" else "coming_soon"))
        from .hub_narration import presentation_config as narration_config
        return dict(characters=characters,narration=narration_config(db),**presentation())
