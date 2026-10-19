"""Prepare the user's existing World CMS using its existing docs secret.

No app deployment, no credentials exported, no model/voice assignments changed.
"""
import json
from pathlib import Path
import modal

ORIGIN='https://nguyenthanhcongloi332004--character-chat-web.modal.run'
app=modal.App('world-cms-authored-audio-maintenance')
image=modal.Image.debian_slim(python_version='3.12').pip_install('httpx')
root=Path(__file__).resolve().parents[1]
audio_image=(modal.Image.debian_slim(python_version='3.12')
 .pip_install('fastapi>=0.115','uvicorn>=0.30','sqlalchemy>=2','pydantic>=2','python-multipart>=0.0.9','httpx>=0.27','pillow>=10.4','pymupdf>=1.24','python-docx>=1.1','python-pptx>=1.0','openpyxl>=3.1','cryptography>=43','imageio-ffmpeg','modal>=1.5,<2')
 .add_local_dir(str(root/'character_chat'),remote_path='/root/character_chat'))
audio_volume=modal.Volume.from_name('character-chat-data')

@app.function(image=audio_image,secrets=[modal.Secret.from_name('character-chat-docs'),modal.Secret.from_name('character-chat-llm')],volumes={'/data':audio_volume},timeout=3600)
def stage_audio(operation,content):
    """Write prepared audio only. Live CMS records and app deployment stay untouched."""
    import asyncio,copy,os,re,subprocess,tempfile,httpx,imageio_ffmpeg
    os.environ['DATA_DIR']='/data'
    from character_chat import main,moonfall_store
    from character_chat.api import hub_narration
    from character_chat.adventure.loader import seed
    from character_chat.adventure.authored_audio import script_events
    from character_chat.adventure import engine
    with main.Session() as db:live=copy.deepcopy(moonfall_store.config(db))
    if operation in ('diagnose-gate-audio','repair-gate-audio'):
        os.environ['WORLD_DEMO_ENABLED']='true'
        from character_chat.models import AppSetting
        async def diagnose():
            results=[]
            endpoint=next(r.endpoint for r in main.app.routes if getattr(r,'path','')=='/v1/moonfall/{ident}/chapter-audio')
            with main.Session() as db:
                rows=db.query(AppSetting).filter(AppSetting.key.like('moonfall_run:%')).order_by(AppSetting.updated_at.desc()).limit(40).all()
                for row in rows:
                    state=json.loads(row.value)
                    if state.get('engine_version')!=2 or state.get('chapter_id')!='selene_01':continue
                    try:
                        report=await endpoint(state['id'],state['owner'],db)
                        if operation=='repair-gate-audio' and state['phase']=='memory':
                            from character_chat.adventure.authored_audio import audio_key
                            missing={c['id'] for c in report['clips'] if not c['ready']}
                            voice=next(r.endpoint for r in main.app.routes if getattr(r,'path','')=='/v1/moonfall/{ident}/voice/{event_id}')
                            for event in state['events']:
                                if event.get('source')=='authored' and event['type']=='NARRATION' and audio_key(event,state['content_language']) in missing:
                                    await voice(state['id'],event['id'],{'voice_language':state['content_language']},state['owner'],db)
                            await audio_volume.commit.aio()
                            report=await endpoint(state['id'],state['owner'],db)
                        results.append(dict(phase=state['phase'],revision=state['revision'],config_revision=state['config_revision'],enabled=report['enabled'],status=report.get('status'),ready=sum(c['ready'] for c in report['clips']),total=len(report['clips']),missing=[c['id'] for c in report['clips'] if not c['ready']]))
                    except Exception as exc:results.append(dict(phase=state['phase'],error=type(exc).__name__,status=getattr(exc,'status_code',None)))
            return results
        return asyncio.run(diagnose())
    if operation=='resolve-young-voice':
        from character_chat.models import ModelConfig
        with main.Session() as db:
            spec=next(p for p in main.effective_presets(db) if ('preset:'+p.preset_type==live['character_source_id'] if live.get('character_source_id') else p.name.casefold()=='selene moonbrook'))
            selected=next(m for m in db.query(ModelConfig).filter_by(enabled=1) if 'tts' in main.model_profile(db,m).get('purposes',[]))
            voice=asyncio.run(main.selected_speech_voice(db,spec,main.character_voice_gender(spec),'vi',main.model_profile(db,selected),selected.api_base,main.credential_for_model(db,selected)))
            return dict(voice=voice,previous=live['adventure']['speaker_voices']['young_selene']['vi'])
    if operation=='diagnose-voice':
        from character_chat.models import ModelConfig
        with main.Session() as db:
            selected=db.get(ModelConfig,live['tts_model_id'])
            key=main.credential_for_model(db,selected)
            endpoint=main.speech_api_base(main.normalized_api_base(selected.api_base))+'/audio/speech'
            voice=live['adventure']['speaker_voices']['young_selene']['vi']
            response=httpx.post(endpoint,headers={'Authorization':'Bearer '+key},json=dict(model=selected.model_id,voice=voice,input='Tôi sẽ tự bước vào. Nhưng hãy để tôi nói hết trước đã.',response_format='mp3'),timeout=90)
            if response.status_code<400:return dict(status=response.status_code,voice=voice,audio_bytes=len(response.content))
            try:detail=response.json().get('detail') or response.json().get('error') or 'Provider returned an error'
            except ValueError:detail='Provider returned a non-JSON error'
            detail=str(detail).replace(key,'[redacted]')[:600]
            return dict(status=response.status_code,voice=voice,detail=detail)
    cfg=copy.deepcopy(live);fresh=seed()
    if content.get('young_voice_override'):
        cfg['adventure']['speaker_voices']['young_selene']['vi']=content['young_voice_override']
    cfg['chapters']=fresh['chapters']
    cfg['adventure']['story_beats']=fresh['adventure']['story_beats']
    # This worker stages the new script without activating a mismatched video
    # or changing production's configured model, voices, choices or saves.
    moonfall_store.config=lambda db:copy.deepcopy(cfg)
    hub_narration.config=lambda db:copy.deepcopy(content)
    def duration(audio):
        with tempfile.NamedTemporaryFile(suffix='.mp3') as f:
            f.write(audio);f.flush()
            out=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-i',f.name],capture_output=True,text=True).stderr
        match=re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)',out)
        return round(sum(float(v)*m for v,m in zip(match.groups(),(3600,60,1))),3) if match else None
    async def run():
        auth=(os.environ['DOCS_USERNAME'],os.environ['DOCS_PASSWORD'])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app),base_url='http://staging',auth=auth,timeout=3600) as client:
            if operation=='stage-intro':
                response=await client.post('/v1/admin/moonfall/hub-narration/prepare')
                if response.status_code!=200:return dict(status=response.status_code)
                result=response.json();timings=[]
                for language in ('vi','en'):
                    for cue in content['cues']:
                        audio=await client.get('/v1/admin/moonfall/hub-narration/audio/'+cue['id'],params={'language':language})
                        seconds=duration(audio.content) if audio.status_code==200 else None
                        slot=cue['end']-cue['start']-.15
                        timings.append(dict(language=language,cue=cue['id'],seconds=seconds,slot=round(slot,3),fits=seconds is not None and seconds<=slot*1.25,status=audio.status_code))
                result['timings']=timings;result['timing_ready']=all(r['fits'] for r in timings)
                return result
            # Admin snapshot preparation includes all four endings in the new
            # code; no player run or progression is created by this worker.
            result=[]
            for n in range(1,9):
                ident='selene_0'+str(n)
                response=await client.post('/v1/admin/moonfall/chapter-audio/prepare',json={'chapters':[ident]})
                ready=await client.get('/v1/admin/moonfall/chapter-audio',params={'chapter_id':ident})
                report=ready.json();retried=[]
                for language,stats in report.get('languages',{}).items():
                    for missing in stats.get('missing',[]):
                        attempt=await client.post('/v1/admin/moonfall/chapter-audio/prepare-line',json=dict(chapter_id=ident,language=language,key=missing['id']))
                        retried.append(dict(language=language,speaker=missing.get('speaker'),text=missing.get('text'),status=attempt.status_code,error=attempt.json().get('detail') if attempt.status_code!=200 else None))
                if retried:
                    report=(await client.get('/v1/admin/moonfall/chapter-audio',params={'chapter_id':ident})).json()
                result.append(dict(chapter=ident,status=ready.status_code,details=report,retried=retried))
                print(json.dumps(result[-1],ensure_ascii=False),flush=True)
                await audio_volume.commit.aio()
            return dict(chapters=result)
    result=asyncio.run(run());audio_volume.commit()
    return result

