"""Presentation of painted items; story clues and rewards remain authoritative."""
import json
from pathlib import Path
from copy import deepcopy
DATA=json.loads((Path(__file__).resolve().parents[1]/'story_data/moonfall_arc/embedded_scenes.json').read_text(encoding='utf-8'))
def manifest(assets):
    template=next(iter(assets.values()))
    for row in list(DATA['scenes'].values())+[o['cleanup'] for o in DATA['hotspots'].values() if o.get('cleanup')]:
        asset=deepcopy(template)
        asset.update(id=row['asset'],path=row['path'],type='IMAGE',fallback='',loop=False,duration=0)
        assets[asset['id']]=asset
    return assets
def layout(s,place):
    row=DATA['scenes'].get(s['chapter_id']+':'+place['id'])
    if not row:
        from .engine import chapter
        from .exploration import same_map
        row=next((DATA['scenes'][s['chapter_id']+':'+p['id']] for p in chapter(s)['scenes']
                  if same_map(s,p['id'],place['id']) and s['chapter_id']+':'+p['id'] in DATA['scenes']),None)
    if not row or row.get('background',place['background'])!=place['background']:return None
    if any(o.get('scene_asset') and not o['scene_asset'].startswith('prop_') for o in place['hotspots']):return None
    return row
def removed(s,ident):
    known=set(s['inspected'])
    return any(ident in r.get('erase_after',[]) and set(r['erase_after'])<=known for r in DATA['hotspots'].values())
def object_layout(s,obj,place):
    if not layout(s,place):return {}
    row=DATA['hotspots'].get(obj['id'])
    if not row:return {}
    if row.get('mode')=='prop':return dict(row['presentation'])
    points=row['polygon'];xs=[p[0] for p in points];ys=[p[1] for p in points]
    return dict(asset='',mode='embedded',polygon=points,removed=removed(s,obj['id']),x=min(xs),y=min(ys),width=max(xs)-min(xs),height=max(ys)-min(ys))
def scene_view(s,place):
    row=layout(s,place)
    if not row:return None
    known=set(s['inspected']);patches=[]
    from .engine import chapter
    from .exploration import same_map
    for obj in [o for p in chapter(s)["scenes"] if same_map(s,p["id"],place["id"]) for o in p["hotspots"]]:
        visual=DATA['hotspots'].get(obj['id'],{})
        if 'cleanup' in visual:
            patches.append({k:v for k,v in visual['cleanup'].items() if k!='path'}|{'visible':set(visual['erase_after'])<=known})
    covers=[]
    key=next((o for p in chapter(s)["scenes"] if same_map(s,p["id"],place["id"]) for o in p["hotspots"] if o["id"]=="selene_01_collapsed_path"),None)
    if key:
        from .exploration import object_open
        origin=next(p for p in chapter(s)["scenes"] if key in p["hotspots"])
        covers.append(dict(id=key["id"],asset="prop_ch02_petal_under_stone",x=.54,y=.69,width=.24,height=.30,
                           visible=key["id"] in known or not object_open(s,origin,key)))
    background=row['asset']
    after=row.get("after_inspection",{})
    if after.get("id") in known:background=after["asset"]
    if s["chapter_id"]=="selene_08" and place["id"] in {"decision_threshold","final_chamber"} and s.get("ending")=="between_memory_and_moonlight":
        background="official_bg_ch08_final_chamber_secret"
    return dict(background=background,width=row['width'],height=row['height'],cleanups=patches,covers=covers)
