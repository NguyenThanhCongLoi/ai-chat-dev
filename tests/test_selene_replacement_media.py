"""Supplied videos trigger once, remain presentation-only, and match each route."""
from copy import deepcopy
from pathlib import Path
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from character_chat.adventure.replacement_media import DATA

def test_seven_authored_event_movies_do_not_change_rewards_or_repeat():
    cfg=seed()
    for n,scene,suffix,event in [(1,'side_path','arrow_trap','ARROW_TRAP'),(2,'echo_archway','follow_silhouette','ECHO_GIRL'),(3,'seal_trap','seal_contact','SEAL_TRAP'),(4,'collapse_passage','falling_ceiling','ACADEMY_COLLAPSE'),(5,'archive_defense','paper_accusation','ARCHIVE_AWAKENS'),(6,'mirror_hall','mirror_desync','MIRROR_DESYNC'),(7,'manifestation','gathering_fragments','PALE_MOON_MANIFESTATION')]:
        s=engine.fresh('a','selene','',cfg,'en',.5);s['admin_preview']=True
        s=engine.admin_preview_chapter(s,f'selene_{n:02}')
        if s['phase']=='intro':s=engine.advance(s,'intro_complete')
        s=engine.advance(s,'go',scene)
        fields=('inventory','stats','flags','core_memories','completed_chapters')
        from character_chat.adventure.exploration import next_object
        target=f'selene_{n:02}_'+suffix
        while (pair:=next_object(s,engine.scene(s))) and pair[1]['id']!=target:
            s=engine.advance(s,'inspect',pair[1]['id'])
        before={k:deepcopy(s[k]) for k in fields}
        s=engine.advance(s,'inspect',f'selene_{n:02}_'+suffix)
        assert all(s[k]==v for k,v in before.items())
        output=view(s,{'name':'Selene'})
        movie=output['visual_events'][event]['cinematic']
        assert output['assets'][movie]['type']=='VIDEO'
        assert '?v=' in output['assets'][movie]['url'] and 'missing' not in output['assets'][movie]['url']
        assert sum(e['visual_event']==event for e in s['events'])==1
        again=engine.advance(s,'inspect',f'selene_{n:02}_'+suffix)
        assert sum(e['visual_event']==event for e in again['events'])==1
        assert not any(a.startswith('ending_video_') for a in output['assets'])

def test_all_supplied_replacements_use_web_formats():
    root=Path('image/worlds/selene/moonfall')
    for asset in DATA['assets']:
        assert (root/asset['path']).is_file()
        assert asset['path'].endswith('.webm' if asset['type']=='VIDEO' else '.webp')
    assert set(DATA['ending_videos'])=={'remember_me','let_me_forget','new_keeper'}

def test_m04_introduction_matches_the_new_encounter_and_keeps_vietnamese_accents():
    line=seed()['chapters'][3]['localization']['selene_04.line.019']
    assert 'hành lang' in line['vi'] and 'elf lớn tuổi' in line['vi']
    assert 'older elf' in line['en']

def test_each_normal_ending_exposes_only_its_selected_movie():
    from test_memory_adventure import play_to_final
    s=play_to_final()
    for option in engine.chapter(s)['choice']['options']:
        chosen=engine.advance(engine.advance(s,'choice',option['id']),'confirm_ending')
        output=view(chosen,{'name':'Selene'})
        expected=DATA['ending_videos'][chosen['pending_ending']]
        assert output['memory_video']['id']==expected
        assert expected in output['chapter_media']
        assert all(a in DATA['ending_videos'].values() or a=='ending_video_hidden' for a in output['chapter_media'] if a.startswith('ending_video_'))

def test_saved_timing_upgrade_is_idempotent_and_preserves_gameplay():
    from character_chat.adventure.dialogue_timing import upgrade
    cfg=seed();ch=cfg['chapters'][0]
    objects={o['id']:o for p in ch['scenes'] for o in p['hotspots']}
    trap=objects['selene_01_arrow_trap'];aftermath=objects['selene_01_fallen_arrow']
    warning=next(e for e in trap['events'] if e['type']=='dialogue')
    reaction=[e for e in trap['events'] if e['type']=='dialogue'][1]
    narration=next(e for e in trap['events'] if e['type']=='narration')
    trap['events']=[{**narration,'visual_event':'ARROW_TRAP'},warning]
    aftermath['events'].append(reaction)
    mechanics=deepcopy([{k:v for k,v in c.items() if k!='scenes'} for c in cfg['chapters']])
    upgraded=upgrade(cfg)
    assert [e['type'] for e in trap['events']]==['dialogue','visual_effect','narration','dialogue']
    assert [e['type'] for e in aftermath['events']]==['narration']
    assert [{k:v for k,v in c.items() if k!='scenes'} for c in cfg['chapters']]==mechanics
    assert upgrade(deepcopy(upgraded))==upgraded
