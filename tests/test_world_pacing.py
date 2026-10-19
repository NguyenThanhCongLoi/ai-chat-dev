"""Real chapter gates, adaptive chat credit, shuffled UI and safe presentation."""
from copy import deepcopy
import json
from datetime import datetime,timezone,timedelta
import pytest
from test_worlds import world_client
from test_moonfall import moonfall
from test_memory_adventure import play_to_final
from character_chat import main,moonfall_store as storage
from character_chat.models import AppSetting,Room,RoomMember,Message,Memory
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from character_chat.adventure.pacing import stamp,status


def first_complete():
    s=engine.advance(engine.fresh('alice','selene','',seed(),'en',.6),'intro_complete')
    ch=s['config']['chapters'][0]
    for place in ch['scenes']:
        s=engine.advance(s,'go',place['id'])
        for obj in place['hotspots']:s=engine.advance(s,'inspect',obj['id'])
    puzzle=ch['puzzles'][0]
    s=engine.advance(s,'solve',json.dumps({'id':puzzle['id'],'answer':puzzle['solution']}))
    s=engine.advance(s,'choice',ch['choice']['options'][0]['id'])
    if s['phase']=='gate_ready':s=engine.advance(s,'open_gate');s=engine.advance(s,'finish_gate_cinematic')
    return engine.advance(s,'finish_memory_cinematic')


def normal_turns(db,texts,room='between',owner='alice',complete=True):
    if not db.get(Room,room):
        db.add(Room(id=room,user_id=owner,name='Normal Selene chat'))
        db.add(RoomMember(id=room+'-s',room_id=room,character_id='selene'))
    for i,text in enumerate(texts):
        ident=room+'-'+str(i)
        db.add(Message(id=ident,room_id=room,sender_type='user',text=text))
        db.add(Message(id=ident+'-reply',room_id=room,sender_type='character',character_id='selene',reply_to_message_id=ident,text='A completed reply.',finish_status='complete' if complete else 'partial'))
    db.commit()


def test_next_chapter_cannot_be_opened_without_new_normal_chat(moonfall,monkeypatch):
    client,factory,user=moonfall
    monkeypatch.setenv('WORLD_ADVENTURE_ENABLED','true')
    s=first_complete()
    with factory() as db:
        stamp(db,{'completed_chapters':[]},s)
        db.add(AppSetting(key=storage.run_key('alice',s['id']),value=json.dumps(s,ensure_ascii=False)))
        db.commit()
    got=client.get('/v1/moonfall/'+s['id']).json()
    assert got['completed'] and got['chapter_outro'] and not got['has_next']
    chapters=client.get('/v1/moonfall/chapters?character_id=selene').json()['chapters']
    assert not chapters[1]['available']
    assert client.post('/v1/moonfall',json={'character_id':'selene','chapter_id':'selene_02'}).status_code==409
    assert client.post('/v1/moonfall/'+s['id']+'/act',json={'revision':got['revision'],'request_id':'skip','action':'chapter','value':'selene_02'}).status_code==409
    with factory() as db:
        normal_turns(db,['hello']*6+['Tell me about the old pendant and the promise we discussed.'],complete=False)
        assert not status(db,'alice',s,'selene_02',seed())['eligible']
        normal_turns(db,[
            'The pendant seems important to you, and I want to understand why.',
            'Keeping a promise matters when we leave each other room to choose freely.',
            'I trust your judgement, even when we see the same event differently.',
            'If you need a quiet afternoon, we could talk about something else.'
        ],room='relevant')
        check=status(db,'alice',s,'selene_02',seed())
        assert check['eligible'] and check['turns']<check['required'],check
        assert not status(db,'bob',s,'selene_02',seed())['eligible']
    response=client.post('/v1/moonfall',json={'character_id':'selene','chapter_id':'selene_02'})
    assert response.status_code==200,response.text


