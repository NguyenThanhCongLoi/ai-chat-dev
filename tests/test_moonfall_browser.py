"""Opt-in local browser acceptance: isolated DB and mock providers, never production data.
Run after frontend build: RUN_MOONFALL_BROWSER=1 DATABASE_URL=sqlite:// pytest ...
"""
import json
import os
import re
import socket
import threading
import time
from pathlib import Path
import pytest
import uvicorn
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat import main
from character_chat.models import AppSetting,UserProfile,Room,RoomMember,Message,Memory,Character
from character_chat.schemas import CharacterSpec

@pytest.mark.skipif(os.getenv("RUN_MOONFALL_BROWSER")!="1",reason="Opt-in browser acceptance")
def test_chapter_one_browser(moonfall,monkeypatch,tmp_path):
    from playwright.sync_api import sync_playwright,expect
    client,old_factory,_=moonfall
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from character_chat.models import Base
    # Browser requests run concurrently: use separate SQLite connections, not StaticPool.
    file_engine=create_engine("sqlite:///"+str(tmp_path/"browser.sqlite"),connect_args={"check_same_thread":False})
    Base.metadata.create_all(file_engine)
    with old_factory.kw["bind"].connect() as src,file_engine.begin() as dst:
        for table in Base.metadata.sorted_tables:
            rows=[dict(r) for r in src.execute(table.select()).mappings()]
            if rows:dst.execute(table.insert(),rows)
    factory=sessionmaker(file_engine,expire_on_commit=False)
    def dependency():
        with factory() as db:yield db
    main.app.dependency_overrides[main.db_session]=dependency
    monkeypatch.setattr(main,"Session",factory)
    output=Path("artifacts/moonfall-acceptance");output.mkdir(parents=True,exist_ok=True)
    monkeypatch.setenv("FRONTEND_DIST",str(Path("frontend/dist").resolve()))
    names=["Liost","Nguyễn Vũ","Merr","Ruby","Kim Anh","Trịnh Khải Nguyên","Aurelion Voss",
           "Selene Moonbrook","Mira Sunpetal","Ren Quickshade","Lyra Ashveil"]
    monkeypatch.setattr(main,"effective_presets",lambda db:[CharacterSpec(id="public-"+str(i),preset_type="public-"+str(i),name=n) for i,n in enumerate(names)])
    captured=[]
    def dialogue(*args,**kw):
        captured.append(str(args))
        return "I can see the weathered marks here. Let us keep looking together."
    monkeypatch.setattr(main,"direct_completion",dialogue)
    def stream(prompt,*args):
        captured.append(str(prompt))
        known="newly awakened runes at Moonfall" in str(prompt)
        yield "delta",("I remember exploring the newly awakened runes at Moonfall with you. We noticed that I knew more about those ruins than I first admitted." if known else "The old ruins have been on my mind. Would you like to walk there with me?")
        yield "complete",{"finish_status":"complete","actual_model":"mock"}
    monkeypatch.setattr(main,"stream_roleplay_answer",stream)
    monkeypatch.setattr(main.llm,"chat_with_meta",lambda *a,**k:('{"suggestions":[]}',{}))
    with factory() as db:
        cfg=json.loads(db.get(AppSetting,"moonfall_story_config").value)
        cfg["entry_gate"]["min_meaningful_turns"]=2
        db.get(AppSetting,"moonfall_story_config").value=json.dumps(cfg)
        db.add(UserProfile(user_id="alice",language="vi"))
        card=CharacterSpec.model_validate_json(db.get(Character,"selene").spec)
        card.description="A moon elf scholar with curiosity, composure and a dry sense of humor."
        card.avatar_url=None
        db.get(Character,"selene").spec=card.model_dump_json()
        db.add(Room(id="browser-solo",user_id="alice",name="Selene"))
        db.add(RoomMember(id="browser-member",room_id="browser-solo",character_id="selene"))
        db.add(Message(id="browser-greeting",room_id="browser-solo",sender_type="character",character_id="selene",text="I have been thinking about the old ruins."))
        db.commit()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(main.app,host="127.0.0.1",port=port,log_level="warning",lifespan="off"))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    base="http://127.0.0.1:"+str(port)
    for _ in range(100):
        if server.started:break
        time.sleep(.05)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="msedge",headless=True)
            context=browser.new_context(viewport={"width":1440,"height":1000})
            context.add_init_script("localStorage.setItem('auth_token','isolated-browser-fixture');if(!localStorage.getItem('ui_language'))localStorage.setItem('ui_language','vi');")
            page=context.new_page();errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            # Localization provider is outside this story acceptance test.
            def translations(route):
                data=route.request.post_data_json or {}
                route.fulfill(json={"translations":["Một người bạn đồng hành, tò mò và điềm tĩnh." for _ in data.get("texts",[])],"failures":[]})
            page.route("**/v1/i18n/translate",translations)
            import io,wave
            chapter_sound=io.BytesIO()
            with wave.open(chapter_sound,"wb") as w:
                w.setnchannels(1);w.setsampwidth(1);w.setframerate(8000);w.writeframes(bytes([128])*32000)
            chapter_requests=[]
            def chapter_voice(route):
                chapter_requests.append(route.request.url.rsplit("/",1)[-1])
                route.fulfill(body=chapter_sound.getvalue(),content_type="audio/wav")
            page.route("**/v1/moonfall/*/voice/*",chapter_voice)
            page.goto(base+"/role-play-ai?workspace=1&view=chat&room=browser-solo",wait_until="domcontentloaded")
            entry=page.locator(".mfStoryToggle")
            try:expect(entry).to_be_visible(timeout=20000)
            except Exception:
                page.screenshot(path=str(output/"failure.png"));(output/"failure.txt").write_text(page.locator("body").inner_text(),encoding="utf8");raise
            entry.scroll_into_view_if_needed()
            assert page.locator(".chat > .mfChatHook").count()==0
            expect(page.locator(".characterTools .mfStoryToggle")).to_be_visible()
            box=page.locator(".mfChatHook").bounding_box()
            assert box and box["height"]<240 and box["width"]>180
            page.screenshot(path=str(output/"01-chat-invitation.png"))
            entry.click()
            expect(page.locator(".mfChapterRow")).to_have_count(8)
            expect(page.locator(".mfChapterLocked:disabled")).to_have_count(8)
            page.screenshot(path=str(output/"01b-locked-chapters.png"))
            page.evaluate("window.unlockSeen=false;new MutationObserver(()=>{if(document.querySelector('.mfChapterJustUnlocked'))window.unlockSeen=true}).observe(document.body,{subtree:true,attributes:true,childList:true})")
            with factory() as db:
                cfg=json.loads(db.get(AppSetting,"moonfall_story_config").value)
                cfg["entry_gate"]["min_meaningful_turns"]=0
                db.get(AppSetting,"moonfall_story_config").value=json.dumps(cfg);db.commit()
            page.locator(".mfChapterRefresh").click()
            expect(page.locator(".mfChapterAvailable")).to_have_count(1)
            assert page.evaluate("window.unlockSeen")
            expect(page.locator(".mfChapterLocked:disabled")).to_have_count(7)
            page.screenshot(path=str(output/"01c-unlocked-chapters.png"))
            page.keyboard.press("Escape")
            entry.click()
            expect(page.locator(".mfChapterAvailable")).to_have_count(1)
            assert page.locator(".mfChapterJustUnlocked").count()==0
            page.evaluate("localStorage.setItem(\"ui_language\",\"en\")")
            page.locator(".mfChatHook a").click()
            page.wait_for_url("**/worlds?character=selene&chapter=selene_01")
            try:expect(page.get_by_role("main",name="Moonfall introduction")).to_be_visible(timeout=15000)
            except Exception:
                page.screenshot(path=str(output/"failure.png"))
                (output/"failure.txt").write_text(page.url+"\n"+page.locator("body").inner_text()+"\n"+str(errors),encoding="utf8")
                raise
            expect(page.locator(".worldCinematic video")).to_have_js_property("videoWidth",1280,timeout=10000)
            page.screenshot(path=str(output/"02-cold-open.png"))
            page.get_by_role("button",name="Listen to narration").click()
            expect(page.locator(".mfIntroNarration .mfListen")).to_have_text("■")
            assert len(chapter_requests)==1
            page.get_by_role("button",name="Skip introduction").click()
            speech=page.locator('[data-output-type="CHARACTER_SPEECH"]').first
            speech.locator(".mfListen").click()
            assert len(chapter_requests)==1  # Queued; must not interrupt the narrator.
            expect(speech).to_have_class(re.compile("mfLinePlaying"),timeout=10000)
            assert len(chapter_requests)==2 and chapter_requests[0]!=chapter_requests[1]
            expect(speech.locator("q")).to_be_visible()
            speech.locator(".mfListen").click()
            expect(page.locator('[data-output-type="CHARACTER_THOUGHT"]').first).to_be_visible()
            assert page.locator('[data-output-type="CHARACTER_THOUGHT"] .mfListen').count()==0
            page.get_by_role("button",name="Walk toward the ruins").click()
            expect(page.locator(".mfHotspot")).to_have_count(2)
            page.evaluate("window.worldObserved=[];new MutationObserver(ms=>{for(const m of ms)for(const n of m.addedNodes)if(n.nodeType===1){if(n.dataset.effect)window.worldObserved.push(n.dataset.effect);for(const el of n.querySelectorAll('[data-effect]'))window.worldObserved.push(el.dataset.effect)}}).observe(document.body,{childList:true,subtree:true})")
            page.locator('.mfHotspot[data-world-target="rune"]').click()
            expect(page.locator(".mfHotspot.mfFound")).to_have_count(1)
            assert "RUNE_GLOW" in page.evaluate("window.worldObserved")
            page.screenshot(path=str(output/"03-rune-and-reaction.png"))
            page.get_by_role("textbox",name="Talk freely with Selene").fill("These runes are unlike anything I have seen. What do you make of their light?")
            page.get_by_role("button",name="Send to Selene").click()
            expect(page.get_by_text("I can see the weathered marks here.",exact=False)).to_be_visible()
            page.locator('.mfHotspot[data-world-target="statue"]').click()
            expect(page.get_by_role("button",name="What you carry together")).to_be_visible()
            if not page.get_by_role("dialog",name="Chapter memory").is_visible():
                page.get_by_role("button",name="What you carry together").click()
            expect(page.get_by_role("dialog",name="Chapter memory")).to_be_visible()
            page.screenshot(path=str(output/"04-chapter-memory.png"))
            expect(page.get_by_role("checkbox",name="Let Selene remember this in normal chat")).to_be_checked()
            page.get_by_role("button",name="Talk to Selene about what happened").click()
            page.wait_for_url("**/role-play-ai?workspace=1&view=chat&room=browser-solo")
            with factory() as db:
                shared=db.query(Memory).filter_by(type="world_shared").all()
                assert len(shared)==1
                assert shared[0].user_id=="alice" and shared[0].character_id=="selene"
            # Exercise actual normal chat SSE route after return and inspect its prompt.
            response=context.request.post(base+"/v1/rooms/browser-solo/messages/stream",data={"message":"What do you remember about our visit to Moonfall?"},timeout=15000)
            assert response.status==200,response.text()
            assert "newly awakened runes at Moonfall" in response.text()
            assert any("explicitly" in prompt and "newly awakened runes at Moonfall" in prompt for prompt in captured)
            routes=[(r.path,sorted(r.methods or [])) for r in main.app.routes if "stream" in r.path]
            (output/"routes.json").write_text(json.dumps(routes),encoding="utf8")
            expect(page.locator(".mfStoryToggle")).to_be_visible(timeout=20000)
            page.screenshot(path=str(output/"05-return-to-chat.png"))
            # Resume preserves completion; historical VFX must not replay.
            page.locator(".mfStoryToggle").click()
            page.locator(".mfChatHook a").click()
            expect(page.get_by_role("button",name="What you carry together")).to_be_visible()
            assert page.locator(".worldEffect").count()==0
            assert page.locator('[data-cinematic="moonfall_intro"]').count()==0
            page.get_by_role("button",name="What you carry together").click()
            page.keyboard.press("Escape")
            expect(page.get_by_role("dialog",name="Chapter memory")).not_to_be_visible()
            # Optional video failure does not affect chapter completion or persisted memory.
            page.route("**/v1/moonfall/assets/memory_space_video",lambda route:route.abort())
            page.get_by_role("button",name="What you carry together").click()
            expect(page.locator(".worldCinematicFallback")).to_be_visible()
            page.keyboard.press("Escape")
            page.emulate_media(reduced_motion="reduce")
            page.get_by_role("button",name="What you carry together").click()
            assert page.locator(".worldCinematic video").count()==0
            page.keyboard.press("Escape")
            # Audio is mocked; exercise synchronized playback without a paid provider.
            import io,wave
            sound=io.BytesIO()
            with wave.open(sound,"wb") as w:
                w.setnchannels(1);w.setsampwidth(1);w.setframerate(8000);w.writeframes(bytes([128])*64000)
            page.route("**/v1/moonfall/hub/narration/*",lambda route:route.fulfill(body=sound.getvalue(),content_type="audio/wav"))
            # Home entry plays the general intro, then the same chapter picker.
            page.emulate_media(reduced_motion="no-preference")
            page.goto(base+"/worlds",wait_until="domcontentloaded")
            expect(page.locator(".whCinema video")).to_have_js_property("videoWidth",1280,timeout=15000)
            expect(page.locator(".whCinema video")).to_have_js_property("muted",False)
            level=page.get_by_role("slider",name="Intro volume")
            level.focus();level.press("Home")
            for _ in range(20):level.press("ArrowRight")
            page.wait_for_function("Math.abs(document.querySelector('.whCinema video').volume-.09)<.001")
            page.locator(".whCinema video").evaluate("(v)=>{v.currentTime=9;v.dispatchEvent(new Event('timeupdate'));}")
            expect(page.locator(".whSubtitles")).to_contain_text("Some encounters")
            page.wait_for_function("Math.abs(document.querySelector('.whCinema video').volume-.028)<.001")
            page.screenshot(path=str(output/"06-home-intro.png"))
            page.get_by_role("button",name="Skip intro",exact=False).click()
            expect(page.locator(".whActor")).to_have_count(11)
            expect(page.locator(".whLocked:disabled")).to_have_count(10)
            expect(page.locator("video[data-world-intro]")).to_have_js_property("paused",True)
            page.screenshot(path=str(output/"07-memory-atlas.png"),animations="disabled")
            page.get_by_role("button",name="Selene Moonbrook",exact=False).click()
            expect(page.locator(".mfChapterRow")).to_have_count(8)
            expect(page.locator(".mfChapterAvailable")).to_have_count(1)
            page.locator(".mfChapterAvailable").click()
            expect(page.locator(".mfRoot")).to_be_visible()
            assert page.locator(".whCinema").count()==0
            page.get_by_role("button",name="Back to Chat",exact=False).click()
            expect(page.locator(".whAtlas")).to_be_visible()
            page.get_by_role("button",name="Replay intro").click()
            expect(page.locator(".whCinema video")).to_be_visible()
            page.locator(".whCinema video").evaluate("(v)=>v.dispatchEvent(new Event('ended'))")
            expect(page.locator(".whAtlas")).to_be_visible()
            # All seven locale titles are authored copy; Vietnamese uses one serif family.
            for locale,title in [("vi","Miền ký ức"),("en","The Memory Atlas"),("zh","记忆之境"),("ja","記憶の世界"),("ko","기억의 세계"),("my","အမှတ်တရတို့ရဲ့ နယ်မြေ"),("km","ដែនអនុស្សាវរីយ៍")]:
                page.evaluate("(lang)=>localStorage.setItem('ui_language',lang)",locale)
                page.reload(wait_until="domcontentloaded")
                page.locator(".whCinemaControls button").click()
                expect(page.locator(".whTitle h1")).to_have_text(title)
                if locale=="vi":
                    page.screenshot(path=str(output/"08-vietnamese-title.png"),animations="disabled")
            page.evaluate("localStorage.setItem('ui_language','en')")
            # A media failure also goes to the atlas without unlocking or erasing a run.
            page.route("**/v1/moonfall/hub/assets/world_intro_*",lambda route:route.abort())
            page.reload(wait_until="domcontentloaded")
            expect(page.locator(".whAtlas")).to_be_visible(timeout=10000)
            assert not errors,errors
            (output/"result.json").write_text(json.dumps({"browser":"Edge headless","chapter_completed":True,"memory_shared":True,"runtime_errors":errors,"provider":"mock; no external calls"},indent=2),encoding="utf8")
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10)
