"""Presentation-only props. Never mutate saved story outcomes, clues or inventory."""
from copy import deepcopy
from pathlib import Path
import json,os
DATA=json.loads((Path(__file__).resolve().parents[1]/"story_data/moonfall_arc/props.json").read_text(encoding="utf-8"))
def media_root():
    return Path(os.getenv("CHARACTER_IMAGE_DIR","image"))/"worlds/selene/moonfall"
def manifest_assets(cfg,embedded=True):
    assets={a["id"]:deepcopy(a) for a in cfg["assets"]}
    from .replacement_media import assets as replacements
    if cfg.get("schema_version")==2:assets=replacements(assets)
    from .asset_variants import VIDEO_DURATIONS
    for row in assets.values():
        if row["path"] in VIDEO_DURATIONS:row["duration"]=VIDEO_DURATIONS[row["path"]]
    template=next(iter(assets.values()))
    names=set(DATA["items"].values())|{p["asset"] for p in DATA["hotspots"].values()}|set(DATA.get("reserved_art",{}))
    for name in names:
        ident="prop_"+name
        row=deepcopy(template)
        row.update(id=ident,path="props/prepared/"+name+".webp",type="IMAGE",fallback="",loop=False,duration=0)
        assets[ident]=row
    for ident,name in DATA["items"].items():
        if ident in assets:assets[ident]["path"]="props/prepared/"+name+".webp"
    from .embedded_scenes import manifest
    return manifest(assets) if embedded else assets
def inventory_art(ident,assets):
    if ident in DATA["items"]:return "prop_"+DATA["items"][ident]
    # Missing standalone art must not masquerade as a different object.
    item=assets.get(ident)
    return ident if item and (media_root()/item["path"]).is_file() else ""
def hotspot_art(obj,place):
    if obj.get("scene_asset"):
        return dict(asset=obj["scene_asset"],mode=obj.get("presentation_mode","floor"),**{k:obj[k] for k in ("x","y","width","height")})
    row=DATA["hotspots"].get(obj["id"])
    if not row or row["scene"]!=place["id"] or row["background"]!=place["background"]:
        return dict(asset="",mode="marker",x=obj["x"],y=obj["y"],width=obj["width"],height=obj["height"])
    result={k:row[k] for k in ("x","y","width","height","mode")}
    result["asset"]="prop_"+row["asset"]
    return result

def editor_config(cfg):
    result=deepcopy(cfg)
    result["assets"]=list(manifest_assets(cfg,embedded=False).values())
    if result.get("schema_version")!=2:return result
    for ch in result["chapters"]:
        for place in ch["scenes"]:
            for obj in place["hotspots"]:
                visual=hotspot_art(obj,place)
                if visual["asset"]:
                    obj.update(scene_asset=visual["asset"],presentation_mode=visual["mode"],
                        **{k:visual[k] for k in ("x","y","width","height")})
    return result
