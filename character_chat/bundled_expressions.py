"""Named, supplied 3x3 expression sheets. No inference or model downloads."""
import hashlib
import os
import re
import threading
import unicodedata
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps
from .models import AppSetting, CharacterExpressionAsset
from .schemas import uid

# Pixel coordinates refer to the inspected original sheets. Labels and frames
# fall outside these rectangles; scaling permits higher-resolution replacements.
LAYOUTS = {
    "ruby": ((1600,1600), [(2,526),(541,1061),(1077,1598)], [(2,525),(543,1061),(1078,1598)]),
    "ha": ((1600,1600), [(36,512),(561,1040),(1088,1565)], [(38,480),(566,1007),(1091,1533)]),
    "kimanh": ((1920,1280), [(66,623),(674,1247),(1297,1854)], [(35,397),(455,815),(873,1200)]),
    "trinhkhainguyen": ((1920,1280), [(22,609),(662,1244),(1302,1889)], [(18,357),(445,787),(877,1216)]),
    "mira": ((1920,1280), [(51,631),(671,1250),(1300,1868)], [(37,384),(452,801),(903,1214)]),
    "lyra": ((1296,1616), [(33,421),(451,846),(877,1262)], [(30,472),(559,1005),(1091,1540)]),
    "ren": ((1920,1280), [(67,623),(679,1245),(1300,1851)], [(33,384),(447,804),(869,1196)]),
    "aurelion": ((1600,1600), [(32,508),(561,1038),(1091,1565)], [(32,466),(560,993),(1091,1530)]),
    "merr": ((1600,1600), [(26,519),(555,1046),(1084,1575)], [(26,471),(551,999),(1081,1531)]),
    "nguyenvu": ((1600,1600), [(46,510),(565,1035),(1090,1554)], [(30,482),(553,1010),(1081,1536)]),
}
CELL_NAMES = ("happy","sad","angry","surprised","laughing","crying","winking","playful","thinking")
ALIASES = {
    "ha":"ha", "kimanh":"kimanh", "trinhkhainguyen":"trinhkhainguyen",
    "mira":"mira","mirasunpetal":"mira","lyra":"lyra","aurelion":"aurelion",
    "ren":"ren","ruby":"ruby","merr":"merr","nguyenvu":"nguyenvu",
}
def name_key(name):
    value = unicodedata.normalize("NFKD", str(name)).casefold().replace("đ","d")
    return re.sub(r"[^a-z0-9]", "", value)

def sheet_for(item):
    root = Path(os.getenv("CHARACTER_IMAGE_DIR","image")) / "react"
    names = [getattr(item,"name",""), getattr(item,"display_name","")]
    key = next((ALIASES[name_key(name)] for name in names if name_key(name) in ALIASES), None)
    if key is None:
        # Full fantasy names such as Mira Sunpetal share their named sheet.
        given_names = {"mira","lyra","aurelion","ren","ruby","merr"}
        key = next((first for name in names if (first := name_key(str(name).split()[0] if str(name).split() else "")) in given_names), None)
    if not key or not root.is_dir():return None
    # Exact normalized names only: never assign Ren's image to Renato, etc.
    path = next((p for p in root.iterdir() if p.is_file() and p.suffix.lower() in {".webp",".png",".jpg",".jpeg"} and name_key(p.stem)==key), None)
    return (key,path) if path else None

@lru_cache(maxsize=20)
def split_sheet(key,path,modified,size):
    layout, columns, rows = LAYOUTS[key]
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        scale_x,scale_y = source.width/layout[0],source.height/layout[1]
        images = {}
        for index,name in enumerate(CELL_NAMES):
            left,right = columns[index%3];top,bottom = rows[index//3]
            image = source.crop((round(left*scale_x),round(top*scale_y),round(right*scale_x),round(bottom*scale_y)))
            image.thumbnail((512,512),Image.Resampling.LANCZOS)
            # Preserve the whole face and aspect ratio rather than stretching it.
            canvas = Image.new("RGB",(512,512),"white")
            canvas.paste(image,((512-image.width)//2,(512-image.height)//2))
            out = BytesIO();canvas.save(out,"WEBP",quality=88,method=4)
            images[name] = out.getvalue()
    # The sheets contain no neutral/shy label. Happy Smile is the normal state,
    # and the restrained winking pose for the existing six-state UI.
    images["neutral"] = images["happy"]
    images["shy"] = images["winking"]
    version = "bundled-sheet-v2:"+hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
    return version,images

_install_lock = threading.RLock()

def ensure_bundled_expressions(db,item):
    # Simultaneous emotion preloads must not create duplicate sets.
    with _install_lock:
        return _ensure_bundled_expressions(db,item)

def _ensure_bundled_expressions(db,item):
    found = sheet_for(item)
    if not found:return None
    key,path = found;info=path.stat()
    source_id = "__bundled__:"+key
    version,images = split_sheet(key,str(path.resolve()),info.st_mtime_ns,info.st_size)
    setting_key = "avatar_expression_version:"+source_id
    current = db.get(AppSetting,setting_key)
    if current and current.value==version and db.query(CharacterExpressionAsset.id).filter_by(character_id=source_id).count()==len(images):
        return source_id
    db.query(CharacterExpressionAsset).filter_by(character_id=source_id).delete()
    for emotion,content in images.items():
        db.add(CharacterExpressionAsset(id=uid(),character_id=source_id,emotion=emotion,mime_type="image/webp",content=content))
    if current:current.value=version
    else:db.add(AppSetting(key=setting_key,value=version))
    db.commit()
    return source_id
