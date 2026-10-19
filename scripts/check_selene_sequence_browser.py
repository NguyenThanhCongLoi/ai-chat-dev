"""Exercise the real React speech hook with controlled media completion."""
import json,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/selene-sequence';OUT.mkdir(parents=True,exist_ok=True)
cases=[]
for n,scene,target in [(1,'side_path','arrow_trap'),(2,'echo_archway','follow_silhouette'),(3,'seal_trap','seal_contact'),(4,'collapse_passage','falling_ceiling'),(5,'archive_defense','paper_accusation'),(6,'mirror_hall','mirror_desync'),(7,'manifestation','gathering_fragments')]:
    s=engine.fresh('test','selene','',seed(),'vi',.5);s['admin_preview']=True;s=engine.admin_preview_chapter(s,f'selene_{n:02}')
    if s['phase']=='intro':s=engine.advance(s,'intro_complete')
    s=engine.advance(s,'go',scene);s['revision']=10
    initial=view(s,{'name':'Selene'});s=engine.advance(s,'inspect',f'selene_{n:02}_'+target);s['revision']=11
    result=view(s,{'name':'Selene'});fresh=[e for e in result['events'] if e['id'] not in {e['id'] for e in initial['events']}]
    cases.append(dict(initial=initial,result=result,speech=[e['id'] for e in fresh if e['type']=='CHARACTER_SPEECH' and e.get('auto_voice')],movie=next(e['id'] for e in fresh if e['type']=='SYSTEM' and e['visual_event'] in ('ARROW_TRAP','ECHO_GIRL','SEAL_TRAP','ACADEMY_COLLAPSE','ARCHIVE_AWAKENS','MIRROR_DESYNC','PALE_MOON_MANIFESTATION'))))
(OUT/'cases.json').write_text(json.dumps(cases,ensure_ascii=False),encoding='utf8')
(OUT/'fixture.tsx').write_text('''import React,{useState,useRef} from 'react';import {createRoot} from 'react-dom/client';
import {useStorySpeech} from '../../frontend/src/worlds/useStorySpeech';
import cases from './cases.json';
function App({index}){const data=cases[index], [run,setRun]=useState(data.initial),[movie,setMovie]=useState(''),pending=useRef(null);
 const speech=useStorySpeech(run,true,'characters',{play:async(e)=>{window.log.push('movie:'+e.id);setMovie(e.id);await new Promise(r=>pending.current=r);},cancel:()=>{setMovie('');pending.current?.();pending.current=null;}});
 return <><button id="start" onClick={()=>setRun(data.result)}>start</button><button id="voice" onClick={()=>speech.setAutomatic(false)}>voice off</button><button id="stop" onClick={()=>speech.stop()}>leave</button>
 <span id="busy">{String(speech.waitingForDialogue)}</span>{movie&&<button id="movie" onClick={()=>{setMovie('');pending.current?.();pending.current=null;}}>movie end/skip/error</button>}
 <div id="transcript">{run.events.filter(e=>!speech.hiddenEventIds.has(e.id)).map(e=><p key={e.id} data-event={e.id}>{e.text}</p>)}</div></>}
window.show=index=>{window.log=[];createRoot(document.getElementById('root')).render(<App index={index}/>);};
''',encoding='utf8')
mock="""export function preparedChapterClip(run,event){const element={pause(){},currentTime:0,onplay:null,onended:null,onerror:null};return {url:'fixture',element,mixer:{setVolume(){},play(){window.log.push('speech:'+event.id);element.onplay?.();window.finishSpeech=()=>element.onended?.();return Promise.resolve();},dispose(){}}};}"""
build="""const esbuild=require('./frontend/node_modules/esbuild');esbuild.build({entryPoints:[process.argv[1]],bundle:true,nodePaths:['./frontend/node_modules'],jsx:'automatic',outfile:process.argv[2],plugins:[{name:'audio',setup(b){b.onResolve({filter:/chapterSpeechMedia$/},()=>({path:'prepared',namespace:'mock'}));b.onLoad({filter:/.*/,namespace:'mock'},()=>({contents:process.argv[3],loader:'js'}));}}]});"""
subprocess.run([str(ROOT.parent/'Chatbot/.tools/node-v24.21.0-win-x64/node.exe'),'-e',build,str(OUT/'fixture.tsx'),str(OUT/'fixture.js'),mock],cwd=ROOT,check=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    for index,data in enumerate(cases):
        page.goto('about:blank');page.set_content('<div id="root"></div>');page.add_script_tag(path=str(OUT/'fixture.js'));page.evaluate('(i)=>window.show(i)',index)
        page.locator('#start').click()
        movie=data['movie'];spoken=data['speech']
        before=next((e['id'] for e in data['result']['events'] if e['id'] in spoken),None)
        is_before=bool(before and next(i for i,e in enumerate(data['result']['events']) if e['id']==before)<next(i for i,e in enumerate(data['result']['events']) if e['id']==movie))
        if is_before:
            page.wait_for_function('(id)=>window.log.includes("speech:"+id)',arg=before)
            expect(page.locator('#movie')).to_have_count(0)
            page.evaluate('window.finishSpeech()')
        expect(page.locator('#movie')).to_be_visible()
        post=[e['id'] for e in data['result']['events'][next(i for i,e in enumerate(data['result']['events']) if e['id']==movie)+1:] if e['id'] in spoken]
        for ident in post:expect(page.locator('[data-event="'+ident+'"]')).to_have_count(0)
        expect(page.locator('#busy')).to_have_text('true');page.locator('#movie').click()
        for ident in post:
            page.wait_for_function('(id)=>window.log.includes("speech:"+id)',arg=ident)
            expect(page.locator('[data-event="'+ident+'"]')).to_have_count(1);page.evaluate('window.finishSpeech()')
        expect(page.locator('#busy')).to_have_text('false')
        log=page.evaluate('window.log');(OUT/f'chapter-{index+1}.json').write_text(json.dumps(log,indent=2),encoding='utf8')
    assert not errors,errors
    browser.close()
print('Passed all seven React dialogue/movie timelines; reactions remain hidden until video completion')
