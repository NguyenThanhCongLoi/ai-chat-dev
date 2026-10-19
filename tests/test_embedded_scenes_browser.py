"""Opt-in desktop UI acceptance for the v2 arc using an isolated database."""
import os,socket,threading,time,json
from pathlib import Path
import pytest,uvicorn
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat import main

@pytest.mark.skipif(os.getenv("RUN_MOONFALL_BROWSER")!="1",reason="Opt-in desktop browser test")
def test_painted_scene_hit_shapes_and_collection(moonfall,monkeypatch,tmp_path):
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
        from character_chat.models import UserAccount
        import httpx
        with factory() as db:
            account=db.get(UserAccount,"alice")
            if account:account.is_admin=1
            else:db.add(UserAccount(user_id="alice",username="paint-admin",display_name="Admin",password_hash="fixture",is_admin=1,status="active"))
            db.commit()
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="msedge",headless=True)
            ctx=browser.new_context(viewport={"width":1600,"height":1000},reduced_motion="reduce")
            ctx.add_init_script("localStorage.setItem('auth_token','isolated-v2');localStorage.setItem('ui_language','en');")
            page=ctx.new_page();snapshot={};errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            def current(route):
                if route.request.method=="POST":route.fulfill(json=snapshot)
                else:route.continue_()
            page.route("**/v1/moonfall",current)
            page.route("**/v1/moonfall/*/voice/*",lambda r:r.fulfill(status=503,json={"detail":"fixture"}))
            def update(response):
                nonlocal snapshot
                if response.url.endswith("/act") and response.status==200:snapshot=response.json()
            page.on("response",update)
            with httpx.Client(base_url=f"http://127.0.0.1:{port}",timeout=60) as api:
                response=api.post("/v1/moonfall",json={"character_id":"selene","chapter_id":"selene_02","content_language":"en","preview":True})
                assert response.status_code==200,response.text
                snapshot=response.json()
                page.goto(f"http://127.0.0.1:{port}/worlds?character=selene")
                expect(page.locator(".maEmbeddedHotspots polygon")).to_have_count(2,timeout=30000)
                expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
                background=page.locator(".maBackground")
                background.evaluate("(im)=>im.decode()")
                assert "embedded_ch02_inner_ruins" in background.get_attribute("src")
                assert page.locator(".maHotspot img").count()==0
                shape=page.locator('[data-world-target="selene_02_pendant"]')
                assert shape.evaluate("(el)=>getComputedStyle(el).stroke")=="rgba(0, 0, 0, 0)"
                stage=page.locator(".maScene");stage.scroll_into_view_if_needed()
                rect=stage.bounding_box()
                # Point inside the crescent's bbox but outside its actual outline.
                blank=page.evaluate("([x,y])=>document.elementFromPoint(x,y)?.getAttribute('data-world-target')",[rect["x"]+rect["width"]*.301,rect["y"]+rect["height"]*.835])
                assert blank!="selene_02_pendant"
                page.mouse.move(rect["x"]+rect["width"]*379/1056,rect["y"]+rect["height"]*529/584)
                expect(page.locator(".maEmbeddedHint")).to_have_count(0)
                assert shape.evaluate("(el)=>getComputedStyle(el).stroke")=="rgba(0, 0, 0, 0)"
                assert shape.evaluate("(el)=>getComputedStyle(el).cursor")=="pointer"
                with page.expect_response(lambda r:r.url.endswith("/act") and r.request.method=="POST") as acted:
                    page.mouse.click(rect["x"]+rect["width"]*379/1056,rect["y"]+rect["height"]*529/584)
                assert acted.value.status==200,acted.value.text()
                expect(shape).to_have_count(0)
                expect(page.locator('[data-cleared-item="clear_selene_02_pendant"]')).to_be_visible()
                expect(page.locator('[data-world-target="selene_02_moonflower"]')).to_have_count(1)
                page.reload()
                expect(page.locator('[data-cleared-item="clear_selene_02_pendant"]')).to_be_visible(timeout=30000)
                page.locator(".maBackground").evaluate("(im)=>im.decode()")
                for im in page.locator(".maCleanPatch").all():im.evaluate("(el)=>el.decode()")
                output=Path("artifacts/memory-adventure/embedded-bg")
                page.locator(".maScene").screenshot(path=str(output/"browser-collected.png"),animations="disabled")
                response=api.post("/v1/moonfall",json={"character_id":"selene","chapter_id":"selene_05","content_language":"en","preview":True})
                assert response.status_code==200,response.text
                snapshot=response.json()
                page.goto(f"http://127.0.0.1:{port}/worlds?character=selene")
                expect(page.locator(".maEmbeddedHotspots polygon")).to_have_count(3,timeout=30000)
                expect(page.locator(".maPreparation")).to_have_count(0,timeout=90000)
                for ident in ["selene_05_ink","selene_05_seal","selene_05_timestamp"]:
                    target=page.locator('[data-world-target="'+ident+'"]')
                    target.focus()
                    with page.expect_response(lambda r:r.url.endswith("/act") and r.request.method=="POST") as acted:
                        target.press("Enter")
                    assert acted.value.status==200,acted.value.text()
                    if ident!="selene_05_timestamp":
                        expect(page.locator('[data-cleared-item="clear_selene_05_ink"]')).to_have_count(0)
                expect(page.locator(".maEmbeddedHotspots polygon")).to_have_count(0)
                expect(page.locator('[data-cleared-item="clear_selene_05_ink"]')).to_be_visible()
            assert not errors,errors
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10)
