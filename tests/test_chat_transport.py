import json
import time

import httpx
import pytest

from character_chat import chat_transport as transport


def event(content=None, finish=None, **delta):
    if content is not None:
        delta["content"] = content
    return ("data: " + json.dumps({"choices": [{"delta": delta, "finish_reason": finish}]}) + "\n\n").encode()


class Stream(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.read_count = 0
        self.closed = False

    def __iter__(self):
        for chunk in self.chunks:
            self.read_count += 1
            yield chunk

    def close(self):
        self.closed = True


def install(monkeypatch, stream, status=200):
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(status, stream=stream, headers={"content-type": "text/event-stream"})
    client = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(transport, "_client", client)
    return client, requests


def test_first_content_is_forwarded_before_remaining_body_and_cancel_closes(monkeypatch):
    stream = Stream([event(reasoning_content="private"), event("Hello"), event(" later"), event(finish="stop")])
    client, requests = install(monkeypatch, stream)
    generator = transport.chat_stream([], "test", "https://gateway.invalid/v1", "key")
    timing = next(generator)["_gateway_timing"]
    assert timing["gateway_first_chunk_ms"] >= timing["gateway_headers_ms"]
    assert next(generator) == "Hello"
    assert stream.read_count == 2
    generator.close()
    assert stream.closed
    assert json.loads(requests[0].content)["stream"] is True
    assert requests[0].url.path == "/v1/chat/completions"
    client.close()


@pytest.mark.parametrize("finish,status", [("stop", "complete"), ("length", "truncated"), (None, "unknown")])
def test_completion_status_is_preserved(monkeypatch, finish, status):
    stream = Stream([event("Hello"), event(finish=finish), b"data: [DONE]\n\n"])
    client, _ = install(monkeypatch, stream)
    values = list(transport.direct_stream([], "test", "https://gateway.invalid", "key"))
    assert values[-1] == {"_stream_status": status}
    assert [value for value in values if isinstance(value, str)] == ["Hello"]
    assert stream.closed
    client.close()


def test_http_failure_closes_upstream(monkeypatch):
    stream = Stream([b"unavailable"])
    client, _ = install(monkeypatch, stream, 503)
    with pytest.raises(RuntimeError, match="Gateway HTTP 503"):
        list(transport.direct_stream([], "test", "https://gateway.invalid", "key"))
    assert stream.closed
    client.close()


def test_roleplay_fallback_keeps_identity_and_stops_after_partial(monkeypatch):
    import character_chat.main as main
    monkeypatch.setattr(main.llm, "model", "config-a")
    monkeypatch.setattr(main.llm, "fallback_model", "config-b")
    monkeypatch.setattr(main.llm, "fallback_model_2", "")
    monkeypatch.setattr(main.llm, "model_wire_ids", {"config-a": "same-wire", "config-b": "same-wire"})
    monkeypatch.setattr(main.llm, "api_key", "test")
    monkeypatch.setattr(main, "model_circuit_remaining", lambda _: 0)
    monkeypatch.setattr(main, "record_model_failure", lambda *args: None)
    monkeypatch.setattr(main, "record_model_success", lambda *args: None)
    calls = []
    def failing_first(*args):
        calls.append(args)
        if len(calls) == 1:
            raise httpx.ReadTimeout("upstream timeout")
        yield {"_gateway_timing": {"gateway_headers_ms": 10, "gateway_first_chunk_ms": 25}}
        yield "Hi"
        yield {"_stream_status": "complete"}
    monkeypatch.setattr(main, "chat_stream", failing_first)
    values = list(main.stream_roleplay_answer([], .3, 200, "normal"))
    assert values[0] == ("delta", "Hi")
    meta = values[-1][1]
    assert meta["actual_model_config_id"] == "config-b"
    assert meta["fallback_used"]
    assert meta["gateway_first_chunk_ms"] == 25

    calls.clear()
    def interrupted(*args):
        calls.append(args)
        yield "partial"
        raise httpx.RemoteProtocolError("connection lost")
    monkeypatch.setattr(main, "chat_stream", interrupted)
    values = list(main.stream_roleplay_answer([], .3, 200, "normal"))
    assert len(calls) == 1
    assert values[-1][1]["finish_status"] == "partial"


def test_bounded_stream_closes_after_deadline(monkeypatch):
    import character_chat.main as main
    closed = []
    def upstream():
        try:
            time.sleep(.05)
            yield "late"
        finally:
            closed.append(True)
    with pytest.raises(TimeoutError):
        list(main.bounded_remote_chunks(upstream(), time.monotonic() + .01))
    for _ in range(30):
        if closed:
            break
        time.sleep(.01)
    assert closed


def test_multiline_sse():
    assert list(transport._sse_data([": heartbeat", "data: {", 'data: "a": 1}', ""])) == ['{\n"a": 1}']

def test_timing_migration_is_idempotent_and_preserves_old_rows(monkeypatch):
    import character_chat.db as db
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.schema import CreateTable
    from character_chat.models import AIRequestLog
    engine = create_engine("sqlite://")
    new_fields = ("server_prepare_ms", "gateway_headers_ms", "gateway_first_chunk_ms")
    ddl = str(CreateTable(AIRequestLog.__table__).compile(dialect=engine.dialect))
    old_ddl = "\n".join(line for line in ddl.splitlines() if not any(field in line for field in new_fields))
    with engine.begin() as connection:
        connection.execute(text(old_ddl))
        required = [column.name for column in AIRequestLog.__table__.columns
                    if not column.nullable and column.name not in new_fields]
        values = {name: ("old-log" if name == "id" else 123 if name == "latency_ms"
                        else 0 if name in ("fallback_used", "continuation_count") else "old") for name in required}
        connection.execute(text("INSERT INTO ai_request_logs (" + ",".join(required) + ") VALUES (" +
                                ",".join(":" + name for name in required) + ")"), values)
    monkeypatch.setattr(db, "engine", engine)
    db.init_db()
    db.init_db()
    assert set(new_fields).issubset({column["name"] for column in inspect(engine).get_columns("ai_request_logs")})
    with engine.connect() as connection:
        row = connection.execute(text("SELECT latency_ms,server_prepare_ms,gateway_headers_ms,gateway_first_chunk_ms FROM ai_request_logs WHERE id='old-log'")).one()
        assert tuple(row) == (123, None, None, None)
    engine.dispose()

def test_assistant_same_wire_model_on_other_gateway_is_not_blocked(monkeypatch):
    import character_chat.main as main
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from character_chat.db import Base, ModelConfig, AppSetting
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setenv("CHAT_TRANSPORT", "direct")
    monkeypatch.setattr(main, "MODEL_CIRCUIT", {})
    monkeypatch.setattr(main, "credential_for_model", lambda *args: "test")
    calls = []
    def completion(*args):
        calls.append(args[2])
        if len(calls) == 1:
            raise httpx.ReadTimeout("timed out")
        return "fallback answer"
    monkeypatch.setattr(main, "direct_completion", completion)
    with sessionmaker(engine, expire_on_commit=False)() as db:
        primary = ModelConfig(id="gateway-a", name="A", provider="test", model_id="same-wire", api_base="https://a.invalid")
        fallback = ModelConfig(id="gateway-b", name="B", provider="test", model_id="same-wire", api_base="https://b.invalid")
        db.add_all([primary, fallback,
                    AppSetting(key="model_profile:gateway-a", value=json.dumps({"purposes": ["assistant_general"]})),
                    AppSetting(key="model_profile:gateway-b", value=json.dumps({"purposes": ["assistant_general_fallback"]}))])
        db.commit()
        answer, meta = main.run_assistant_model_chain(db, [primary, fallback], "assistant_general", "prompt", [], "")
        assert answer == "fallback answer"
        assert meta["actual_model_config_id"] == "gateway-b"
        assert meta["fallback_used"]
        assert main.model_circuit_remaining("gateway-a") > 0
        assert main.model_circuit_remaining("gateway-b") == 0
    assert calls == ["https://a.invalid", "https://b.invalid"]
    engine.dispose()
