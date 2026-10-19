"""Reviewed presentation replacements, including aliases for archived source images."""
from pathlib import Path
CHARACTERS=("neutral","serious","worry","determined","fear","touch pendant","magic")
PROPS=() # Superseded by the user-supplied chapter props.
VARIANTS={**{"characters/"+n+".webp":"characters/cutouts/"+n+".png" for n in CHARACTERS},
          **{"props/"+n+".webp":"props/cutouts/"+n+".png" for n in PROPS}}

SOURCE_ALIASES={'backgrounds/Ancient Archive.png': 'backgrounds/echoes_bg_16x9/ch05_archive_records.webp', 'backgrounds/ancient_archive.webp': 'backgrounds/echoes_bg_16x9/ch05_archive_records.webp', 'backgrounds/Ancient Gate.png': 'backgrounds/echoes_bg_16x9/ch01_ancient_gate.webp', 'backgrounds/ancient_gate.webp': 'backgrounds/echoes_bg_16x9/ch01_ancient_gate.webp', 'backgrounds/Blackwood Forest.png': 'backgrounds/echoes_bg_16x9/ch05_witch_house.webp', 'backgrounds/blackwood_forest.webp': 'backgrounds/echoes_bg_16x9/ch05_witch_house.webp', 'backgrounds/Chapter Complete Background.png': 'backgrounds/echoes_bg_16x9/ch08_memory_space.webp', 'backgrounds/chapter_complete_background.webp': 'backgrounds/echoes_bg_16x9/ch08_memory_space.webp', 'backgrounds/Deep Vault.png': 'backgrounds/echoes_bg_16x9/ch06_deep_vault.webp', 'backgrounds/deep_vault.webp': 'backgrounds/echoes_bg_16x9/ch06_deep_vault.webp', 'backgrounds/Inner Ruins.png': 'backgrounds/echoes_bg_16x9/ch02_inner_corridor.webp', 'backgrounds/inner_ruins.webp': 'backgrounds/echoes_bg_16x9/ch02_inner_corridor.webp', 'backgrounds/Map Background  World Select.png': 'backgrounds/echoes_bg_16x9/ch07_between_memories.webp', 'backgrounds/map_background_world_select.webp': 'backgrounds/echoes_bg_16x9/ch07_between_memories.webp', 'backgrounds/Memory Space.png': 'backgrounds/echoes_bg_16x9/ch08_memory_space.webp', 'backgrounds/memory_space.webp': 'backgrounds/echoes_bg_16x9/ch08_memory_space.webp', 'backgrounds/Moon Temple.png': 'backgrounds/echoes_bg_16x9/ch07_moon_temple.webp', 'backgrounds/moon_temple.webp': 'backgrounds/echoes_bg_16x9/ch07_moon_temple.webp', 'backgrounds/Moonfall Outer Ruins.png': 'backgrounds/echoes_bg_16x9/ch01_outer_ruins.webp', 'backgrounds/moonfall_outer_ruins.webp': 'backgrounds/echoes_bg_16x9/ch01_outer_ruins.webp', 'backgrounds/Moonfall Overview.png': 'backgrounds/echoes_bg_16x9/ch01_outer_ruins.webp', 'backgrounds/moonfall_overview.webp': 'backgrounds/echoes_bg_16x9/ch01_outer_ruins.webp', 'backgrounds/Moonfall Past.png': 'backgrounds/echoes_bg_16x9/ch04_academy_intact.webp', 'backgrounds/moonfall_past.webp': 'backgrounds/echoes_bg_16x9/ch04_academy_intact.webp', 'backgrounds/Underground Chamber.png': 'backgrounds/echoes_bg_16x9/ch03_ritual_chamber.webp', 'backgrounds/underground_chamber.webp': 'backgrounds/echoes_bg_16x9/ch03_ritual_chamber.webp', 'backgrounds/Witch Area  Witch House.png': 'backgrounds/echoes_bg_16x9/ch05_witch_house.webp', 'backgrounds/witch_area_witch_house.webp': 'backgrounds/echoes_bg_16x9/ch05_witch_house.webp'}

def presentation_path(root:Path,path:str)->str:
    from .props import DATA
    old=path.rsplit("/",1)[-1].rsplit(".",1)[0]
    replacement=DATA["items"].get(old) if path.startswith("props/") else None
    if path=="props/Elven Council.webp":replacement=DATA["items"]["council_record"]
    candidate=("props/prepared/"+replacement+".webp") if replacement else VARIANTS.get(path) or SOURCE_ALIASES.get(path)
    return candidate if candidate and (root/candidate).is_file() else path


# One duration source: the reviewed official manifest, including saved ID aliases.
from .replacement_media import DATA as MEDIA
VIDEO_DURATIONS={a["path"]:a["duration"] for a in MEDIA["assets"] if a["type"]=="VIDEO"}

from functools import lru_cache
import hashlib
@lru_cache(maxsize=128)
def _video_digest(path,size,mtime):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]

def video_version(root,path):
    file=(root/path).resolve()
    if not file.is_relative_to(root.resolve()) or not file.is_file():return "missing"
    info=file.stat()
    return _video_digest(str(file),info.st_size,info.st_mtime_ns)
