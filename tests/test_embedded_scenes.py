"""Painted background hit regions and clean-plate lifecycle."""
from copy import deepcopy
from pathlib import Path
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from character_chat.adventure.embedded_scenes import DATA
from character_chat.adventure.props import manifest_assets

def state(chapter):
    s=engine.fresh('alice','selene','',seed(),'en',.5)
    s['admin_preview']=True
    s=engine.select_chapter(s,chapter)
    return engine.advance(s,'intro_complete') if s['phase']=='intro' else s

def test_every_painted_scene_and_region_has_a_valid_asset():
    cfg=seed();assets=manifest_assets(cfg);ids=set()
    assert set(DATA['scenes'])=={c['id']+':'+p['id'] for c in cfg['chapters'] for p in c['scenes']}
    assert len(DATA['hotspots'])>=60
    for ch in cfg['chapters']:
        s=state(ch['id'])
        s['inventory']=[i['id'] for i in cfg['adventure']['items']]
        for place in ch['scenes']:
            s=engine.advance(s,'go',place['id'])
            out=view(s,{'id':'selene','name':'Selene'})
            art=out['embedded_scene']
            if ch['id']+':'+place['id'] not in DATA['scenes']:
                assert art is None
                assert all(o['mode']=='marker' for o in out['objects'])
                continue
            assert art['background'] in out['assets']
            assert art['width']/art['height']>=1.5
            for o in out['objects']:
                ids.add(o['id'])
                if o['mode']!='embedded':
                    assert o['mode']=='marker' or o['asset'] in out['assets']
                    continue
                assert not o['asset']
                assert len(o['polygon'])>=3
                assert all(0<=v<=1 for p in o['polygon'] for v in p)
                assert not o['removed']
            for patch in art['cleanups']:
                assert not patch['visible'] and patch['asset'] in out['assets']
    assert ids<=set(DATA['hotspots'])
    for a in assets.values():
        if a['path'].startswith(('backgrounds/interactive/','backgrounds/echoes_bg_16x9/')):
            assert (Path('image/worlds/selene/moonfall')/a['path']).is_file()

def test_replacement_collection_keeps_painted_art_without_an_invalid_clean_plate():
    s=state('selene_02');s=engine.advance(s,'inspect','selene_02_pendant')
    out=view(deepcopy(s),{'id':'selene','name':'Selene'})
    obj=next(o for o in out['objects'] if o['id']=='selene_02_pendant')
    assert obj['discovered'] and not obj['interactive'] and not obj['removed']
    assert out['embedded_scene']['cleanups']==[]
    assert 'silver_pendant' in s['inventory']
    s=engine.advance(s,'go','moonflower_garden')
    for ident in ['selene_02_stone_bench','selene_02_erased_names','selene_02_follow_silhouette','selene_02_echo_trace']:s=engine.advance(s,'inspect',ident)
    assert any(o['id']=='selene_02_moonflower' and o['mode']=='floor' for o in view(s,{'id':'selene','name':'Selene'})['objects'])


def test_document_is_kept_until_all_required_details_have_been_read():
    s=state('selene_05')
    for ident in ['selene_05_ink','selene_05_seal']:
        s=engine.advance(s,'inspect',ident)
        assert not any(p['visible'] for p in view(s,{'id':'selene','name':'Selene'})['embedded_scene']['cleanups'])
    s=engine.advance(s,'inspect','selene_05_timestamp')
    out=view(s,{'id':'selene','name':'Selene'})
    assert all(o['discovered'] and not o['interactive'] for o in out['objects'])
    # A clean plate from the retired painting must never cover the new art.
    assert out['embedded_scene']['cleanups']==[]
