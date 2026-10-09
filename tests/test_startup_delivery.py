import asyncio
from starlette.requests import Request
from starlette.responses import Response
import character_chat.main as main

def request(path):
    return Request({"type":"http","method":"GET","path":path,"headers":[],"query_string":b"","scheme":"http","server":("test",80),"client":("test",1)})

def test_fingerprinted_assets_are_cached_but_named_assets_revalidate(monkeypatch):
    monkeypatch.setattr(main,"write_audit_event",lambda **kwargs:None)
    async def next_response(req):
        return Response("asset")
    for path,expected in [
        ("/assets/app-DKUPMAd-.js","public, max-age=31536000, immutable"),
        ("/assets/loading-cat-walk-sprite.webp","public, max-age=0, must-revalidate"),
        ("/","no-store, no-cache, must-revalidate, max-age=0"),
    ]:
        response=asyncio.run(main.disable_stale_frontend_cache(request(path),next_response))
        assert response.headers["cache-control"]==expected

def test_audit_runs_after_response_and_preserves_existing_background(monkeypatch):
    from starlette.background import BackgroundTask
    events=[]
    monkeypatch.setattr(main,"write_audit_event",lambda **kwargs:events.append("audit"))
    async def next_response(req):
        return Response("ready",background=BackgroundTask(lambda:events.append("existing")))
    response=asyncio.run(main.disable_stale_frontend_cache(request("/ai-assistant"),next_response))
    assert events==[]
    asyncio.run(response.background())
    assert events==["existing","audit"]


def test_audio_file_reads_skip_audit_but_catalog_reads_keep_it(monkeypatch):
    monkeypatch.setattr(main,"write_audit_event",lambda **kwargs:None)
    async def next_response(req):
        return Response("audio")
    for path in [
        "/v1/roleplay/background-music/track-id",
        "/v1/roleplay/action-sounds/pen",
        "/v1/characters/character-id/reactions/clip-id/audio",
    ]:
        response=asyncio.run(main.disable_stale_frontend_cache(request(path),next_response))
        assert response.background is None
    response=asyncio.run(main.disable_stale_frontend_cache(request("/v1/roleplay/background-music"),next_response))
    assert response.background is not None