@pytest.mark.parametrize('ending',['remember_me','let_me_forget','new_keeper','between_memory_and_moonlight'])
def test_all_endings_expose_a_working_return_to_chat(moonfall,monkeypatch,ending):
    client,factory,_=moonfall
    monkeypatch.setenv('WORLD_ADVENTURE_ENABLED','true')
    monkeypatch.setattr(main,'direct_completion',lambda *a,**k:'I remember the journey we shared.')
    s=play_to_final()
    if ending=='between_memory_and_moonlight':s['ending_offer_at']=0;choice='remember_without_becoming'
    else:choice=s['config']['chapters'][7]['choice']['options'][['remember_me','let_me_forget','new_keeper'].index(ending)]['id']
    s=engine.advance(s,'choice',choice);s=engine.advance(s,'confirm_ending')
    if s['phase']=='memory':s=engine.advance(s,'finish_memory_cinematic')
    with factory() as db:
        db.add(AppSetting(key=storage.run_key('alice',s['id']),value=json.dumps(s,ensure_ascii=False)));db.commit()
    projected=client.get('/v1/moonfall/'+s['id']).json()
    assert projected['phase']=='arc_complete' and projected['chapter_outro']
    result=client.post('/v1/moonfall/'+s['id']+'/return-to-chat',json={'sync_memory':True})
    assert result.status_code==200,result.text
    assert '/role-play-ai?' in result.json()['url']


def test_choices_are_stable_but_change_slots_and_do_not_leak_solutions():
    s=engine.fresh('alice','selene','',seed(),'en',.5)
    from character_chat.adventure.story_enrichment import shuffled
    rows=[{'id':'a'},{'id':'b'},{'id':'c'}]
    positions=[]
    for chapter in s['config']['chapters']:
        s['chapter_id']=chapter['id']
        a=shuffled(rows,s,'choices');assert a==shuffled(rows,s,'choices')
        positions.append([r['id'] for r in a].index('a'))
    assert all(a!=b for a,b in zip(positions,positions[1:]))


def test_echo_identity_waits_for_the_deduction_and_cinematic_assets_are_resolved():
    s=engine.fresh('alice','selene','',seed(),'en',.5);s['admin_preview']=True
    s=engine.select_chapter(s,'selene_03')
    ch=engine.chapter(s)
    for place in ch['scenes']:
        s=engine.advance(s,'go',place['id'])
        for obj in place['hotspots']:s=engine.advance(s,'inspect',obj['id'])
    assert not any(e.get('speaker')=='young_selene' for e in s['events'])
    puzzle=ch['puzzles'][0]
    s=engine.advance(s,'go',puzzle['scene'])
    s=engine.advance(s,'solve',json.dumps({'id':puzzle['id'],'answer':puzzle['solution']}))
    output=view(s,{'id':'selene','name':'Selene'})
    assert output['supporting_cast'][0]['id']=='young_selene'
    assert all(e['voice_role'] is None for e in output['events'] if e['speaker']=='young_selene')
    assert 'seal_activation' in output['assets']
    assert output['visual_events']['MAGIC_SEAL_ACTIVATE']['cinematic']=='seal_activation'
    assert len(output['story_stages'])==4


def test_world_cms_can_edit_chapters_and_story_beats_without_chat_moderation(moonfall,monkeypatch):
    client,_,_=moonfall
    monkeypatch.setenv('WORLD_ADVENTURE_ENABLED','true')
    calls=[]
    def reject(*args,**kwargs):
        calls.append(args)
        raise main.HTTPException(422,'Content requires moderation. Please revise.')
    monkeypatch.setattr(main,'ensure_safe_content',reject)
    cfg=client.get('/v1/admin/moonfall').json()['config']
    cfg['chapters'][0]['title']['en']='An editor-authored chapter'
    cfg['adventure']['story_beats']['beats']['selene_01_collapsed_path'][0]['text']['en']='The old ritual left a mark on these ruins.'
    response=client.put('/v1/admin/moonfall',json=cfg)
    assert response.status_code==200,response.text
    assert response.json()['chapters'][0]['title']['en']=='An editor-authored chapter'
    assert not calls
    # The editorial exception is behind the existing CMS authentication dependency.
    def deny():raise main.HTTPException(401,'CMS authentication required')
    main.app.dependency_overrides[main.docs_auth]=deny
    assert client.put('/v1/admin/moonfall',json=response.json()).status_code==401

