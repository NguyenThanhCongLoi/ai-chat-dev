"""Opt-in desktop UI acceptance for the v2 arc using an isolated database."""
import os,socket,threading,time,json
from pathlib import Path
import pytest,uvicorn
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat import main

@pytest.mark.skipif(os.getenv("RUN_MOONFALL_BROWSER")!="1",reason="Opt-in desktop browser test")
def test_stay_and_reopen_completed_maps_are_silent_and_prepared(moonfall,monkeypatch,tmp_path):
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
        s=gate_ready()
        from character_chat.adventure import engine as story_engine
        for action in ("open_gate","finish_gate_cinematic","finish_memory_cinematic"):s=story_engine.advance(s,action)
        s["revision"]=10
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
            # Show the just-completed state once, then use the real persisted API.
            snapshot=page.request.get(f"http://127.0.0.1:{port}/v1/moonfall/"+s["id"]).json()
            snapshot["revision"]-=1  # Simulate a background reflection winning the save race.
            page.route("**/v1/moonfall",lambda route:route.fulfill(json=snapshot) if route.request.method=="POST" else route.continue_())
            downloads=[]
            page.on("request",lambda request:downloads.append(request.url) if "/v1/moonfall/assets/" in request.url else None)
            page.goto(f"http://127.0.0.1:{port}/worlds?character=selene")
            expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
            expect(page.locator(".maChapterConclusion")).to_be_visible(timeout=30000)
            with page.expect_response(lambda r:r.url.endswith("/act") and r.request.method=="POST") as stayed:
                page.get_by_role("button",name="Stay in this chapter",exact=True).click()
            assert stayed.value.status==409
            expect(page.locator(".maChapterConclusion")).to_have_count(0,timeout=10000)
            expect(page.locator(".maReview")).to_be_visible(timeout=15000)
            expect(page.locator(".maReading")).to_have_count(0)
            expect(page.locator(".worldCinematic")).to_have_count(0)
            expect(page.locator(".maSceneSubtitle")).to_have_count(0)
            expect(page.locator(".maCornerSeal img")).to_have_attribute("src",__import__("re").compile("^blob:"))
            before=len(downloads)
            for place in ("outer_ruins","ancient_gate"):
                with page.expect_response(lambda r:r.url.endswith("/act") and r.request.method=="POST") as moved:
                    page.locator('[data-world-target="map:'+place+'"]').click()
                assert moved.value.status==200,moved.value.text()
                expect(page.locator(".maPreparation")).to_have_count(0)
                expect(page.locator(".maBackground")).to_have_attribute("src",__import__("re").compile("^blob:"))
                expect(page.locator(".maReading")).to_have_count(0)
                expect(page.locator(".worldCinematic")).to_have_count(0)
                expect(page.locator(".maMapArrival")).to_be_visible()
                assert page.locator(".maMapArrival button").count()==0
                expect(page.locator(".maMapArrival")).to_have_count(0,timeout=4000)
            assert len(downloads)==before,(before,len(downloads))
            assert not voice_requests,voice_requests
            page.unroute("**/v1/moonfall")
            page.reload()
            expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
            expect(page.locator(".maReview")).to_be_visible(timeout=30000)
            expect(page.locator(".maChapterConclusion")).to_have_count(0)
            expect(page.locator(".worldCinematic")).to_have_count(0)
            expect(page.locator(".maReading")).to_have_count(0)
            output=Path("artifacts/memory-adventure/silent-review");output.mkdir(parents=True,exist_ok=True)
            page.locator(".maScene").screenshot(path=str(output/"prepared-map-seal.png"))
            assert not errors,errors
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10)
