"""Replay attempts are sequential and cannot farm or reroll endings."""
import json
import pytest
from character_chat.adventure import engine
from character_chat.adventure.conditions import allows
from character_chat.adventure.projection import view
from test_memory_adventure import play_to_final, investigate
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat import moonfall_store as storage
from character_chat.models import AppSetting

def finish(s,index=0):
    options=s['config']['chapters'][7]['choice']['options']
    s=engine.advance(s,'choice',options[index]['id'])
    s=engine.advance(s,'confirm_ending')
    if s['phase']=='memory':s=engine.advance(s,'finish_memory_cinematic')
    return s

def play_replay(s,stop=8):
    if s['phase']=='intro':s=engine.advance(s,'intro_complete')
    for n,ch in enumerate(s['config']['chapters'][:stop]):
        if s['chapter_id']!=ch['id']:s=engine.select_chapter(s,ch['id'])
        s=investigate(s)
        for puzzle in ch['puzzles']:
            s=engine.advance(s,'go',puzzle['scene'])
            s=engine.advance(s,'solve',json.dumps({'id':puzzle['id'],'answer':puzzle['solution']}))
        if n==7:return s
        s=engine.advance(s,'choice',ch['choice']['options'][2]['id'])
        if s['phase']=='gate_ready':s=engine.advance(s,'open_gate');s=engine.advance(s,'finish_gate_cinematic')
        s=engine.advance(s,'finish_memory_cinematic')
    return s

def test_replay_requires_the_entire_route_for_a_new_ending():
    old=finish(play_to_final(),0)
    assert set(old['ending_collection'])=={'remember_me'}
    new=engine.advance(old,'restart')
    assert new['id']==old['id'] and new['attempt_id']!=old['id']
    assert new['attempt_number']==2 and not new['completed_chapters']
    assert new['stats']==dict(trust=0,truth=0,understanding=0,sacrifice=0)
    assert not new['inventory'] and not new['flags']
    with pytest.raises(ValueError):engine.select_chapter(new,'selene_08')
    partial=play_replay(new,3)
    resumed=json.loads(json.dumps(partial))
    with pytest.raises(ValueError):engine.select_chapter(resumed,'selene_08')
    with pytest.raises(ValueError):engine.advance(resumed,'restart')
    assert set(resumed['ending_collection'])=={'remember_me'}
    another=finish(play_replay(engine.advance(old,'restart')),1)
    assert another['ending']=='let_me_forget' and another['ending_is_new']
    assert len(another['ending_collection'])==2
    review=engine.select_chapter(another,'selene_08')
    with pytest.raises(ValueError):engine.advance(review,'choice',review['config']['chapters'][7]['choice']['options'][2]['id'])
    assert review['ending']=='let_me_forget'

def test_same_ending_is_not_revealed_or_rewarded_twice():
    old=finish(play_to_final(),0)
    repeated=finish(play_replay(engine.advance(old,'restart')),0)
    assert repeated['ending']=='remember_me' and repeated['ending_is_new'] is False
    assert len(repeated['ending_collection'])==1 and len(repeated['memories'])==7
    assert not any(e.get('visual_event')=='ARC_COMPLETE' for e in repeated['events'])
    review=engine.select_chapter(repeated,'selene_08')
    assert not view(review,{'id':'selene','name':'Selene'})['can_replay_memory']
    with pytest.raises(ValueError):engine.advance(review,'review_memory')

def test_incomplete_route_cannot_forge_a_final_reveal():
    s=play_to_final();s['choices']=s['choices'][1:]
    s=engine.advance(s,'choice',s['config']['chapters'][7]['choice']['options'][0]['id'])
    with pytest.raises(ValueError):engine.advance(s,'confirm_ending')

def test_http_restart_is_owner_scoped_idempotent_and_resumes_current_attempt(moonfall,monkeypatch):
    client,factory,user=moonfall
    monkeypatch.setenv('WORLD_ADVENTURE_ENABLED','true')
    s=finish(play_to_final())
    with factory() as db:
        db.add(AppSetting(key=storage.run_key('alice',s['id']),value=json.dumps(s,ensure_ascii=False)))
        db.commit()
    url='/v1/moonfall/'+s['id']
    before=client.get(url).json()
    user['id']='bob'
    assert client.post(url+'/act',json={'revision':before['revision'],'request_id':'restart-1','action':'restart'}).status_code==404
    user['id']='alice'
    payload={'revision':before['revision'],'request_id':'restart-1','action':'restart'}
    r=client.post(url+'/act',json=payload)
    assert r.status_code==200,r.text
    new=r.json()
    assert new['attempt_number']==2 and new['chapter_id']=='selene_01'
    assert len([e for e in new['ending_collection'] if e['discovered']])==1
    duplicate=client.post(url+'/act',json=payload)
    assert duplicate.status_code==200 and duplicate.json()['attempt_number']==2
    resumed=client.post('/v1/moonfall',json={'character_id':'selene'})
    assert resumed.status_code==200 and resumed.json()['attempt_number']==2
    assert client.post('/v1/moonfall',json={'character_id':'selene','chapter_id':'selene_08'}).status_code==409
    assert client.post(url+'/act',json={'revision':new['revision'],'request_id':'restart-2','action':'restart'}).status_code==422
    with factory() as db:
        saved=json.loads(db.get(AppSetting,storage.run_key('alice',s['id'])).value)
    assert saved['finished_attempts'][0]['ending']=='remember_me'
    assert saved['ending'] is None and not saved['completed_chapters']