def test_completed_chapter_reentry_allows_staying_chat_and_memory_replay(moonfall,monkeypatch):
    client,factory,_=moonfall
    monkeypatch.setenv('WORLD_ADVENTURE_ENABLED','true')
    monkeypatch.setattr(main,'direct_completion',lambda *a,**k:'We can stay here and talk about what we found.')
    s=first_complete()
    s['config']['model_id']='mf-chat'
    with factory() as db:
        stamp(db,{'completed_chapters':[]},s)
        db.add(AppSetting(key=storage.run_key('alice',s['id']),value=json.dumps(s,ensure_ascii=False)))
        # Initial entry conditions cannot lock an already opened chapter again.
        cfg=storage.config(db);cfg['entry_gate']['min_meaningful_turns']=100
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg,ensure_ascii=False)
        db.commit()
    response=client.post('/v1/moonfall',json={'character_id':'selene','chapter_id':'selene_01'})
    assert response.status_code==200,response.text
    got=response.json()
    assert got['reviewing'] and got['completed'] and got['phase']=='explore'
    assert got['can_replay_memory']
    def act(action,value=''):
        nonlocal got
        r=client.post('/v1/moonfall/'+got['id']+'/act',json={'action':action,'value':value,'revision':got['revision'],'request_id':'review-'+str(got['revision'])})
        assert r.status_code==200,r.text
        got=r.json()
        return got
    act('go','outer_ruins')
    assert got['location']=='outer_ruins'
    act('say','Can we spend a little more time here before heading home?')
    assert got['events'][-1]['text']=='We can stay here and talk about what we found.'
    act('review_memory')
    assert got['phase']=='memory'
    key=got['memory_video']['key']
    act('finish_memory_cinematic')
    assert got['reviewing'] and got['phase']=='explore'
    act('review_memory')
    assert got['memory_video']['key']!=key
    act('finish_memory_cinematic')
    with factory() as db:
        saved=json.loads(db.get(AppSetting,storage.run_key('alice',s['id'])).value)
    for field in ['memories','stats','inventory','flags','choices','completed_chapters','completion_marks']:
        assert saved[field]==s[field],field

def test_all_completed_chapters_can_be_revisited_without_changing_the_ending():
    s=play_to_final()
    choice=s['config']['chapters'][7]['choice']['options'][0]['id']
    s=engine.advance(s,'choice',choice);s=engine.advance(s,'confirm_ending')
    if s['phase']=='memory':s=engine.advance(s,'finish_memory_cinematic')
    canonical={k:deepcopy(s[k]) for k in ['ending','memories','inventory','stats','choices','flags','completed_chapters']}
    for ch in s['config']['chapters']:
        s=engine.select_chapter(s,ch['id'])
        assert s['reviewing'] and s['phase']=='explore'
        for place in ch['scenes']:s=engine.advance(s,'go',place['id'])
        for k,v in canonical.items():assert s[k]==v,k

def test_an_opened_unfinished_chapter_stays_accessible_when_browsing_old_chapters():
    s=first_complete()
    s=engine.select_chapter(s,'selene_02')
    s=engine.select_chapter(s,'selene_01')
    assert s['reviewing'] and 'selene_02' in s['chapter_bookmarks']
    assert status(None,'alice',s,'selene_02',s['config'])['eligible']
    assert not status(None,'bob',s,'selene_02',s['config'])['eligible']
    resumed=engine.select_chapter(s,'selene_02')
    assert not resumed['reviewing'] and resumed['phase']=='explore'
