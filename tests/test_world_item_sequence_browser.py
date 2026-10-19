"""Opt-in desktop UI acceptance for the v2 arc using an isolated database."""
import os,socket,threading,time,json
from pathlib import Path
import pytest,uvicorn
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat import main

@pytest.mark.skipif(os.getenv("RUN_MOONFALL_BROWSER")!="1",reason="Opt-in desktop browser test")
def test_only_gate_then_key_with_cover_and_matching_dialogue(moonfall,monkeypatch,tmp_path):
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
        from character_chat.adventure import engine as story_engine
        from character_chat.adventure.loader import seed
        s=story_engine.advance(story_engine.fresh("alice","selene","",seed(),"en",.5),"intro_complete")
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
            def ready_audio_catalog(route):
                response=route.fetch()
                plan=response.json()
                for clip in plan.get("clips",[]):clip["ready"]=True
                route.fulfill(status=200,content_type="application/json",body=json.dumps(plan))
            page.route("**/v1/moonfall/*/chapter-audio",ready_audio_catalog)


            page.on('pageerror',lambda e:errors.append(str(e)))
            failures=[]
            page.on("response",lambda r:failures.append(str(r.status)+" "+r.url) if r.status>=400 else None)
            page.on("console",lambda m:failures.append(m.text) if m.type=="warning" else None)
            page.on("requestfailed",lambda r:failures.append(r.url+" "+str(r.failure)))
            page.route('**/v1/moonfall/*/voice/*',lambda r:(voice_requests.append(r.request.url),r.fulfill(status=503,json={'detail':'fixture'})))
            video_check=page.request.get(f"http://127.0.0.1:{port}/v1/moonfall/assets/enter_ruins_video")
            assert video_check.status==200,(video_check.status,video_check.text()[:500])
            page.goto(f"http://127.0.0.1:{port}/worlds?character=selene")
            expect(page.locator(".maRoot")).to_be_visible(timeout=30000)
            try:
                expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
            except AssertionError:
                raise AssertionError(page.locator(".maPreparation").inner_text()+" "+str(errors)+" "+str(failures))
            gate=page.locator('[data-world-target="selene_01_old_gate"]')
            expect(gate).to_have_attribute("aria-disabled","false",timeout=15000)
            expect(page.locator('[data-hint-for="selene_01_old_gate"]')).to_have_count(1)
            gate.hover()
            assert gate.evaluate("(el)=>getComputedStyle(el).fill")=="rgba(0, 0, 0, 0)"
            assert gate.evaluate("(el)=>getComputedStyle(el).stroke")=="rgba(0, 0, 0, 0)"
            assert gate.evaluate("(el)=>getComputedStyle(el).cursor")=="pointer"
            assert gate.evaluate("(el)=>parseFloat(getComputedStyle(el).strokeWidth)")>=24

            expect(page.locator('[data-world-target="selene_01_collapsed_path"]')).to_have_count(0)
            cover=page.locator('[data-covered-item="selene_01_collapsed_path"]')
            expect(cover).to_be_visible()
            assert page.locator('.maEmbeddedHotspots polygon[aria-disabled="false"]').count()==1
            output=Path("artifacts/memory-adventure/ordered-items");output.mkdir(parents=True,exist_ok=True)
            page.locator(".maScene").screenshot(path=str(output/"01-key-concealed.png"))
            gate.press("Enter")
            expect(cover).to_have_count(0,timeout=15000)
            expect(page.locator(".maSceneSubtitle")).to_contain_text("locked",timeout=15000)
            key=page.locator('[data-world-target="selene_01_collapsed_path"]')
            expect(key).to_have_attribute("aria-disabled","false",timeout=30000)
            assert page.locator('.maEmbeddedHotspots polygon[aria-disabled="false"]').count()==1
            page.locator(".maScene").screenshot(path=str(output/"02-key-unlocked.png"))
            with page.expect_response(lambda r:r.url.endswith("/act") and r.request.method=="POST") as collected:
                key.press("Enter")
            assert collected.value.status==200
            assert "ancient_key" in collected.value.json()["inventory"]
            expect(cover).to_be_visible(timeout=15000)
            expect(page.locator(".maSceneSubtitle")).to_contain_text("key",timeout=15000)
            # Chapter 2's secret is a real stone/petal prop, not an empty painted hitbox.
            audit=story_engine.fresh("alice","selene","",seed(),"en",.5)
            audit["admin_preview"]=True
            audit=story_engine.select_chapter(audit,"selene_02")
            audit["admin_preview"]=False
            audit["id"]=s["id"];audit["revision"]=100
            audit["location"]="moonflower_garden";audit["phase"]="explore"
            audit["inspected"]=["selene_02_pendant","selene_02_stone_bench","selene_02_erased_names",
                                "selene_02_follow_silhouette","selene_02_echo_trace"]
            with factory() as db:
                db.get(AppSetting,storage.run_key("alice",audit["id"])).value=json.dumps(audit)
                db.commit()
            page.reload()
            expect(page.locator(".maRoot")).to_be_visible(timeout=30000)
            expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
            petal=page.locator('[data-world-target="selene_02_moonflower"]')
            expect(petal).to_have_attribute("data-prop-asset","prop_ch02_petal_under_stone")
            expect(petal).to_have_attribute("data-hint","hidden")
            expect(petal).to_have_attribute("aria-disabled","false",timeout=15000)
            assert petal.evaluate("(el)=>getComputedStyle(el,'::after').content")=="none"
            page.locator(".maScene").screenshot(path=str(output/"03-secret-petal.png"))
            # Chapter four artifacts belong on the corridor floor, not the sky BG.
            audit=story_engine.fresh("alice","selene","",seed(),"en",.5)
            audit["admin_preview"]=True
            audit=story_engine.select_chapter(audit,"selene_04")
            audit=story_engine.advance(audit,"go","past")
            audit.update(id=s["id"],revision=200,events=[],admin_preview=False)
            with factory() as db:
                db.get(AppSetting,storage.run_key("alice",audit["id"])).value=json.dumps(audit)
                db.commit()
            page.reload()
            expect(page.locator(".maRoot")).to_have_attribute("data-chapter","selene_04",timeout=30000)
            expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
            crystal=page.locator('[data-world-target="selene_04_crystal"]')
            expect(crystal).to_have_attribute("aria-disabled","false",timeout=15000)
            scene_box=page.locator(".maScene").bounding_box()
            crystal_box=crystal.bounding_box()
            assert crystal_box["y"]>=scene_box["y"]+scene_box["height"]*.77
            assert crystal_box["width"]<=scene_box["width"]*.09
            assert crystal.locator("img").evaluate("(el)=>getComputedStyle(el).objectFit")=="contain"
            expect(page.locator('[data-prop-asset="prop_ch04_shattered_echo"]')).to_have_count(0)
            expect(page.locator('[data-prop-asset="prop_ch04_corridor_guiding_lights"]')).to_have_count(0)
            page.locator(".maScene").screenshot(path=str(output/"04-corridor-crystal.png"))
            crystal.press("Enter")
            tablet=page.locator('[data-world-target="selene_04_tablet"]')
            expect(tablet).to_have_attribute("aria-disabled","false",timeout=30000)
            assert tablet.bounding_box()["y"]>=scene_box["y"]+scene_box["height"]*.75
            page.locator(".maScene").screenshot(path=str(output/"05-corridor-tablet.png"))
            # A real admin can preview the hidden outcome without playing the arc.
            from character_chat.models import UserAccount
            with factory() as db:
                db.add(UserAccount(user_id="alice",username="preview-admin",display_name="Preview Admin",
                                   password_hash="fixture",is_admin=1,status="active"))
                audit=story_engine.fresh("alice","selene","",seed(),"en",.5)
                audit.update(id=s["id"],revision=300,admin_preview=True)
                db.get(AppSetting,storage.run_key("alice",audit["id"])).value=json.dumps(audit)
                db.commit()
            page.reload()
            ending_select=page.get_by_label("Admin preview ending",exact=True)
            expect(ending_select).to_be_visible(timeout=30000)
            expect(ending_select.locator("option")).to_have_count(5)
            ending_select.select_option("between_memory_and_moonlight")
            expect(page.locator(".maRoot")).to_have_attribute("data-chapter","selene_08",timeout=30000)
            expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
            expect(page.locator(".worldCinematic")).to_be_visible(timeout=30000)
            page.screenshot(path=str(output/"06-admin-hidden-ending-preview.png"))
            assert not voice_requests,voice_requests
            assert not errors,errors
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10)
