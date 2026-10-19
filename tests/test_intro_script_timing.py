from copy import deepcopy
import json
from pathlib import Path
import pytest
from character_chat.api.hub_narration import validate
from character_chat.adventure.authored_audio import script_events
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from test_moonfall import moonfall
from test_worlds import world_client

def authored():return json.loads(Path('character_chat/story_data/world_hub_narration.json').read_text(encoding='utf8'))

def test_script_fits_the_trimmed_clip_and_preserves_four_silences():
    cfg=validate(authored())
    assert len(cfg['silent_windows'])==4 and cfg['cues'][-1]['end']<93.708
    welcome=next(c for c in cfg['cues'] if c['id']=='intro_welcome')
    before=next(w for w in cfg['silent_windows'] if w['id']=='before_welcome')
    assert before['end']==welcome['start'] and 2<=before['end']-before['start']<=3
    assert 'Chào mừng đến với World Mode' in welcome['text']['vi']

@pytest.mark.parametrize('bad',['overlap','past_end','nan','silence_overlap','silence_duration'])
def test_cms_rejects_narration_that_breaks_the_picture_or_music_pause(bad):
    cfg=authored()
    if bad=='overlap':cfg['cues'][0]['end']=9
    elif bad=='past_end':cfg['cues'][-1]['end']=95
    elif bad=='nan':cfg['silent_windows'][0]['start']=float('nan')
    elif bad=='silence_overlap':cfg['silent_windows'][1]['start']=18
    else:cfg['silent_windows'][-1]['end']=100
    with pytest.raises(ValueError):validate(cfg)

def test_private_cms_plan_prepares_m08_without_exposing_it_to_a_player():
    cfg=seed();s=engine.fresh('a','selene','',cfg,'vi',0);s['admin_preview']=True
    s=engine.select_chapter(s,'selene_08');before=deepcopy(s)
    private=script_events(s,'vi',include_all_endings=True)
    public=script_events(s,'vi')
    assert s==before and len(private)>len(public)
    assert any('World' not in e['text']['vi'] and 'mái nhà Moonbrook' in e['text']['vi'] for e in private.values())
    assert not any('mái nhà Moonbrook' in e['text']['vi'] for e in public.values())

def test_admin_audio_status_never_generates_and_requires_auth(moonfall,monkeypatch):
    from character_chat import main
    from test_moonfall import mock_audio
    client,_,_=moonfall;calls=mock_audio(monkeypatch)
    got=client.get('/v1/admin/moonfall/hub-narration/status')
    assert got.status_code==200 and not got.json()['ready'] and calls==[]
    assert len(got.json()['results'])==20
    assert client.get('/v1/admin/moonfall/hub-narration/audio/intro_door?language=vi').status_code==409
    assert calls==[]
    main.app.dependency_overrides.pop(main.docs_auth,None)
    assert client.get('/v1/admin/moonfall/hub-narration/status').status_code==401

def test_shipped_legacy_intro_follows_new_clip_without_overwriting_custom_cms(moonfall):
    from character_chat.api.hub_narration import KEY,config
    from character_chat.models import AppSetting
    _,factory,_=moonfall
    old=json.loads(Path('character_chat/story_data/world_hub_narration_legacy.json').read_text(encoding='utf8'))
    old.update(revision=10,music_gain=.3,duck_gain=.1,voice_gain=.8,enabled=False)
    with factory() as db:
        db.add(AppSetting(key=KEY,value=json.dumps(old,ensure_ascii=False)));db.commit()
        current=config(db)
        assert len(current['cues'])==10 and current['revision']==11
        assert current['music_gain']==.3 and not current['enabled']
        # This effective-content upgrade never mutates the DB during a read.
        assert json.loads(db.get(AppSetting,KEY).value)==old
        old['cues'][0]['text']['vi']='Lời intro riêng do người quản trị biên soạn.'
        db.get(AppSetting,KEY).value=json.dumps(old,ensure_ascii=False);db.commit()
        assert config(db)==old