@app.function(image=image,secrets=[modal.Secret.from_name('character-chat-docs')],timeout=900)
def operate(operation,content=None):
    import os,httpx
    user=os.getenv('DOCS_USERNAME');password=os.getenv('DOCS_PASSWORD')
    if not user or not password:return dict(error='CMS credentials are not configured in the existing docs secret')
    with httpx.Client(auth=(user,password),timeout=600,follow_redirects=False) as client:
        def call(method,path,**kw):
            response=client.request(method,ORIGIN+path,**kw)
            if response.status_code>=400:raise RuntimeError('CMS '+path+' returned HTTP '+str(response.status_code))
            return response.json()
        intro=call('GET','/v1/admin/moonfall/hub-narration')
        world=call('GET','/v1/admin/moonfall')['config']
        if operation=='inspect':
            return dict(intro=intro,tts_model_selected=bool(world.get('tts_model_id')),narrator_voices=world.get('narrator_voices'),chapter_count=len(world.get('chapters',[])),supporting_voice_assignments=world.get('adventure',{}).get('speaker_voices',{}))
        if operation=='publish-story':
            from copy import deepcopy
            previous=deepcopy(world)
            authored=content['story']
            for key in ('schema_version','chapters','assets','visual_events','intro_asset','intro_narration'):
                world[key]=authored[key]
            for key in ('story_beats','chapter_one_flow','enrichment_enabled'):
                world['adventure'][key]=authored['adventure'][key]
            saved=call('PUT','/v1/admin/moonfall',json=world)
            return dict(previous=previous,revision=saved['revision'],chapters=len(saved['chapters']),assets=len(saved['assets']))
        if operation=='verify-media':
            from hashlib import sha256
            result=[]
            for asset in content['assets']:
                response=client.get(ORIGIN+'/v1/moonfall/assets/'+asset['id'],headers={'Range':'bytes=0-255'})
                result.append(dict(id=asset['id'],status=response.status_code,content_type=response.headers.get('content-type'),bytes=len(response.content),prefix_sha256=sha256(response.content[:256]).hexdigest(),expected=asset['prefix_sha256']))
            statuses={str(n):call('GET','/v1/admin/moonfall/chapter-audio?chapter_id=selene_0'+str(n)) for n in range(1,9)}
            return dict(media=result,health=call('GET','/health'),intro_cues=len(intro['cues']),silent_windows=len(intro.get('silent_windows',[])),m04_vi=world['chapters'][3]['localization']['selene_04.line.019']['vi'],chapter_audio=statuses,revision=world['revision'])
        if operation=='voice-check':
            catalog=call('GET','/v1/admin/moonfall/voices',params={'model_id':world.get('tts_model_id','')})
            voices={v['id']:v for v in catalog['voices']}
            assigned=world.get('adventure',{}).get('speaker_voices',{})
            return {speaker:{language:dict(id=voice,in_catalog=voice in voices,details=voices.get(voice)) for language,voice in values.items()} for speaker,values in assigned.items()}
        if operation=='apply-intro':
            # Legacy deployed CMS represents intentional silence as cue gaps.
            editable={key:content[key] for key in ('enabled','music_gain','duck_gain','voice_gain','cues','duration_seconds','silent_windows')}
            editable['revision']=intro['revision']
            saved=call('PUT','/v1/admin/moonfall/hub-narration',json=editable)
            return dict(previous=intro,saved=saved)
        if operation=='repair-young-voice':
            previous=world['adventure']['speaker_voices']['young_selene']['vi']
            world['adventure']['speaker_voices']['young_selene']['vi']=content['replacement_voice']
            saved=call('PUT','/v1/admin/moonfall',json=world)
            return dict(previous=previous,voice=saved['adventure']['speaker_voices']['young_selene']['vi'],revision=saved['revision'])
        if operation=='prepare-intro':return call('POST','/v1/admin/moonfall/hub-narration/prepare')
        if operation=='prepare-chapters':return call('POST','/v1/admin/moonfall/chapter-audio/prepare',json={})
        if operation=='chapter-status':
            return {str(n):call('GET','/v1/admin/moonfall/chapter-audio?chapter_id=selene_0'+str(n)) for n in range(1,9)}
        raise ValueError('Unknown maintenance operation')

