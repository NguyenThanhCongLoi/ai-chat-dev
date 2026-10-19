"""Visual acceptance for supplied painted scenes, isolated from live users."""
import json,subprocess
from pathlib import Path
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view
from character_chat.adventure.props import manifest_assets,media_root
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1];out=root/'artifacts/selene-replacements/browser';out.mkdir(parents=True,exist_ok=True)
cfg=seed();cases=[];assets=manifest_assets(cfg)
for ch in cfg['chapters']:
    s=engine.fresh('fixture','selene','',cfg,'en',.5);s['admin_preview']=True
    s=engine.admin_preview_chapter(s,ch['id'])
    if s['phase']=='intro':s=engine.advance(s,'intro_complete')
    for place in ch['scenes']:
        s=engine.advance(s,'go',place['id']);run=view(s,{'name':'Selene'})
        if run['embedded_scene']:cases.append(run)
fixture=out/'fixture.tsx'
fixture.write_text('''import React from 'react';import {createRoot} from 'react-dom/client';
import EmbeddedScene from '../../../frontend/src/worlds/EmbeddedScene';
import '../../../frontend/src/worlds/adventure.css';
const cases='''+json.dumps(cases,ensure_ascii=False)+''';
window.show=(i,blocked=false)=>{const run=cases[i],scene=run.embedded_scene;
createRoot(document.getElementById('root')).render(<div className="maRoot"><div className="maScene" style={{width:'100%',aspectRatio:scene.width+'/'+scene.height}}>
<img className="maBackground" src={run.assets[scene.background].url}/>
<EmbeddedScene run={run} blocked={blocked} inspectLabel="Inspect " onInspect={id=>window.clicked=id}/></div></div>);};
''',encoding='utf8')
node=root.parent/'Chatbot/.tools/node-v24.21.0-win-x64/node.exe'
subprocess.run([str(node),'-e',"require('./frontend/node_modules/esbuild').buildSync({entryPoints:[process.argv[1]],bundle:true,nodePaths:['./frontend/node_modules'],jsx:'automatic',outfile:process.argv[2]})",str(fixture),str(out/'fixture.js')],cwd=root,check=True)
report=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport=dict(width=1280,height=1000),reduced_motion='reduce')
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def route(r):
        ident=r.request.url.split('/assets/')[1].split('?')[0]
        r.fulfill(path=str(media_root()/assets[ident]['path']))
    page.route('**/v1/moonfall/assets/**',route)
    for i,run in enumerate(cases):
        for width in (1100,430):
            page.set_viewport_size(dict(width=width,height=1000))
            page.goto('about:blank');page.set_content('<base href="http://fixture.local/"><div id="root"></div>')
            page.add_style_tag(path=str(out/'fixture.css'));page.add_script_tag(path=str(out/'fixture.js'))
            page.evaluate('(i)=>window.show(i)',i)
            page.locator('.maBackground').evaluate('(im)=>im.decode()')
            stage=page.locator('.maScene').bounding_box()
            assert abs(stage['width']/stage['height']-run['embedded_scene']['width']/run['embedded_scene']['height'])<.02
            objects=[o for o in run['objects'] if o['mode']=='embedded' and o['interactive']]
            for obj in objects:
                x=sum(p[0] for p in obj['polygon'])/len(obj['polygon']);y=sum(p[1] for p in obj['polygon'])/len(obj['polygon'])
                point=page.evaluate("""({id,x,y})=>{const el=document.querySelector('[data-world-target="'+id+'"]');const r=el.getBoundingClientRect();const inside=(a,b)=>document.elementFromPoint(a,b)===el;if(inside(x,y))return [x,y];for(let i=1;i<20;i++)for(let j=1;j<20;j++){const a=r.x+r.width*i/20,b=r.y+r.height*j/20;if(inside(a,b))return [a,b];}return null;}""",dict(id=obj['id'],x=stage['x']+stage['width']*x,y=stage['y']+stage['height']*y))
                assert point,obj['id']+' has no reachable painted region'
                page.mouse.click(*point)
                assert page.evaluate('window.clicked')==obj['id'],obj['id']
                shape=page.locator('[data-world-target="'+obj['id']+'"]')
                shape.focus();page.keyboard.press('Enter');assert page.evaluate('window.clicked')==obj['id']
            assert page.locator('.maItemLight').count()==len(objects)
            if width==1100:page.locator('.maScene').screenshot(path=str(out/(run['chapter_id']+'-'+run['location']+'.png')),animations='disabled')
            report.append(dict(chapter=run['chapter_id'],scene=run['location'],viewport=width,clicks=len(objects)))
    assert not errors,errors
    browser.close()
(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('Passed',len(report),'desktop/mobile scene checks;',sum(r['clicks'] for r in report),'painted pointer and keyboard targets')
