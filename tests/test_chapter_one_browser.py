"""Opt-in desktop UI acceptance for the v2 arc using an isolated database."""
import os,socket,threading,time,json
from pathlib import Path
import pytest,uvicorn
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat import main

@pytest.mark.skipif(os.getenv("RUN_MOONFALL_BROWSER")!="1",reason="Opt-in desktop browser test")
def test_gate_ready_invisible_click_video_and_scroll(moonfall,monkeypatch,tmp_path):
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
        from test_chapter_one_sequence import gate_ready
        from character_chat.models import AppSetting
        from character_chat import moonfall_store as storage
        from character_chat.adventure.projection import view
        s=gate_ready();s["attempt_number"]=2;s["revision"]=10;s["phase"]="explore";s["choices"]=[];s["events"]=s["events"][:-2]
        with factory() as db:
            db.add(AppSetting(key=storage.run_key('alice',s['id']),value=json.dumps(s,ensure_ascii=False)))
            db.commit()
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            ctx=browser.new_context(viewport={'width':1600,'height':1000})
            ctx.add_init_script("localStorage.setItem('auth_token','isolated-v2');localStorage.setItem('ui_language','en');")
            page=ctx.new_page();errors=[];voice_requests=[]
            import io,wave
            wave_data=io.BytesIO()
            with wave.open(wave_data,"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(8000);wav.writeframes(bytes(32000))
            page.route("**/v1/moonfall/*/chapter-audio/*",lambda route:route.fulfill(content_type="audio/wav",body=wave_data.getvalue()))

            page.on('pageerror',lambda e:errors.append(str(e)))
            page.route('**/v1/moonfall/*/voice/*',lambda r:(voice_requests.append(r.request.url),r.fulfill(status=503,json={'detail':'fixture'})))
            video_check=page.request.get(f"http://127.0.0.1:{port}/v1/moonfall/assets/enter_ruins_video")
            assert video_check.status==200,(video_check.status,video_check.text()[:500])
            page.goto(f'http://127.0.0.1:{port}/worlds?character=selene')
            expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
            page.locator(".maTools > button").last.click()
            expect(page.locator('[data-effect="THOUGHT_BUBBLE"]')).to_be_visible(timeout=10000)
            page.locator(".maChoices button").nth(1).click()
            expect(page.locator(".maReading").first).to_be_visible(timeout=30000)
            expect(page.locator('[data-world-target="selene_01_old_gate"]')).to_have_attribute("aria-disabled","true")
            expect(page.locator('[data-cinematic="enter_ruins_video"]')).to_have_count(0)
            expect(page.locator('.maGatePrompt')).to_contain_text('open the ancient gate',timeout=60000)
            expect(page.locator('.maPreparation')).to_have_count(0,timeout=90000)
            gate=page.locator('[data-world-target="selene_01_old_gate"]')
            expect(gate).to_have_attribute('aria-disabled','false')
            expect(page.locator('[data-world-target="selene_01_collapsed_path"]')).to_have_attribute('aria-disabled','true')
            gate.focus()
            assert gate.evaluate('(el)=>getComputedStyle(el).stroke')!='rgba(0, 0, 0, 0)'
            assert page.locator('.maEmbeddedHint').count()==0
            assert gate.locator('title').count()==1
            with page.expect_response(lambda r:r.url.endswith('/act') and r.request.method=='POST') as opened:
                gate.press('Enter')
            assert opened.value.status==200
            assert opened.value.json()['phase']=='gate_cinematic'
            expect(page.locator('[data-cinematic="enter_ruins_video"]')).to_be_visible(timeout=30000)
            video=page.locator('[data-cinematic="enter_ruins_video"] video')
            expect(video).to_have_attribute('src',__import__('re').compile('^blob:'),timeout=15000)
            page.get_by_role('button',name='Skip cinematic',exact=True).click()
            expect(page.locator('[data-cinematic="memory_video_01"]')).to_be_visible(timeout=30000)
            assert page.locator('.maCinematicNarration button').count()==0
            # Manual narrator playback belongs only to the transcript.
            assert page.locator('.maTranscript button[aria-label*="narration"]').count()>0
            page.get_by_role('button',name='Skip cinematic',exact=True).click()
            expect(page.locator(".maReading").first).to_be_visible(timeout=30000)
            expect(page.locator(".maChapterConclusion")).to_have_count(0)
            expect(page.locator('.maChapterConclusion')).to_be_visible(timeout=30000)
            expect(page.locator('.maParchment')).to_contain_text('Moonbrook')
            expect(page.locator('.maEndSentence')).to_contain_text('Chapter 1')
            assert page.locator('.maCinematicNarration button').count()==0
            output=Path('artifacts/memory-adventure/chapter-one-flow');output.mkdir(parents=True,exist_ok=True)
            page.locator('.maChapterConclusion').screenshot(path=str(output/'scroll.png'),animations='disabled')
            expect(page.get_by_role("button",name="Next chapter")).to_be_visible()
            page.get_by_role("button",name="Next chapter").click()
            expect(page.locator(".maChapterConclusion")).to_have_count(0,timeout=30000)
            expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
            # Chapter 2: inspecting a pendant must not launch a transition movie.
            expect(page.locator('[data-world-target="selene_02_pendant"]')).to_have_attribute("aria-disabled","false",timeout=30000)
            with page.expect_response(lambda r:r.url.endswith("/act") and r.request.method=="POST") as pendant:
                page.locator('[data-world-target="selene_02_pendant"]').press("Enter")
            assert pendant.value.status==200,pendant.value.text()
            expect(page.locator(".maReading").first).to_be_visible(timeout=10000)
            expect(page.locator('[data-cinematic="memory_transition"]')).to_have_count(0)
            expect(page.locator('[data-cinematic="chapter_complete_video"]')).to_have_count(0)
            page.locator('[data-world-target="map:moonflower_garden"]').click()
            for ident in ("selene_02_stone_bench","selene_02_erased_names","selene_02_follow_silhouette","selene_02_echo_trace"):
                target=page.locator('[data-world-target="'+ident+'"]')
                expect(target).to_have_attribute("aria-disabled","false",timeout=60000)
                target.press("Enter")
            archive=page.locator('[data-world-target="map:archive"]')
            expect(archive).to_be_enabled(timeout=60000)
            archive.click()
            expect(page.locator('[data-world-target="selene_02_journal"]')).to_have_attribute("aria-disabled","false",timeout=30000)
            with page.expect_response(lambda r:r.url.endswith("/act") and r.request.method=="POST") as journal:
                page.locator('[data-world-target="selene_02_journal"]').press("Enter")
            data=journal.value.json()
            beat=data["events"][-1]["beat_id"]
            assert sum(e["type"]=="CHARACTER_SPEECH" and e["auto_voice"] for e in data["events"] if e.get("beat_id")==beat)==1
            expect(page.locator('[data-cinematic="memory_transition"]')).to_have_count(0)
            torn=page.locator('[data-world-target="selene_02_torn_page"]')
            expect(torn).to_have_attribute("aria-disabled","false")
            with page.expect_response(lambda r:r.url.endswith("/act") and r.request.method=="POST") as torn_response:
                torn.press("Enter")
            assert torn_response.value.status==200,torn_response.value.text()
            # Seed the expanded chapter-2 investigation prerequisites; this test owns the gate/memory transitions.
            from character_chat.adventure import engine as story_engine
            with factory() as db:
                saved=db.get(AppSetting,storage.run_key('alice',s['id']))
                state=json.loads(saved.value);chapter=story_engine.chapter(state)
                for place in chapter['scenes']:
                    state=story_engine.advance(state,'go',place['id'])
                    for obj in place['hotspots']:
                        if obj['id'] in chapter['required_inspections'] and obj['id'] not in state['inspected']:
                            state=story_engine.advance(state,'inspect',obj['id'])
                state=story_engine.advance(state,'go','archive');state['revision']+=1
                saved.value=json.dumps(state,ensure_ascii=False);db.commit()
            page.reload()
            expect(page.locator('.maPreparation')).to_have_count(0,timeout=90000)
            expect(page.locator(".maPuzzle .maTokens")).to_be_visible(timeout=10000)
            tokens=page.locator(".maPuzzle .maTokens")
            for label in ("The pendant is given","Selene promises to remember","The girl gently teases her"):
                tokens.get_by_role("button",name=label,exact=True).click()
            page.locator(".maPuzzle > button").first.click()
            page.locator(".maChoices button").first.click()
            expect(page.locator('[data-cinematic="memory_video_02"]')).to_be_visible(timeout=15000)
            expect(page.locator('[data-cinematic="memory_transition"]')).to_have_count(0)
            page.get_by_role("button",name="Skip cinematic",exact=True).click()
            expect(page.locator(".maChapterConclusion")).to_be_visible(timeout=15000)
            expect(page.locator(".worldCinematic")).to_have_count(0)
            if voice_requests:
                snapshot=page.request.get(f"http://127.0.0.1:{port}/v1/moonfall/"+s["id"]).json()
                print("VOICE CACHE MISSES",[(url,[e for e in snapshot["events"] if e["id"]==url.rsplit("/",1)[-1]]) for url in voice_requests])
            assert not voice_requests,voice_requests
            assert not errors,errors
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10)
