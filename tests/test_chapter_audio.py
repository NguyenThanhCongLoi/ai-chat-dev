"""Persistent fixed speech, ownership, invalidation and no future ending disclosure."""
import json
from copy import deepcopy
from test_worlds import world_client
from test_moonfall import moonfall,mock_audio
from character_chat import moonfall_store as storage
from character_chat.models import AppSetting
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.authored_audio import script_events,audio_key

def test_revisit_narration_does_not_expand_required_preload_at_the_gate():
    from test_chapter_one_sequence import gate_ready
    state=gate_ready()
    baseline=script_events(state,'vi')
    label={'id':'revisit-label','type':'NARRATION','speaker':'narrator','source':'authored','chapter_id':'selene_01','text':{'vi':'Dư âm vòng phép','en':'After the silver ward'}}
    state['events'].append(label)
    state=engine.advance(engine.advance(state,'open_gate'),'finish_gate_cinematic')
    assert state['phase']=='memory'
    assert script_events(state,'vi')==baseline
    assert audio_key(label,'vi') not in baseline

def stored(factory):
    s=engine.fresh("alice","selene","",seed(),"en",.6)
    with factory() as db:
        db.add(AppSetting(key=storage.run_key("alice",s["id"]),value=json.dumps(s)));db.commit()
    return s

def prepare(client,factory,monkeypatch,chapter='selene_01'):
    from character_chat import main
    from character_chat.schemas import CharacterSpec
    monkeypatch.setattr(main,'Session',factory)
    monkeypatch.setattr(main,'effective_presets',lambda db:[CharacterSpec(id='selene',name='Selene Moonbrook',tts_voice_en='selene-en',tts_voice_vi='selene-vi')])
    response=client.post('/v1/admin/moonfall/chapter-audio/prepare',json={'chapters':[chapter]})
    assert response.status_code==200,response.text

def test_fixed_audio_is_cached_and_owner_scoped(moonfall,monkeypatch):
    client,factory,user=moonfall;monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    requests=mock_audio(monkeypatch);s=stored(factory)
    response=client.get("/v1/moonfall/"+s["id"]+"/chapter-audio")
    assert response.status_code==200,response.text
    catalog=response.json();assert catalog["enabled"] and len(catalog["clips"])>10
    assert requests==[]
    assert all(set(c)=={"id","ready","version"} for c in catalog["clips"])
    key=catalog["clips"][0]["id"];endpoint="/v1/moonfall/"+s["id"]+"/chapter-audio/"+key
    assert client.post(endpoint).status_code==409
    assert requests==[]
    prepare(client,factory,monkeypatch)
    prepared_count=len(requests)
    first=client.post(endpoint);assert first.status_code==200,first.text
    assert len(requests)==prepared_count
    again=client.post(endpoint);assert again.status_code==200 and again.content==first.content
    assert len(requests)==prepared_count
    fresh=client.get("/v1/moonfall/"+s["id"]+"/chapter-audio").json()
    assert fresh["version"]==catalog["version"]
    assert next(c for c in fresh["clips"] if c["id"]==key)["ready"]
    assert client.post("/v1/moonfall/"+s["id"]+"/chapter-audio/"+"0"*64).status_code==404
    user["id"]="bob"
    assert client.post(endpoint).status_code==404
    assert len(requests)==prepared_count

def test_changing_narrator_voice_changes_audio_cache_key(moonfall,monkeypatch):
    client,factory,_=moonfall;monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    requests=mock_audio(monkeypatch);s=stored(factory)
    event=next(e for e in script_events(s,"en").values() if e["type"]=="NARRATION")
    key=audio_key(event,"en");endpoint="/v1/moonfall/"+s["id"]+"/chapter-audio/"+key
    prepare(client,factory,monkeypatch)
    assert client.post(endpoint).status_code==200
    prepared_count=len(requests)
    with factory() as db:
        cfg=storage.config(db);cfg["narrator_voices"]["en"]="new-narrator"
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg);db.commit()
    assert client.post(endpoint).status_code==409
    assert len(requests)==prepared_count
    prepare(client,factory,monkeypatch)
    assert client.post(endpoint).status_code==200
    assert len(requests)>prepared_count and requests[-1]["voice"]=="new-narrator"

def test_planner_does_not_reveal_hidden_ending_or_mutate_story():
    s=engine.fresh("alice","selene","",seed(),"en",.6);s["admin_preview"]=True
    s=engine.select_chapter(s,"selene_08");old=deepcopy(s)
    plan=script_events(s,"en")
    assert s==old
    hidden=s["config"]["adventure"]["endings"][3]
    for e in hidden["events"]:
        if e["type"] in ("dialogue","narration"):
            assert audio_key({"type":"CHARACTER_SPEECH" if e["type"]=="dialogue" else "NARRATION","speaker":e.get("speaker"),"text":e.get("text",{})},"en") not in plan


