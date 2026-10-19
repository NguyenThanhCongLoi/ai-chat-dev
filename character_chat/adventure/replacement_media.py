"""Reviewed media only; persisted gameplay state remains authoritative."""
import json
from copy import deepcopy
from pathlib import Path
DATA=json.loads((Path(__file__).resolve().parents[1]/'story_data/moonfall_arc/replacement_media.json').read_text(encoding='utf8'))
RETIRED_VIDEO_IDS={"memory_transition","memory_exit","memory_space_video","chapter_complete_video","seal_activation","deep_vault_awaken"}

def assets(values):
    template=next(iter(values.values()))
    for supplied in DATA['assets']:
        row=deepcopy(values.get(supplied['id'],template));row.update(supplied,loop=False)
        values[row['id']]=row
    for ident in RETIRED_VIDEO_IDS|{"memory_fragment_core","young_selene","elarion","unknown_girl"}:values.pop(ident,None)
    return values

def visuals(values):
    # Retire generic interstitials from the old prototype. Dedicated story
    # events and each chapter's memory still own their reviewed movies.
    retired={"memory_transition","memory_exit","memory_space_loop","seal_activation","deep_vault_awaken","chapter_complete","chapter_complete_video","memory_space_video"}
    for key,row in values.items():
        movie=row.get("cinematic","")
        if movie in retired or (key=="CHAPTER_COMPLETE" and movie=="ending_video_hidden"):
            row["cinematic"]=""
    template=next(iter(values.values()))
    for key,supplied in DATA['visual_events'].items():
        row=deepcopy(values.get(key,template));row.update(supplied,skippable=True)
        values[key]=row
    return values

def memory_asset(s,ch):
    if ch['order']<8:return ch['memory']['video']
    if s.get('pending_ending')=='between_memory_and_moonlight':return 'memory_video_08'
    return DATA['ending_videos'].get(s.get('pending_ending'))
