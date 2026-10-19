"""Narrative progression, unchanged rewards, and media sequencing."""
from copy import deepcopy
import pytest
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from test_memory_adventure import play_to_final


def test_expanded_actions_are_required_but_do_not_grant_route_rewards():
    cfg=seed()
    for ch in cfg['chapters']:
        assert len(ch['scenes'])==4
        s=engine.fresh('a','selene','',cfg,'vi',.5)
        s['admin_preview']=True
        s=engine.select_chapter(s,ch['id'])
        if s['phase']=='intro':s=engine.advance(s,'intro_complete')
        for place in ch['scenes']:
            s=engine.advance(s,'go',place['id'])
            for obj in place['hotspots']:
                if '.expanded.' not in next(e.get('text_key','') for e in obj['events'] if e.get('text_key')):continue
                assert obj['id'] in ch['required_inspections']
                assert all(obj['id'] in p['requires_inspections'] for p in ch['puzzles'])
                before={k:deepcopy(s[k]) for k in ('stats','flags','inventory','echoes','lore_fragments','core_memories')}
                s=engine.advance(s,'inspect',obj['id'])
                for k,v in before.items():assert s[k]==v
                projected=view(s,{'id':'selene','name':'Selene'})
                assert projected['assets']
                # Missing new art uses a normal, operable marker.
                assert next(o for o in projected['objects'] if o['id']==obj['id'])['mode'] in ('marker','embedded')


@pytest.mark.parametrize('ending',range(4))
def test_video_skip_matches_stepwise_outcome_and_m08_starts_on_rooftop(ending):
    s=play_to_final()
    s['ending_offer_at']=0
    ident='remember_without_becoming' if ending==3 else engine.chapter(s)['choice']['options'][ending]['id']
    s=engine.advance(engine.advance(s,'choice',ident),'confirm_ending')
    if ending==3:
        assert s['events'][-1]['text']['en'].startswith('On a Moonbrook rooftop')
        assert view(s,{'id':'selene','name':'Selene'})['memory_video']['id']=='memory_video_08'
    skipped=engine.advance(s,'finish_memory_cinematic')
    while s['phase']=='memory':s=engine.advance(s,'continue')
    for k in ('stats','inventory','flags','core_memories','ending','memories','completed_chapters'):
        assert s[k]==skipped[k]
    if ending==3:
        last_beat=skipped['events'][-1]['beat_id']
        spoken=[e['text']['en'] for e in skipped['events'] if e.get('beat_id')==last_beat and e['type']=='CHARACTER_SPEECH' and e.get('presentation')=='main']
        assert len(spoken)==1 and 'Are you still coming with me?' in spoken[0]
