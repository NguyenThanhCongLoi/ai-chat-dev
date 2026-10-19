"""Opt-in desktop UI acceptance for the v2 arc using an isolated database."""
import os,socket,threading,time,json
from pathlib import Path
import pytest,uvicorn
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat import main

@pytest.mark.skipif(os.getenv("RUN_MOONFALL_BROWSER")!="1",reason="Opt-in desktop browser test")
def test_adventure_desktop(moonfall,monkeypatch,tmp_path):
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
    output=Path("artifacts/memory-adventure");output.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="msedge",headless=True)
            context=browser.new_context(viewport={"width":1600,"height":1000},reduced_motion="reduce")
            context.add_init_script("localStorage.setItem('auth_token','isolated-v2');localStorage.setItem('ui_language','en');")
            page=context.new_page();errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            voice_requests=[]
            def mock_voice(route):
                voice_requests.append(route.request.url.rsplit("/",1)[-1])
                route.fulfill(status=503,json={"detail":"Voice not configured in test"})
            page.route("**/v1/moonfall/*/voice/*",mock_voice)
            page.goto(f"http://127.0.0.1:{port}/worlds?character=selene")
            expect(page.locator(".maRoot")).to_be_visible(timeout=20000)
            expect(page.locator(".memoryLocationEffects")).to_have_attribute("data-effect-profile","1")
            expect(page.locator(".maHotspot")).not_to_have_count(0)
            page.screenshot(path=str(output/"chapter-01-desktop.png"),full_page=True)
            # Narrator is opt-in while character dialogue remains automatic.
            narration=page.locator('.maTypeNARRATION').first
            narration_id=narration.get_attribute("data-world-target").removeprefix("event:")
            assert narration_id not in voice_requests
            narration.locator("button").click()
            page.wait_for_function("()=>!document.querySelector('.maConversation textarea').readOnly")
            assert narration_id in voice_requests
            page.locator('select[aria-label="Text language"]').select_option("ja")
            expect(page.locator('.maRoot')).to_have_attribute("lang","ja")
            expect(page.locator('.maTranscript article button')).to_have_count(0)
            expect(page.locator('.maAudioSettings select')).to_have_count(1)
            assert any(ord(c)>0x3000 for c in page.locator('.maChapter h1').inner_text())
            page.locator('.maAudioSettings select').select_option("en")
            expect(page.locator('.maRoot')).to_have_attribute("lang","en")
            expect(page.locator('.maTypeNARRATION button').first).to_be_visible()
            # Enter sends once, Shift+Enter/IME preserve composition, and typing is visible.
            held_chat=[];sent=[]
            def hold_chat(route):
                payload=route.request.post_data_json
                sent.append(payload)
                if payload.get("action")=="say":held_chat.append(route)
                else:route.continue_()
            page.route("**/v1/moonfall/*/act",hold_chat)
            composer=page.locator(".maConversation textarea")
            composer.fill("Can we talk?")
            composer.press("Shift+Enter")
            expect(composer).to_have_value("Can we talk?\n")
            assert not sent
            composer.evaluate("(el)=>el.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',isComposing:true,bubbles:true,cancelable:true}))")
            assert not sent
            composer.press("Enter")
            expect(page.locator(".maThinking")).to_be_visible()
            expect(page.locator(".maTypeUSER").last).to_contain_text("Can we talk?")
            composer.press("Enter")
            assert len(held_chat)==1
            route=held_chat.pop()
            route.fulfill(response=route.fetch())
            expect(page.locator(".maThinking")).to_have_count(0,timeout=15000)
            expect(composer).to_have_value("")
            assert sum(x["action"]=="say" for x in sent)==1
            # A second click on a found hotspot makes no request or new speech event.
            button=page.locator(".maHotspot").first
            button.click()
            expect(button).to_have_class(__import__("re").compile("maFound"))
            count=len(sent);events=page.locator(".maEvent").count()
            button.dispatch_event("click")
            page.wait_for_timeout(150)
            assert len(sent)==count and page.locator(".maEvent").count()==events
            assert button.evaluate("(b)=>getComputedStyle(b).borderTopWidth")=="0px"
            page.screenshot(path=str(output/"chapter-chat-items.png"),full_page=True)
            for button in page.locator(".maHotspot").all():
                if "maFound" in button.get_attribute("class"):continue
                button.click()
                expect(button).to_have_class(__import__("re").compile("maFound"))
            place=page.locator(".maTools button").nth(1)
            place.click()
            expect(place).to_have_attribute("aria-current","location")
            for button in page.locator(".maHotspot").all():
                if "maFound" in button.get_attribute("class"):continue
                button.click();expect(button).to_have_class(__import__("re").compile("maFound"))
            with factory() as db:
                from character_chat import moonfall_store
                run=moonfall_store.user_runs(db,"alice")[0]
            puzzle=run["config"]["chapters"][0]["puzzles"][0]
            # Runtime UI exposes options, not solutions. Test fixture knows authored answers.
            for ident in puzzle["solution"]:
                label=next(o["label"]["en"] for o in puzzle["options"] if o["id"]==ident)
                page.locator(".maTokens").get_by_role("button",name=label).click()
            page.locator(".maPuzzle").get_by_role("button",name="Check").click()
            expect(page.locator(".maChoices button")).to_have_count(3)
            # Narration is opt-in even over video; skipping stops manual audio
            # immediately and performs one persisted transition, with no Continue button.
            import io,wave
            cue_audio=io.BytesIO()
            with wave.open(cue_audio,"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(1);wav.setframerate(8000);wav.writeframes(bytes([128])*64000)
            page.locator(".maAudioSettings button").click()
            voice_ids=[]
            def voice_cue(route):
                voice_ids.append(route.request.url.rsplit("/",1)[-1])
                route.fulfill(body=cue_audio.getvalue(),content_type="audio/wav")
            page.route("**/v1/moonfall/*/voice/*",voice_cue)
            page.evaluate("window.__chapterAudios=[];const OriginalAudio=window.Audio;window.Audio=function(...args){const a=new OriginalAudio(...args);window.__chapterAudios.push(a);return a;}")
            page.emulate_media(reduced_motion="no-preference")
            page.locator(".maChoices button").nth(1).click()
            clip=page.locator('[data-cinematic="memory_video_01"] video')
            expect(clip).to_be_visible(timeout=15000)
            assert clip.evaluate("(v)=>v.src.startsWith('blob:')")
            assert not voice_ids
            page.locator(".maCinematicNarration button").click()
            page.wait_for_function("window.__chapterAudios.some(a=>!a.paused)")
            narrator=page.evaluate_handle("window.__chapterAudios.find(a=>!a.paused)")
            with factory() as db:
                current=moonfall_store.user_runs(db,"alice")[0]
                assert all(next(e for e in current["events"] if e["id"]==ident)["type"]=="NARRATION" for ident in voice_ids)
            expect(page.locator(".maConversation form button")).to_be_disabled()
            page.get_by_role("button",name="Skip cinematic",exact=False).click()
            assert narrator.evaluate("(a)=>a.paused")
            expect(page.get_by_role("button",name="Continue memory")).to_have_count(0)
            expect(page.locator(".maCompletion")).to_be_visible(timeout=10000)
            page.screenshot(path=str(output/"chapter-01-complete.png"),full_page=True)
            page.get_by_role("button",name="View recovered memories").click()
            expect(page.locator("dialog[open]")).to_be_visible()
            page.screenshot(path=str(output/"archive.png"),full_page=True)
            page.locator(".maClose").click()
            page.emulate_media(reduced_motion="no-preference")
            before=page.locator(".memoryLocationEffects").evaluate("(c)=>c.toDataURL()")
            page.wait_for_timeout(350)
            after=page.locator(".memoryLocationEffects").evaluate("(c)=>c.toDataURL()")
            assert before!=after
            page.goto(f"http://127.0.0.1:{port}/worlds/admin")
            expect(page.get_by_role("heading",name="Echoes of Moonfall · 8 chương")).to_be_visible()
            page.locator(".mfCmsBody textarea").first.fill("World title updated in test")
            with page.expect_request(lambda r:r.method=="PUT" and r.url.endswith("/v1/admin/moonfall")) as saved:
                page.get_by_role("button",name="Lưu cấu hình World",exact=True).click()
            assert not saved.value.headers.get("authorization","").startswith("Bearer ")
            expect(page.get_by_role("status")).to_contain_text("Đã lưu phiên bản")
            page.get_by_role("button",name="8 chương",exact=True).click()
            expect(page.locator(".mfCmsChapters button")).to_have_count(8)
            page.locator(".mfCmsChapters button").nth(7).click()
            expect(page.get_by_role("heading",name="selene_08")).to_be_visible()
            page.screenshot(path=str(output/"cms-chapter-08.png"),full_page=True)
            # The intro remains paused until downloaded video AND every voice cue are prepared.
            import io,wave
            sound=io.BytesIO()
            with wave.open(sound,"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(1);wav.setframerate(8000);wav.writeframes(bytes([128])*8000)
            page.route("**/v1/moonfall/hub/narration/*",lambda route:route.fulfill(body=sound.getvalue(),content_type="audio/wav"))
            page.route("**/v1/moonfall/hub/assets/selene_intro_1080",lambda route:route.fulfill(path=str(Path("image/worlds/selene/moonfall/video/memories/memory_01.webm").resolve()),content_type="video/webm"))
            page.emulate_media(reduced_motion="reduce")
            page.goto(f"http://127.0.0.1:{port}/worlds")
            expect(page.get_by_role("button",name="Play intro with sound")).to_be_visible(timeout=15000)
            assert page.locator("video[data-world-intro]").evaluate("(v)=>v.paused&&v.src.startsWith('blob:')")
            page.get_by_role("button",name="Skip intro").click()
            expect(page.locator(".whAtlas")).to_be_visible()
            assert page.locator(".whHeader .mfSound button").first.get_attribute("aria-pressed")=="true"
            # Home keeps the existing loading-cat theme while the intro download is pending.
            page.route("**/v1/auth/me",lambda route:route.fulfill(json={"id":"alice","username":"fixture","display_name":"Fixture","theme":"dark","language":"en"}))
            held=[]
            page.route("**/v1/moonfall/hub/assets/selene_intro_1080",lambda route:held.append(route))
            with page.expect_request(lambda r:r.url.endswith("/v1/moonfall/hub/assets/selene_intro_1080")):
                page.goto(f"http://127.0.0.1:{port}/avibi-platform",wait_until="domcontentloaded")
            expect(page.locator(".assistantGate .roleplayLoadingCat")).to_be_visible()
            expect(page.locator(".platformWorkspace")).to_have_count(0)
            assert held
            expect(page.locator(".homePreparationProgress progress")).to_be_visible()
            value=float(page.locator(".homePreparationProgress progress").get_attribute("value"))
            assert 0<=value<100
            for route in held:
                route.fulfill(path=str(Path("image/worlds/selene/moonfall/video/memories/memory_01.webm").resolve()),content_type="video/webm")
            expect(page.locator(".platformWorkspace")).to_be_visible(timeout=15000)
            expect(page.locator(".assistantGate")).to_have_count(0)
            page.screenshot(path=str(output/"home-ready.png"),full_page=True)
            # Review the actual composition for every scene in all eight chapters.
            from character_chat.models import UserAccount
            import httpx
            with factory() as db:
                account=db.get(UserAccount,"alice")
                if account:account.is_admin=1
                else:db.add(UserAccount(user_id="alice",username="props-review",display_name="Admin",password_hash="fixture",is_admin=1,status="active"))
                db.commit()
            snapshot={}
            def preview_snapshot(route):
                if route.request.method=="POST":route.fulfill(json=snapshot)
                else:route.continue_()
            page.route("**/v1/moonfall",preview_snapshot)
            page.route("**/v1/moonfall/*/voice/*",lambda r:r.fulfill(status=503,json={"detail":"fixture"}))
            page.emulate_media(reduced_motion="reduce")
            from character_chat.adventure.loader import seed
            with httpx.Client(base_url=f"http://127.0.0.1:{port}",timeout=30) as review:
                for ch in seed()["chapters"]:
                    result=review.post("/v1/moonfall",json={"character_id":"selene","chapter_id":ch["id"],"content_language":"en"})
                    assert result.status_code==200,result.text
                    snapshot=result.json()
                    def step(action,value=""):
                        nonlocal snapshot
                        response=review.post("/v1/moonfall/"+snapshot["id"]+"/act",json={"revision":snapshot["revision"],"request_id":"review-"+str(snapshot["revision"]),"action":action,"value":value})
                        assert response.status_code==200,response.text
                        snapshot=response.json()
                    if snapshot["phase"]=="intro":step("intro_complete")
                    for scene in ch["scenes"]:
                        if snapshot["location"]!=scene["id"]:step("go",scene["id"])
                        page.goto(f"http://127.0.0.1:{port}/worlds?character=selene&chapter="+ch["id"])
                        expect(page.locator(".maScene")).to_be_visible(timeout=15000)
                        for img in page.locator(".maHotspot img").all():
                            img.evaluate("(im)=>im.decode().catch(()=>{})")
                            assert img.evaluate("(im)=>im.complete&&im.naturalWidth>0")
                        page.locator(".maScene").screenshot(path=str(output/("props-"+ch["id"]+"-"+scene["id"]+".png")))
            assert not errors,errors
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10)
