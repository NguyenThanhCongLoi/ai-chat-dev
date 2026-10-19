"""Authored expansion: attributed echoes, optional presentation and chapter outros."""
import json,hashlib
from pathlib import Path
from copy import deepcopy
DATA=json.loads((Path(__file__).resolve().parents[1]/"story_data/moonfall_arc/story_beats.json").read_text(encoding="utf8"))
TOPICS={
 "selene_02":["約束","信頼","承诺","信任","약속","신뢰","ကတိ","សន្យា"],
 "selene_03":["記憶","日記","记忆","日记","기억","일기","အမှတ်တရ","អនុស្សាវរីយ៍"],
 "selene_04":["選択","儀式","选择","仪式","선택","의식","ရွေးချယ်","ជម្រើស"],
 "selene_05":["証拠","真実","证据","真相","증거","진실","အမှန်","ការពិត"],
 "selene_06":["手紙","エラリオン","信件","편지","စာ","សំបុត្រ"],
 "selene_07":["時間","失う","时间","시각","시간","အချိန်","ពេលវេលា"],
 "selene_08":["過去","未来","过去","미래","과거","အနာဂတ်","អនាគត"]}
def data(cfg):return cfg.get("adventure",{}).get("story_beats") or DATA
def enabled(cfg):return cfg.get("adventure",{}).get("enrichment_enabled",True)
def extra(s,hotspot):
    if not enabled(s["config"]):return []
    return deepcopy(data(s["config"])["beats"].get(hotspot,[]))
def outro(s):
    from .engine import chapter,text
    return data(s["config"]).get("outros",{}).get(s["chapter_id"]) or text(chapter(s),chapter(s)["reflection_key"])
def speaker_name(s,speaker):
    return data(s["config"]).get("speakers",{}).get(speaker)
def shuffled(rows,s,salt):
    # A run-specific base permutation rotates between chapters. The same
    # semantic choice cannot occupy the same slot throughout an eight-part arc.
    base=sorted(range(len(rows)),key=lambda i:hashlib.sha256((s.get("attempt_id",s["id"])+salt+str(i)).encode()).hexdigest())
    if not base:return rows
    from .engine import chapter
    shift=(chapter(s)["order"]-1)%len(base)
    order=base[shift:]+base[:shift]
    return [rows[i] for i in order]
def visuals(cfg):
    values=deepcopy(cfg["visual_events"])
    # Older CMS/save snapshots predate the magic movie mappings. Supply missing
    # definitions only; explicit CMS choices (including disabled clips) still win.
    from .loader import legacy_seed
    defaults=legacy_seed()["visual_events"]
    for key in ("MAGIC_SEAL_ACTIVATE","VAULT_AWAKEN","MAJOR_REVEAL"):
        values.setdefault(key,deepcopy(defaults[key]))
    from .replacement_media import visuals as replacements
    return replacements(values)

def stage_view(s):
    from .engine import chapter,ready
    ch=chapter(s);metadata=data(s["config"])
    inspected=set(ch["required_inspections"])<=set(s["inspected"])
    current=3 if s["completed"] else 2 if ready(s) or s["phase"]=="memory" else 1 if inspected else 0
    defaults={"observe":{"vi":"Khám phá","en":"Explore"},"compare":{"vi":"Đối chiếu","en":"Compare"},"remember":{"vi":"Ký ức","en":"Memory"},"return":{"vi":"Trở về","en":"Return"}}
    stages=[dict(id=k,title=metadata.get("stages",defaults).get(k,defaults[k]),complete=i<current,current=i==current) for i,k in enumerate(defaults)]
    return stages,metadata.get("scene_notes",{}).get(s["chapter_id"],{})
