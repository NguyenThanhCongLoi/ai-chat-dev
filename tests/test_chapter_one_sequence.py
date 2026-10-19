"""Chapter 1 gate interaction is persisted; previews remain private."""
import json
import pytest
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from character_chat import moonfall_store as storage
from character_chat.models import AppSetting,UserAccount,Memory
from test_moonfall import moonfall
from test_worlds import world_client

def gate_ready():
    s=engine.advance(engine.fresh('alice','selene','',seed(),'en',.5),'intro_complete')
    ch=engine.chapter(s)
    for place in ch['scenes']:
        s=engine.advance(s,'go',place['id'])
        for obj in place['hotspots']:s=engine.advance(s,'inspect',obj['id'])
    puzzle=ch['puzzles'][0]
    s=engine.advance(s,'solve',json.dumps({'id':puzzle['id'],'answer':puzzle['solution']}))
    return engine.advance(s,'choice',ch['choice']['options'][1]['id'])

def test_gate_is_the_only_active_target_and_cannot_open_early():
    s=engine.advance(engine.fresh('alice','selene','',seed(),'en',.5),'intro_complete')
    with pytest.raises(ValueError):engine.advance(s,'open_gate')
    s=gate_ready();out=view(s,{'id':'selene','name':'Selene'})
    assert s['phase']=='gate_ready' and s['location']=='ancient_gate'
    assert [o['id'] for o in out['objects'] if o['interactive']]==['selene_01_old_gate']
    assert not out['puzzles'] and not out['choices']
    assert not any(e['visual_event']=='LOCATION_ENTER' for e in out['events'])
    for action,value in [('go','outer_ruins'),('inspect','selene_01_collapsed_path')]:
        with pytest.raises(ValueError):engine.advance(s,action,value)
    assert 'M01' not in s['core_memories']
    assert out['chapter_one_flow']['scroll_body']

def test_gate_and_memory_skip_failure_resume_have_the_same_outcome():
    s=gate_ready();opened=engine.advance(s,'open_gate')
    assert opened['phase']=='gate_cinematic' and opened['gate_opened']
    resumed=json.loads(json.dumps(opened))
    with pytest.raises(ValueError):engine.advance(resumed,'open_gate')
    memory=engine.advance(resumed,'finish_gate_cinematic')
    assert memory['phase']=='memory' and not memory['completed']
    done=engine.advance(memory,'finish_memory_cinematic')
    assert done['completed'] and done['core_memories']==['M01']
    assert done['memories'][0]['id']=='M01'
    with pytest.raises(ValueError):engine.advance(done,'finish_gate_cinematic')
    for language in ['vi','en','ja','zh','ko','my','km']:
        done['content_language']=language
        output=view(done,{'id':'selene','name':'Selene'})
        assert output['chapter_one_flow']['scroll_title'] and output['chapter_one_flow']['scroll_body']

def test_admin_default_preview_resumes_without_touching_real_save(moonfall,monkeypatch):
    client,factory,user=moonfall
    monkeypatch.setenv('WORLD_ADVENTURE_ENABLED','true')
    real=gate_ready()
    with factory() as db:
        db.add(AppSetting(key=storage.run_key('alice',real['id']),value=json.dumps(real,ensure_ascii=False)))
        db.add(UserAccount(user_id='alice',username='preview-admin',display_name='Admin',password_hash='fixture',is_admin=1,status='active'))
        db.commit()
    initial=client.post('/v1/moonfall',json={'character_id':'selene','chapter_id':'selene_08'})
    assert initial.status_code==200,initial.text
    preview=initial.json()
    assert preview['admin_preview'] and preview['id'].startswith('debug_')
    assert preview['chapter_id']=='selene_08' and len(preview['preview_chapters'])==8
    resumed=client.post('/v1/moonfall',json={'character_id':'selene'})
    assert resumed.status_code==200 and resumed.json()['id']==preview['id']
    assert all(ch['available'] for ch in client.get('/v1/moonfall/chapters?character_id=selene').json()['chapters'])
    assert client.post('/v1/moonfall/'+preview['id']+'/return-to-chat',json={'sync_memory':True}).status_code==409
    with factory() as db:
        assert json.loads(db.get(AppSetting,storage.run_key('alice',real['id'])).value)==real
        assert not db.query(Memory).filter_by(type='world_shared').count()
    user['id']='bob'
    assert client.get('/v1/moonfall/'+preview['id']).status_code==404
