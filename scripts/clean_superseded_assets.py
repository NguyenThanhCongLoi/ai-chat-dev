"""Delete reviewed obsolete World files and local build caches, never user data.
Default is a dry run. --apply writes a deletion ledger before removing files.
"""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from character_chat.adventure.loader import seed
from character_chat.adventure.props import manifest_assets, media_root
from character_chat.adventure.asset_variants import presentation_path

def checked(path):
    path=path.resolve()
    if not path.is_relative_to(ROOT) or path==ROOT:
        raise ValueError("Cleanup target escapes the workspace")
    if path.name==".env" or path.name.startswith(".env.") or path.name in {"secrets.vault.json",".docs-credentials"}:
        raise ValueError("Protected credentials")
    if any(part in {".git","backups","data","data-dev",".tools",".tmp_db_check"} for part in path.relative_to(ROOT).parts):
        raise ValueError("Protected cleanup target")
    return path

def plan():
    assets=manifest_assets(seed())
    media=media_root().resolve()
    active={checked(media/presentation_path(media,a["path"])) for a in assets.values()
            if (media/presentation_path(media,a["path"])).is_file()}
    hub=json.loads((ROOT/"character_chat/story_data/world_hub.json").read_text(encoding="utf8"))
    active.update(checked(ROOT/"image"/a["path"]) for a in hub["assets"])
    choices={}
    def add(path,reason):
        path=checked(path)
        if path.is_file():
            if path in active:raise ValueError("Refusing to delete active media: "+str(path))
            choices[path]=reason
    for path in (media/"video").rglob("*"):
        if path.is_file() and path.suffix.lower() in {".mp4",".webm"} and path.resolve() not in active:
            add(path,"superseded World video; current manifest uses official media")
    add(ROOT/"image/worlds/hub/video/selene_intro_1080.webm",
        "superseded hub intro; playlist uses selene_intro_20261018_from17.webm")
    for name in ("locations","memories","reveals"):
        add(media/"video"/name/".gitkeep","obsolete video folder scaffold")
    for name in ("Elarion Vael.png","Unknown Girl.png","Young Selene.png"):
        add(media/"characters/cutouts"/name,"supporting portrait renderer removed; no current asset binding")
    add(media/"props/cutouts/memory_fragment_core.png","retired prototype fragment; not in current manifest or inventory")
    obsolete_scripts=[
        "cleanup_redundant_world_videos.py","define_embedded_hotspots.py",
        "extract_memory_locations.py","inspect_selene_replacements.py",
        "install_selene_replacements.py","prepare_embedded_backgrounds.py",
        "prepare_memory_arc_assets.py","prepare_world_images.py","prepare_world_videos.py",
        "export_moonfall_item_placements.py","render_moonfall_placement_diagrams.py",
    ]
    for name in obsolete_scripts:
        add(ROOT/"scripts"/name,"retired media preparation tool; would recreate obsolete paths")
    old_previews=[
        "artifacts/memory-adventure/embedded-bg",
        "artifacts/memory-adventure/full-item-audit",
        "artifacts/memory-adventure/item-placement",
        "artifacts/memory-adventure/item-placement-new-props",
        "artifacts/memory-adventure/location-extraction",
        "artifacts/memory-adventure/corrected-m01-m04",
        "artifacts/memory-adventure/new-props-scenes",
        "artifacts/refactor/npm-temp",
    ]
    cache_roots=[ROOT/".pytest_cache",ROOT/".reaction-cache/node-compile-cache",
                 ROOT/"frontend/node_modules/.vite"]
    # Do not traverse dependency/model environments or nested repository backups.
    for folder in ["character_chat","scripts","tests"]:
        cache_roots.extend((ROOT/folder).rglob("__pycache__"))
    cache_roots.append(ROOT/"__pycache__")
    for directory in cache_roots+[ROOT/p for p in old_previews]:
        directory=checked(directory)
        if not directory.exists():continue
        if directory.is_symlink():raise ValueError("Refusing a linked cleanup directory")
        for path in directory.rglob("*"):
            if path.is_file():add(path,"generated local cache or preview from retired media")
    return active,choices

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    active,choices=plan()
    rows=[]
    for path,reason in sorted(choices.items()):
        rows.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reason=reason))
    out=ROOT/"artifacts/cleanup"
    out.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report=out/(stamp+("-removed" if args.apply else "-plan")+".json")
    report.write_text(json.dumps(dict(applied=args.apply,files=rows,
        total_bytes=sum(r["bytes"] for r in rows)),ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    if args.apply:
        for row in rows:
            path=checked(ROOT/row["path"])
            # Recheck both identity and bounds immediately before deletion.
            if path in active or hashlib.sha256(path.read_bytes()).hexdigest()!=row["sha256"]:
                raise ValueError("File changed since planning: "+row["path"])
            path.unlink()
        # Only prune empty parents of deleted files, inside their original trees.
        for row in reversed(rows):
            parent=(ROOT/row["path"]).parent
            while parent!=ROOT:
                if parent.is_dir() and not any(parent.iterdir()):
                    checked(parent).rmdir()
                    parent=parent.parent
                else:break
    print(json.dumps(dict(applied=args.apply,files=len(rows),MiB=round(sum(r["bytes"] for r in rows)/1048576,2),
                          ledger=report.relative_to(ROOT).as_posix())))
if __name__=="__main__":main()
