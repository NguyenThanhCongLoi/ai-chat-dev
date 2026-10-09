import threading
import time

import httpx
import pytest


def test_document_redirect_is_checked_before_request(monkeypatch):
    import character_chat.main as main
    requested=[]
    def validate(url):
        if "127.0.0.1" in url:raise ValueError("private address")
    def respond(request):
        requested.append(str(request.url))
        return httpx.Response(302,headers={"location":"http://127.0.0.1/private"})
    original=httpx.Client
    monkeypatch.setattr(main,"_safe_public_url",validate)
    monkeypatch.setattr(main.httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    with pytest.raises(ValueError,match="private address"):
        main._download_public_document("https://public.example/story")
    assert requested==["https://public.example/story"]


def test_document_download_stops_at_size_limit(monkeypatch):
    import character_chat.main as main
    class Stream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"x"*65536
            raise AssertionError("Should stop before reading more")
    original=httpx.Client
    monkeypatch.setattr(main,"_safe_public_url",lambda url:None)
    monkeypatch.setattr(main.httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,stream=Stream())),**kw))
    with pytest.raises(ValueError):main._download_public_document("https://public.example/story",limit=100)


def test_deadline_returns_without_waiting_for_stalled_request():
    from character_chat.engine import _within_deadline
    release=threading.Event()
    started=time.monotonic()
    try:
        with pytest.raises(httpx.ReadTimeout):
            _within_deadline(lambda:release.wait(2),.05)
        assert time.monotonic()-started<1
    finally:release.set()


def test_connect_retry_uses_only_remaining_time(monkeypatch):
    from character_chat.engine import LLM
    import character_chat.engine as engine
    model=LLM();model.api_key="test"
    ticks=iter([10,17])
    monkeypatch.setattr(engine.time,"monotonic",lambda:next(ticks))
    class Client:
        calls=0
        def post(self,*args,**kwargs):
            self.calls+=1
            if self.calls==1:raise httpx.ConnectTimeout("test")
            assert kwargs["timeout"].read==3
            return httpx.Response(200,json={"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}]})
    model._clients[model.url]=Client()
    assert model._request([],0,20,"test",10)=="ok"
