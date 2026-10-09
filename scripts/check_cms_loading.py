"""Verify that hidden CMS log/database panels do not load on startup."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    calls=[]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT/"frontend/dist"),**kwargs)
    def log_message(self,*args):pass
    def do_GET(self):
        path=urlparse(self.path).path
        if path.startswith("/v1/"):
            Handler.calls.append(path)
            data={
                "/v1/admin/overview":{"stats":{},"characters":[],"rooms":[],"documents":[],"ai_activity":[]},
                "/v1/admin/settings":{"_base_prompts":{"response":"","suggestion":"","compiler":""}},
                "/v1/admin/access-control":{"accounts":[]},
                "/v1/admin/characters":{"preset_catalog":[],"user_characters":[]},
                "/v1/admin/models":[],
                "/v1/admin/credentials":{"avibi":{"configured":False,"source":"missing","hint":""}},
                "/v1/admin/database":[{"name":"users","rows":0,"columns":["id"]}],
                "/v1/admin/database/users":{"rows":[],"columns":["id"],"total":0},
            }.get(path,[])
            self.send_response(200);self.send_header("Content-Type","application/json")
            self.end_headers();self.wfile.write(json.dumps(data).encode());return
        if path=="/admin":self.path="/admin.html"
        super().do_GET()
def run():
    Handler.calls=[]
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="msedge",headless=True)
            page=browser.new_page(viewport=dict(width=1440,height=1100))
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.route("**/*",lambda route:route.continue_() if route.request.url.startswith("http://127.0.0.1:") else route.abort())
            page.goto(f"http://127.0.0.1:{server.server_port}/admin",wait_until="networkidle")
            page.wait_for_selector("#dashboard .kpi")
            forbidden=("/v1/admin/database","/v1/admin/action-logs","/v1/admin/voice-logs","/v1/admin/assistant-profiles")
            assert not any(path.startswith(forbidden) for path in Handler.calls),Handler.calls
            page.locator('[data-view="database"]').click()
            page.wait_for_selector("#db-count")
            page.wait_for_function("document.querySelector('#db-count').textContent.includes('0')")
            assert "/v1/admin/database/users" in Handler.calls
            assert not errors,errors
            print("PASS: CMS startup skips hidden logs/database; Database loads on selection; no JavaScript errors")
            browser.close()
    finally:
        server.shutdown();server.server_close()
if __name__=="__main__":run()
