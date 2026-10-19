"""Opt-in desktop UI acceptance for the v2 arc using an isolated database."""
import os,socket,threading,time,json
from pathlib import Path
import pytest,uvicorn
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat import main

@pytest.mark.skipif(os.getenv("RUN_MOONFALL_BROWSER")!="1",reason="Opt-in desktop browser test")
def test_chapter_conclusion_and_music_controls(moonfall,monkeypatch,tmp_path):
    from playwright.sync_api import sync_playwright,expect
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from character_chat.models import Base
    _,old_factory,_=moonfall
    monkeypatch.setenv("WORLD_ADVENTURE_ENABLED","true")
    engine=create_engine("sqlite:///"+str(tmp_path/"adventure.sqlite"),connect_args={"check_same_thread":False})
    Base.metadata.create_all(engine)
    with old_factory.kw["bind"].connect() as src,engine.begin() as dst:
        for table in Base.metadata.sorted_tables:
            rows=[dict(r) for r in src.execute(table.select()).mappings()]
            if rows:dst.execute(table.insert(),rows)
    factory=sessionmaker(engine,expire_on_commit=False)
    def dependency():
        with factory() as db:yield db
    main.app.dependency_overrides[main.db_session]=dependency
    monkeypatch.setattr(main,"Session",factory)
    monkeypatch.setattr(main,"direct_completion",lambda *a,**k:"I remember what we found together among the ruins.")
    monkeypatch.setenv("FRONTEND_DIST",str(Path("frontend/dist").resolve()))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(main.app,host="127.0.0.1",port=port,log_level="warning",lifespan="off"))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    for _ in range(100):
        if server.started:break
        time.sleep(.05)
    try:
        from test_world_pacing import first_complete
        from test_memory_adventure import play_to_final
        from character_chat.adventure import engine as story
        from character_chat.moonfall_store import run_key
        from character_chat.models import AppSetting
        from playwright.sync_api import sync_playwright,expect
        states=[first_complete(),play_to_final()]
        last=states[1]
        choice=last['config']['chapters'][7]['choice']['options'][0]['id']
        last=story.advance(last,'choice',choice)
        last=story.advance(last,'confirm_ending')
        if last['phase']=='memory':last=story.advance(last,'finish_memory_cinematic')
        states[1]=last
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            ctx=browser.new_context(viewport={'width':1600,'height':1000},reduced_motion='reduce')
            ctx.add_init_script("localStorage.setItem('auth_token','isolated-v2');localStorage.setItem('ui_language','en');")
            page=ctx.new_page();browser_errors=[]
            page.on("pageerror",lambda e:browser_errors.append(str(e)))
            ctx.add_init_script("""window.__worldAudios=[];const NativeAudio=window.Audio;window.Audio=function(...args){const audio=new NativeAudio(...args);window.__worldAudios.push(audio);return audio;};""")
            page.route("**/v1/roleplay/background-music",lambda route:route.fulfill(json={"tracks":[{"id":"cms-a","title":"CMS Song A","url":"/test-bgm/a.wav"},{"id":"cms-b","title":"CMS Song B","url":"/test-bgm/b.wav"}],"volume":.3}))
            import io,wave
            raw=io.BytesIO()
            with wave.open(raw,"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(8000);wav.writeframes(bytes(160000))
            page.route("**/test-bgm/*.wav",lambda route:route.fulfill(content_type="audio/wav",body=raw.getvalue()))
            page.route("**/v1/moonfall/*/chapter-audio",lambda route:route.fulfill(json={"enabled":False,"clips":[],"version":"fixture-off"}))
            page.route('**/v1/moonfall/*/voice/*',lambda r:r.fulfill(status=503,json={'detail':'fixture'}))
            for state in states:
                with factory() as db:
                    db.query(AppSetting).filter(AppSetting.key.like('moonfall_run:%')).delete(synchronize_session=False)
                    db.add(AppSetting(key=run_key('alice',state['id']),value=json.dumps(state,ensure_ascii=False)))
                    db.commit()
                page.goto(f'http://127.0.0.1:{port}/worlds?character=selene')
                modal=page.locator('.maReview')
                expect(modal).to_be_visible(timeout=30000)
                with page.expect_response(lambda r:r.url.endswith('/v1/moonfall') and r.request.method=='POST') as resumed:
                    page.reload()
                assert resumed.value.json()['chapter_id']==state['chapter_id']
                expect(modal).to_be_visible(timeout=30000)
                expect(page.locator('.maChapterConclusion')).to_have_count(0)
                expect(page.locator('.maPreparation')).to_have_count(0,timeout=90000)
                expect(page.locator('.maConversation textarea')).to_be_editable()
                if state is states[0]:
                    page.get_by_role("button",name="World mixer",exact=True).click()
                    expect(page.locator(".mfMixer")).to_contain_text("CMS Song A")
                    page.evaluate("""()=>{const audio=window.__worldAudios.find(a=>a.src.includes('/test-bgm/a.wav'));if(!audio)throw Error('Missing World BGM');if(audio.loop)throw Error('Playlist incorrectly loops first song');audio.dispatchEvent(new Event('ended'));}""")
                    expect(page.locator(".mfMixer")).to_contain_text("CMS Song B")
                    page.get_by_role("button",name="World mixer",exact=True).click()

                with page.expect_response(lambda r:'/return-to-chat' in r.url) as response:
                    modal.get_by_role('button',name='Return to Selene chat',exact=True).click()
                assert response.value.status==200,response.value.text()
                page.wait_for_url('**/role-play-ai?**',timeout=30000)
            page.goto(f'http://127.0.0.1:{port}/worlds?character=selene')
            expect(page.locator('.maReview')).to_be_visible(timeout=30000)
            page.get_by_role('button',name='Replay from Chapter 1',exact=True).click()
            with page.expect_response(lambda r:r.url.endswith('/act') and r.request.method=='POST') as replay:
                page.get_by_role('button',name='Start a new attempt',exact=True).click()
            assert replay.value.status==200,replay.value.text()
            assert replay.value.json()['attempt_number']==2
            assert replay.value.json()['chapter_id']=='selene_01'
            expect(page.locator('.maChapterConclusion')).to_have_count(0)
            page.reload()
            expect(page.locator('.maChapterConclusion')).to_have_count(0)
            page.goto(f'http://127.0.0.1:{port}/worlds/admin')
            expect(page.locator('.mfCms')).to_be_visible(timeout=30000)
            sliders=page.locator('.mfCmsBody input[type=range]')
            expect(sliders).to_have_count(7,timeout=30000)
            sliders.nth(1).fill('60')
            with page.expect_response(lambda r:'/v1/admin/moonfall' in r.url and r.request.method=='PUT') as saved:
                page.get_by_role('button',name='Lưu cấu hình World',exact=True).click()
            assert saved.value.status==200,saved.value.text()
            assert saved.value.json()['adventure']['music_levels']['music']==.6
            # Embedded platform hides World without unmounting it. A modal left
            # in the top layer would make the returned chat completely inert.
            import subprocess
            bundle=tmp_path/"embedded-world.js"
            subprocess.run([r"D:\Chatbot\.tools\node-v24.21.0-win-x64\node.exe","tests/world_embed_fixture.cjs",str(bundle)],check=True)
            state=states[0];state["revision"]=20
            with factory() as db:
                db.add(AppSetting(key=run_key("alice",state["id"]),value=json.dumps(state,ensure_ascii=False)))
                db.commit()
            snapshot=page.request.get(f"http://127.0.0.1:{port}/v1/moonfall/"+state["id"]).json()
            def resume_fixture(route):
                if route.request.method=="POST":route.fulfill(json=snapshot)
                else:route.continue_()
            page.route("**/v1/moonfall",resume_fixture)
            page.route("**/fixture-world-host.js",lambda route:route.fulfill(content_type="application/javascript",body=bundle.read_bytes()))
            page.route("**/fixture-world-host.css",lambda route:route.fulfill(content_type="text/css",body=bundle.with_suffix(".css").read_bytes()))
            page.route("**/embedded-world-fixture",lambda route:route.fulfill(content_type="text/html",body='<html><head><link rel="stylesheet" href="/fixture-world-host.css"></head><body><div id="root"></div><script src="/fixture-world-host.js"></script></body></html>'))
            page.goto(f"http://127.0.0.1:{port}/embedded-world-fixture")
            try:
                expect(page.locator(".maChapterConclusion")).to_be_visible(timeout=30000)
            except AssertionError:
                print("EMBEDDED DEBUG",browser_errors,page.locator("body").inner_text()[:3000])
                raise
            page.locator(".maChapterConclusion > button.maPrimary").click()
            expect(page.locator("#host-chat")).to_be_visible(timeout=30000)
            expect(page.locator("dialog:modal")).to_have_count(0)
            page.locator("#host-chat").click()
            expect(page.locator("#host-chat")).to_have_text("Chat responds")
            # The hub must show measured progress while its intro is still downloading.
            page.route("**/v1/worlds/config",lambda route:route.fulfill(json={"enabled":True}))
            page.route("**/v1/moonfall/hub/presentation",lambda route:route.fulfill(json={"intro":[{"id":"fixture-intro","url":"/loading-fixture.webm"}]}))
            page.route("**/v1/moonfall/hub/narration-config",lambda route:route.fulfill(json={"enabled":False,"revision":1,"cues":[]}))
            page.route("**/v1/moonfall/hub",lambda route:route.fulfill(json={"background":None,"characters":[],"intro":[]}))
            held=[]
            page.route("**/loading-fixture.webm",lambda route:held.append(route))
            page.goto(f"http://127.0.0.1:{port}/worlds")
            expect(page.locator(".homePreparationProgress progress")).to_have_attribute("max","100",timeout=30000)
            expect(page.locator(".homePreparationProgress span")).to_have_text(__import__("re").compile(r"[0-9]+%"))
            expect(page.locator(".assistantGate")).to_contain_text("Almost ready")
            expect(page.locator(".assistantGate .roleplayLoadingCat")).to_be_visible()
            bar=page.locator(".homePreparationProgress progress").bounding_box()
            assert bar and 4 <= bar["height"] <= 8 and bar["width"] <= 320, bar
            # Chapter loader must never expand its progress element vertically.
            page.add_style_tag(path=str(Path("frontend/src/worlds/adventure.css").resolve()))
            page.evaluate('() => {const gate=document.createElement("div");gate.className="maPreparation";gate.innerHTML="<progress max=1 value=.65></progress><strong>65%</strong>";document.body.append(gate);}')
            chapter_bar=page.locator(".maPreparation progress").bounding_box()
            assert chapter_bar and 4 <= chapter_bar["height"] <= 8 and chapter_bar["width"] <= 320, chapter_bar
            for route in held:route.abort()
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10)
