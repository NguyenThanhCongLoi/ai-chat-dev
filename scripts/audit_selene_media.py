"""Audit current World runtime media without obsolete conversion history."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from character_chat.adventure.loader import seed
from character_chat.adventure.props import manifest_assets, media_root
from character_chat.adventure.asset_variants import presentation_path
from character_chat.adventure.embedded_scenes import DATA

def audit():
    root=media_root()
    rows=[]
    for ident,a in sorted(manifest_assets(seed()).items()):
        path=root/presentation_path(root,a["path"])
        rows.append(dict(id=ident,type=a["type"],path=path.as_posix(),exists=path.is_file(),
                         bytes=path.stat().st_size if path.is_file() else 0))
    hub=json.loads((ROOT/"character_chat/story_data/world_hub.json").read_text(encoding="utf8"))
    for a in hub["assets"]:
        path=ROOT/"image"/a["path"]
        rows.append(dict(id="hub:"+a["id"],type="VIDEO" if path.suffix==".webm" else "IMAGE",
                         path=path.relative_to(ROOT).as_posix(),exists=path.is_file(),
                         bytes=path.stat().st_size if path.is_file() else 0))
    missing=[r for r in rows if not r["exists"] and r["type"] in ("IMAGE","VIDEO")]
    optional_audio=[r["id"] for r in rows if not r["exists"] and r["type"] not in ("IMAGE","VIDEO")]
    return dict(visuals_ready=not missing,missing_visuals=missing,
                optional_audio_not_supplied=optional_audio,assets=rows,
                scene_count=len(DATA["scenes"]),scope="source defaults plus runtime aliases; no database or user data modified")

def main():
    result=audit()
    out=ROOT/"artifacts/cleanup/current-media-audit.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:v for k,v in result.items() if k!="assets"},ensure_ascii=False))
    if not result["visuals_ready"]:raise SystemExit(1)
if __name__=="__main__":main()
