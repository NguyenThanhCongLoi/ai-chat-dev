"""Content-addressed persistent speech. No story state or credentials are written."""
import hashlib,json,os
from pathlib import Path
from threading import Lock
_guard=Lock()
_pending=set()
def audio_path(model,voice,text,key,owner=None):
    digest=hashlib.sha256(json.dumps([model.id,model.model_id,model.api_base,voice,text,hashlib.sha256(key.encode()).hexdigest(),owner],ensure_ascii=False).encode()).hexdigest()
    return Path(os.getenv("DATA_DIR","data"))/"world_chapter_audio"/(digest+".mp3")
def claim(key):
    with _guard:
        if key in _pending:return False
        _pending.add(key);return True
def release(key):
    with _guard:_pending.discard(key)
