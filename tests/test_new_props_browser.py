"""Opt-in desktop UI acceptance for the v2 arc using an isolated database."""
import os,socket,threading,time,json
from pathlib import Path
import pytest,uvicorn
from test_worlds import world_client
from test_moonfall import moonfall
from character_chat import main

@pytest.mark.skipif(os.getenv("RUN_MOONFALL_BROWSER")!="1",reason="Opt-in desktop browser test")
def test_replacement_props_all_scenes(moonfall,monkeypatch,tmp_path):
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
    output=Path("artifacts/memory-adventure/new-props-scenes");output.mkdir(parents=True,exist_ok=True)
    try:
        from character_chat.models import UserAccount
        from character_chat.adventure.loader import seed
        from character_chat.adventure.props import DATA
        import httpx
        with factory() as db:
            account=db.get(UserAccount,"alice")
            if account:account.is_admin=1
            else:db.add(UserAccount(user_id="alice",username="props-admin",display_name="Admin",password_hash="fixture",is_admin=1,status="active"))
            db.commit()
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="msedge",headless=True)
            ctx=browser.new_context(viewport={"width":1600,"height":1000},reduced_motion="reduce")
            ctx.add_init_script("localStorage.setItem('auth_token','isolated-v2');localStorage.setItem('ui_language','en');")
            page=ctx.new_page();snapshot={};errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            def current_run(route):
                if route.request.method=="POST":route.fulfill(json=snapshot)
                else:route.continue_()
            page.route("**/v1/moonfall",current_run)
            page.route("**/v1/moonfall/*/voice/*",lambda r:r.fulfill(status=503,json={"detail":"fixture"}))
            with httpx.Client(base_url=f"http://127.0.0.1:{port}",timeout=60) as api:
                for ch in seed()["chapters"]:
                    response=api.post("/v1/moonfall",json={"character_id":"selene","chapter_id":ch["id"],"content_language":"en","preview":True})
                    assert response.status_code==200,response.text
                    snapshot=response.json()
                    def step(action,value=""):
                        nonlocal snapshot
                        response=api.post("/v1/moonfall/"+snapshot["id"]+"/act",json={"revision":snapshot["revision"],"request_id":"props-"+str(snapshot["revision"]),"action":action,"value":value})
                        assert response.status_code==200,response.text
                        snapshot=response.json()
                    if snapshot["phase"]=="intro":step("intro_complete")
                    for scene in ch["scenes"]:
                        if snapshot["location"]!=scene["id"]:step("go",scene["id"])
                        page.goto(f"http://127.0.0.1:{port}/worlds?character=selene&chapter="+ch["id"])
                        expect(page.locator(".maScene")).to_be_visible(timeout=30000)
                        for img in page.locator(".maScene img").all():
                            img.evaluate("(im)=>im.decode()")
                            assert img.evaluate("(im)=>im.naturalWidth>0")
                        stage=page.locator(".maScene")
                        background=page.locator(".maBackground")
                        size=background.evaluate("im=>[im.naturalWidth,im.naturalHeight]")
                        rect=stage.bounding_box()
                        assert abs(rect["width"]/rect["height"]-size[0]/size[1])<.01
                        for obj in snapshot["objects"]:
                            button=page.locator('[data-world-target="'+obj["id"]+'"]')
                            if obj["mode"]=="embedded":
                                assert button.get_attribute("data-prop-mode")=="embedded"
                                assert button.get_attribute("points")
                                assert obj["asset"]==""
                            else:
                                assert button.get_attribute("data-prop-asset")==obj["asset"]
                                for key in ("x","y","width","height"):
                                    assert obj[key]==DATA["hotspots"][obj["id"]][key]
                            if obj["mode"]=="table":assert button.locator("img").evaluate("im=>getComputedStyle(im).transform")=="none"
                        stage.screenshot(path=str(output/(ch["id"]+"-"+scene["id"]+".png")))
            assert not errors,errors
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10)
