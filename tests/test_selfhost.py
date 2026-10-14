"""Standalone CPU release: reject legacy routes and run without the Modal SDK."""
import importlib.util
from pathlib import Path
import sys
import pytest
from character_chat import chat_transport

ROOT = Path(__file__).resolve().parents[1]


def entrypoint():
    spec = importlib.util.spec_from_file_location("selfhost_entry", ROOT / "scripts/service_entrypoint.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def valid_environment(tmp_path, monkeypatch):
    for name in ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "AVATAR_MODAL_FUNCTION"):
        monkeypatch.delenv(name, raising=False)
    config = {
        "DOCS_USERNAME": "fixture",
        "DOCS_PASSWORD": "fixture-only",
        "DEMO_AUTH_ENABLED": "false",
        "CHAT_TRANSPORT": "direct",
        "GROUP_ROUTER_MODE": "local",
        "GROUP_ROUTER_TRANSPORT": "http",
        "REACTION_GENERATOR_MODE": "disabled",
        "AVATAR_GENERATOR_MODE": "default",
        "DATA_DIR": str(tmp_path / "data"),
        "FRONTEND_DIST": str(tmp_path / "dist"),
    }
    (tmp_path / "dist").mkdir()
    for name in ("index.html", "admin.html"):
        (tmp_path / "dist" / name).write_text("<html></html>")
    for name, value in config.items():
        monkeypatch.setenv(name, value)
    return config


def test_startup_without_modal_sdk(valid_environment, monkeypatch):
    monkeypatch.setitem(sys.modules, "modal", None)
    entrypoint().validate()
    import character_chat.main as main
    assert main.app is not None


@pytest.mark.parametrize("name,value", [
    ("CHAT_TRANSPORT", "modal"),
    ("GROUP_ROUTER_TRANSPORT", "modal"),
    ("GROUP_ROUTER_MODE", "decision"),
    ("REACTION_GENERATOR_MODE", "modal"),
    ("REACTION_GENERATOR_MODE", "http"),
    ("AVATAR_MODAL_FUNCTION", "process_avatar"),
    ("MODAL_TOKEN_ID", "legacy"),
    ("MODAL_TOKEN_SECRET", "legacy"),
])
def test_startup_rejects_unmigrated_configuration(valid_environment, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=name):
        entrypoint().validate()


def test_stream_uses_direct_transport_without_sdk(monkeypatch):
    monkeypatch.setenv("CHAT_TRANSPORT", "direct")
    monkeypatch.setitem(sys.modules, "modal", None)
    monkeypatch.setattr(chat_transport, "direct_stream", lambda *args: iter(["fixture text"]))
    assert list(chat_transport.chat_stream([], "fixture")) == ["fixture text"]
    monkeypatch.setenv("CHAT_TRANSPORT", "modal")
    with pytest.raises(ValueError, match="CHAT_TRANSPORT=direct"):
        chat_transport.chat_stream([], "fixture")


def test_default_avatar_preserves_migrated_images(monkeypatch):
    import character_chat.main as main
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from character_chat.models import Base, CharacterExpressionAsset
    from character_chat import avatar_pipeline
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as db:
        db.add(CharacterExpressionAsset(id="existing", character_id="elf",
            emotion="happy", mime_type="image/png", content=b"migrated-image"))
        db.commit()
    monkeypatch.setattr(main, "Session", factory)
    monkeypatch.setenv("AVATAR_GENERATOR_MODE", "default")
    monkeypatch.setattr(avatar_pipeline, "build_ai_expression_variants",
                        lambda *args: pytest.fail("Default mode must not call the image provider"))
    defaults = []
    monkeypatch.setattr(main, "install_default_expressions", lambda db, identifier: defaults.append(identifier))
    main.generate_character_expressions("elf", b"source")
    with factory() as db:
        assert db.get(CharacterExpressionAsset, "existing").content == b"migrated-image"
    assert defaults == []
    main.generate_character_expressions("new-character", b"source")
    assert defaults == ["new-character"]
    engine.dispose()