def test_supporting_voice_requires_cms_assignment(moonfall,monkeypatch):
    client,factory,_=moonfall;monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    requests=mock_audio(monkeypatch)
    s=engine.fresh("alice","selene","",seed(),"en",.6)
    s["chapter_id"]="selene_03";s["location"]=s["config"]["chapters"][2]["scenes"][0]["id"]
    configured=deepcopy(s);configured["config"]["adventure"]["speaker_voices"]={"young_selene":{"en":"young-en"},"elarion":{"en":"elarion-en"}}
    supported={k:e for k,e in script_events(configured,"en").items() if e["speaker"] not in ("selene","narrator")}
    assert supported
    key,event=next(iter(supported.items()))
    with factory() as db:
        db.add(AppSetting(key=storage.run_key("alice",s["id"]),value=json.dumps(s)))
        cfg=storage.config(db);cfg["adventure"]["speaker_voices"]=configured["config"]["adventure"]["speaker_voices"]
        db.get(AppSetting,storage.CONFIG_KEY).value=json.dumps(cfg);db.commit()
    prepare(client,factory,monkeypatch,'selene_03')
    response=client.post("/v1/moonfall/"+s["id"]+"/chapter-audio/"+key)
    assert response.status_code==200,response.text
    assert any(r['voice']==configured["config"]["adventure"]["speaker_voices"][event["speaker"]]["en"] for r in requests)


def test_cms_prepares_both_languages_without_creating_a_player_run(moonfall,monkeypatch):
    from character_chat import main
    from character_chat.schemas import CharacterSpec
    client,factory,_=moonfall;monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    monkeypatch.setattr(main,"Session",factory)
    card=CharacterSpec(id="selene",name="Selene Moonbrook",tts_voice_en="selene-en",tts_voice_vi="selene-vi")
    monkeypatch.setattr(main,"effective_presets",lambda db:[card])
    requests=mock_audio(monkeypatch)
    result=client.post("/v1/admin/moonfall/chapter-audio/prepare",json={"chapters":["selene_01"]})
    assert result.status_code==200,result.text
    ready=client.get("/v1/admin/moonfall/chapter-audio?chapter_id=selene_01").json()
    for language in ("vi","en"):
        row=ready["languages"][language]
        assert row["enabled"] and row["ready"]==row["total"] and row["total"]>10,ready
    count=len(requests)
    assert client.post("/v1/admin/moonfall/chapter-audio/prepare",json={"chapters":["selene_01"]}).status_code==200
    assert len(requests)==count
    with factory() as db:
        assert not db.query(AppSetting).filter(AppSetting.key.like("moonfall_run:%")).count()

def test_cms_can_retry_one_missing_line_without_creating_a_run(moonfall,monkeypatch):
    from character_chat import main
    from character_chat.schemas import CharacterSpec
    client,factory,_=moonfall;monkeypatch.setenv('WORLD_ADVENTURE_ENABLED','true')
    monkeypatch.setattr(main,'effective_presets',lambda db:[CharacterSpec(id='selene',name='Selene Moonbrook',tts_voice_en='selene-en',tts_voice_vi='selene-vi')])
    calls=mock_audio(monkeypatch)
    report=client.get('/v1/admin/moonfall/chapter-audio?chapter_id=selene_01').json()
    line=report['languages']['vi']['missing'][0]
    body=dict(chapter_id='selene_01',language='vi',key=line['id'])
    response=client.post('/v1/admin/moonfall/chapter-audio/prepare-line',json=body)
    assert response.status_code==200,response.text
    assert len(calls)==1
    assert client.post('/v1/admin/moonfall/chapter-audio/prepare-line',json=body).status_code==200
    assert len(calls)==1
    assert client.post('/v1/admin/moonfall/chapter-audio/prepare-line',json={**body,'key':[]}).status_code==422
    with factory() as db:
        assert not db.query(AppSetting).filter(AppSetting.key.like('moonfall_run:%')).count()


def test_server_startup_prepares_missing_fixed_speech_without_creating_runs(moonfall,monkeypatch):
    import asyncio
    from character_chat import main
    from character_chat.schemas import CharacterSpec
    _,factory,_=moonfall
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    monkeypatch.setenv("WORLD_CHAPTER_PREPARE_ON_STARTUP","true")
    monkeypatch.setattr(main,"Session",factory)
    monkeypatch.setattr(main,"effective_presets",lambda db:[CharacterSpec(id="selene",name="Selene Moonbrook",tts_voice_en="selene-en",tts_voice_vi="selene-vi")])
    calls=mock_audio(monkeypatch)
    async def boot_twice():
        first=main.start_world_chapter_audio()
        assert first is not None
        assert main.start_world_chapter_audio() is None
        await first
        count=len(calls)
        assert count>0
        await main.start_world_chapter_audio()
        assert len(calls)==count
    asyncio.run(boot_twice())
    with factory() as db:
        assert not db.query(AppSetting).filter(AppSetting.key.like("moonfall_run:%")).count()
