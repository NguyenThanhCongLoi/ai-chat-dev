"""Serve only bundled background audio, never documents or arbitrary paths."""
import hashlib
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import Response
import json
import re
from .models import AppSetting, BackgroundMusicAsset
from fastapi.responses import FileResponse

AUDIO_TYPES = {".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav", ".m4a": "audio/mp4"}


def music_catalog(directory=None):
    root=Path(directory or os.getenv("ROLEPLAY_MUSIC_DIR", Path(__file__).resolve().parent.parent/"music_backgr"/"mp3")).resolve()
    if not root.is_dir():
        return {}
    tracks={}
    for path in sorted(root.rglob("*")):
        resolved=path.resolve()
        if not path.is_file() or path.suffix.lower() not in AUDIO_TYPES or root not in resolved.parents:
            continue
        track_id=hashlib.sha256(path.relative_to(root).as_posix().encode()).hexdigest()[:24]
        tracks[track_id]=resolved
    return tracks



def settings(db):
    row=db.get(AppSetting,"background_music_settings") if db else None
    return json.loads(row.value) if row else {"volume":0.30,"selected_ids":None}

def removed_tracks(db):
    row=db.get(AppSetting,"background_music_removed") if db else None
    return set(json.loads(row.value)) if row else set()

def all_tracks(db):
    tracks=[]
    for key,path in music_catalog().items():
        info=path.stat()
        version=hashlib.sha256(f"{info.st_mtime_ns}:{info.st_size}".encode()).hexdigest()[:12]
        tracks.append({"id":key,"title":path.stem,"url":f"/v1/roleplay/background-music/{key}?v={version}","uploaded":False})
    if db:
        for row in db.query(BackgroundMusicAsset.id,BackgroundMusicAsset.title).all():
            tracks.append({"id":row.id,"title":row.title,"url":f"/v1/roleplay/background-music/{row.id}","uploaded":True})
    removed=removed_tracks(db)
    return [track for track in tracks if track["id"] not in removed]

def build_background_music_router(current_user, db_session=None, admin_auth=None):
    router=APIRouter()
    database=db_session or (lambda: None)

    @router.get("/v1/roleplay/background-music")
    def playlist(user=Depends(current_user),db=Depends(database)):
        config=settings(db)
        tracks=all_tracks(db)
        if config["selected_ids"] is not None:
            tracks=[track for track in tracks if track["id"] in config["selected_ids"]]
        return {"tracks":tracks,"volume":config["volume"]}

    @router.get("/v1/roleplay/background-music/{track_id}")
    def audio(track_id:str,request:Request,db=Depends(database)):
        if track_id in removed_tracks(db):raise HTTPException(404,"Background music not found")
        path=music_catalog().get(track_id)
        if path:
            return FileResponse(path,media_type=AUDIO_TYPES[path.suffix.lower()],headers={"Cache-Control":"public, max-age=3600"})
        row=db.get(BackgroundMusicAsset,track_id) if db else None
        if not row:raise HTTPException(404,"Background music not found")
        content=row.content;size=len(content)
        headers={"Accept-Ranges":"bytes","Cache-Control":"public, max-age=3600"}
        byte_range=request.headers.get("range")
        if byte_range:
            match=re.fullmatch(r"bytes=(\d*)-(\d*)",byte_range)
            if not match or not any(match.groups()):
                return Response(status_code=416,headers={"Content-Range":f"bytes */{size}"})
            start,end=match.groups()
            if start:lower=int(start);upper=min(int(end) if end else size-1,size-1)
            else:lower=max(0,size-int(end));upper=size-1
            if lower>upper or lower>=size:return Response(status_code=416,headers={"Content-Range":f"bytes */{size}"})
            headers["Content-Range"]=f"bytes {lower}-{upper}/{size}"
            return Response(content[lower:upper+1],status_code=206,media_type=row.mime_type,headers=headers)
        return Response(content,media_type=row.mime_type,headers=headers)

    if admin_auth:
        @router.get("/v1/admin/background-music")
        def admin_playlist(_=Depends(admin_auth),db=Depends(database)):
            return {**settings(db),"tracks":all_tracks(db)}

        @router.put("/v1/admin/background-music")
        def configure(data:dict,_=Depends(admin_auth),db=Depends(database)):
            try:volume=float(data.get("volume",settings(db)["volume"]))
            except (KeyError,TypeError,ValueError):raise HTTPException(400,"Volume must be 0 to 100 percent")
            if not 0<=volume<=1:raise HTTPException(400,"Volume must be 0 to 100 percent")
            selected=data.get("selected_ids")
            available={track["id"] for track in all_tracks(db)}
            if selected is not None and (not isinstance(selected,list) or any(not isinstance(key,str) or key not in available for key in selected)):
                raise HTTPException(400,"Unknown music track")
            config={"volume":volume,"selected_ids":None if selected is None else list(dict.fromkeys(selected))}
            row=db.get(AppSetting,"background_music_settings")
            if row:row.value=json.dumps(config)
            else:db.add(AppSetting(key="background_music_settings",value=json.dumps(config)))
            db.commit();return config

        @router.delete("/v1/admin/background-music/{track_id}")
        def delete_track(track_id:str,_=Depends(admin_auth),db=Depends(database)):
            if track_id not in {track["id"] for track in all_tracks(db)}:raise HTTPException(404,"Background music not found")
            uploaded=db.get(BackgroundMusicAsset,track_id)
            if uploaded:db.delete(uploaded)
            else:
                removed=removed_tracks(db);removed.add(track_id)
                row=db.get(AppSetting,"background_music_removed")
                value=json.dumps(sorted(removed))
                if row:row.value=value
                else:db.add(AppSetting(key="background_music_removed",value=value))
            config=settings(db)
            if config["selected_ids"] is not None:
                config["selected_ids"]=[key for key in config["selected_ids"] if key!=track_id]
                row=db.get(AppSetting,"background_music_settings")
                row.value=json.dumps(config)
            db.commit()
            return {"deleted":True}

        @router.post("/v1/admin/background-music/upload")
        def upload(file:UploadFile=File(...),_=Depends(admin_auth),db=Depends(database)):
            suffix=Path(file.filename or "").suffix.lower()
            content=file.file.read(20*1024*1024+1)
            if len(content)>20*1024*1024:raise HTTPException(413,"Maximum audio size is 20 MB")
            valid=(suffix==".mp3" and (content.startswith(b"ID3") or (len(content)>1 and content[0]==255 and content[1]&224==224))) or (suffix==".ogg" and content.startswith(b"OggS")) or (suffix==".wav" and content.startswith(b"RIFF") and content[8:12]==b"WAVE") or (suffix==".m4a" and content[4:8]==b"ftyp")
            if not valid:raise HTTPException(400,"Invalid MP3, OGG, WAV or M4A audio")
            key=hashlib.sha256(content).hexdigest()
            if not db.get(BackgroundMusicAsset,key):
                title=Path((file.filename or "").replace("\\","/")).stem[:120]
                db.add(BackgroundMusicAsset(id=key,title=title,mime_type=AUDIO_TYPES[suffix],content=content))
                db.commit()
            return {"id":key}
    return router
