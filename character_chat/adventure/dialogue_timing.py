"""Upgrade shipped dialogue timing without altering progress, puzzles or rewards."""
from copy import deepcopy
BINDINGS=((1,'arrow_trap','ARROW_TRAP','fallen_arrow'),(2,'follow_silhouette','ECHO_GIRL',None),(3,'seal_contact','SEAL_TRAP',None),(4,'falling_ceiling','ACADEMY_COLLAPSE',None),(5,'paper_accusation','ARCHIVE_AWAKENS',None),(6,'mirror_desync','MIRROR_DESYNC',None),(7,'gathering_fragments','PALE_MOON_MANIFESTATION','separate_fragments'))

def upgrade(cfg):
    for n,suffix,movie,reaction in BINDINGS:
        ch=next((c for c in cfg.get('chapters',[]) if c['id']==f'selene_{n:02}'),None)
        if not ch:continue
        objects={o['id']:o for p in ch['scenes'] for o in p['hotspots']}
        obj=objects.get(ch['id']+'_'+suffix)
        if not obj or not any(e.get('visual_event')==movie for e in obj['events']):continue
        if any(e['type'] not in ('narration','dialogue','visual_effect') for e in obj['events']):continue
        if any(e['type']=='visual_effect' and e.get('visual_event')!=movie for e in obj['events']):continue
        rows=deepcopy([e for e in obj['events'] if e['type']!='visual_effect'])
        for e in rows:
            if e.get('visual_event')==movie:e.pop('visual_event')
        narration=[e for e in rows if e['type']=='narration']
        dialogue=[e for e in rows if e['type']=='dialogue']
        other=objects.get(ch['id']+'_'+reaction) if reaction else None
        if other:
            dialogue+=deepcopy([e for e in other['events'] if e['type']=='dialogue'])
            other['events']=[e for e in other['events'] if e['type']!='dialogue']
        barrier={'type':'visual_effect','visual_event':movie}
        if n==1:
            if not dialogue:continue
            result=[dialogue[0],barrier,*narration,*dialogue[1:]]
        elif n in (2,3,4,6):result=[*dialogue,barrier,*narration]
        else:result=[barrier,*narration,*dialogue]
        obj['events']=result
    return cfg