@app.local_entrypoint()
def main(operation:str='inspect'):
    root=Path(__file__).resolve().parents[1]
    content=json.loads((root/'character_chat/story_data/world_hub_narration.json').read_text(encoding='utf8'))
    if operation=='publish-story':
        from character_chat.adventure.loader import seed
        content={'story':seed()}
    if operation=='verify-media':
        from character_chat.adventure.loader import seed
        from character_chat.adventure.props import manifest_assets,media_root
        from hashlib import sha256
        content={'assets':[dict(id=a['id'],prefix_sha256=sha256((media_root()/a['path']).read_bytes()[:256]).hexdigest()) for a in manifest_assets(seed()).values() if 'replacement_' in a['id'] or a['id'].startswith(('memory_video_','story_','ending_video_')) or a['id']=='enter_ruins_video']}
    if operation=='repair-young-voice':
        content['replacement_voice']=json.loads((root/'artifacts/world-hub/cms-resolve-young-voice.json').read_text(encoding='utf8'))['voice']
    repaired=root/'artifacts/world-hub/cms-repair-young-voice.json'
    if operation=='stage-chapters' and repaired.is_file():
        content['young_voice_override']=json.loads(repaired.read_text(encoding='utf8'))['voice']
    result=stage_audio.remote(operation,content) if operation in ('stage-intro','stage-chapters','diagnose-voice','resolve-young-voice','diagnose-gate-audio','repair-gate-audio') else operate.remote(operation,content)
    target=root/'artifacts/world-hub'/('cms-'+operation+'.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    # Only this task's metadata; never print credentials or full world configuration.
    if operation=='inspect':print(json.dumps({k:v for k,v in result.items() if k!='intro'},ensure_ascii=False))
    elif operation=='verify-media':print(json.dumps(dict(revision=result['revision'],media=len(result['media']),matched=sum(a['status'] in (200,206) and a['prefix_sha256']==a['expected'] for a in result['media']),health=result['health'],intro_cues=result['intro_cues'],silent_windows=result['silent_windows'])))
    elif operation=='chapter-status':print(json.dumps({k:{lang:{field:stats.get(field) for field in ('enabled','ready','total','status')} for lang,stats in v.get('languages',{}).items()} for k,v in result.items()},ensure_ascii=False))
    elif operation=='publish-story':print(json.dumps({k:v for k,v in result.items() if k!='previous'}))
    elif operation=='apply-intro':print(json.dumps(dict(saved_revision=result.get('saved',{}).get('revision'),cues=len(result.get('saved',{}).get('cues',[])))))
    else:print(json.dumps(result,ensure_ascii=False))
