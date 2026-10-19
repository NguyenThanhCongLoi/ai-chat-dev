"""Author speech/movie barriers without changing interaction IDs or outcomes."""
import json
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1]/'character_chat/story_data/moonfall_arc'
BINDINGS=[(1,'arrow_trap','ARROW_TRAP','fallen_arrow'),(2,'follow_silhouette','ECHO_GIRL',None),(3,'seal_contact','SEAL_TRAP',None),(4,'falling_ceiling','ACADEMY_COLLAPSE',None),(5,'paper_accusation','ARCHIVE_AWAKENS',None),(6,'mirror_desync','MIRROR_DESYNC',None),(7,'gathering_fragments','PALE_MOON_MANIFESTATION','separate_fragments')]

def main():
    for n,suffix,movie,reaction in BINDINGS:
        p=ROOT/f'ch{n:02}.json';ch=json.loads(p.read_text(encoding='utf8'))
        objects={o['id']:o for scene in ch['scenes'] for o in scene['hotspots']}
        obj=objects[ch['id']+'_'+suffix]
        rows=[deepcopy(e) for e in obj['events'] if e['type']!='visual_effect']
        for e in rows:e.pop('visual_event',None)
        narration=[e for e in rows if e['type']=='narration']
        dialogue=[e for e in rows if e['type']=='dialogue']
        if reaction:
            other=objects[ch['id']+'_'+reaction]
            moved=[e for e in other['events'] if e['type']=='dialogue']
            if moved:
                dialogue+=moved
                other['events']=[e for e in other['events'] if e['type']!='dialogue']
        barrier={'type':'visual_effect','visual_event':movie}
        if n==1:
            # Explicitly preserve both warning and instinctive reaction around the movie.
            warning=dialogue[0]
            aftermath=[e for e in dialogue if e is not warning]
            obj['events']=[warning,barrier,*narration,*aftermath]
        elif n in (2,3,4,6):obj['events']=[*dialogue,barrier,*narration]
        else:obj['events']=[barrier,*narration,*dialogue]
        p.write_text(json.dumps(ch,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Sequenced seven chapter events: warning -> movie -> reaction')

if __name__=='__main__':main()
