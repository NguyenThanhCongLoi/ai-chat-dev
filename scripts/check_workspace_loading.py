# Reproduce an expired iframe session against the built frontend.
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    checks=0
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/"frontend/dist"),**kwargs)
    def log_message(self,*args):pass
    def do_GET(self):
        path=urlparse(self.path).path
        if path.startswith("/v1/"):
            status=200;data=[]
            if path=="/v1/auth/me":
                Handler.checks+=1
                if Handler.checks==1:data={"id":"fixture-user","display_name":"Test","username":"test","language":"vi","theme":"light"}
                else:status=401;data={"detail":"Session expired"}
            self.send_response(status);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(json.dumps(data).encode());return
        if not path.startswith("/assets/"):self.path="/index.html"
        super().do_GET()
def run():
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler);Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="msedge",headless=True)
            page=browser.new_page()
            page.add_init_script("localStorage.setItem('auth_token','fixture-token');localStorage.setItem('ui_language','vi')")
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_port}/",wait_until="domcontentloaded")
            page.wait_for_selector(".platformWorkspace",timeout=10000)
            page.wait_for_selector(".platformWorkspaceLoading",state="hidden",timeout=15000)
            frames=[f for f in page.frames if "?workspace=1" in f.url]
            assert len(frames)==1
            assert frames[0].locator(".loginScene").count()>0
            assert not errors,errors
            print("PASS: expired iframe session shows login, loading overlay closes, no JavaScript errors")
            browser.close()
    finally:server.shutdown();server.server_close()
if __name__=="__main__":run()
