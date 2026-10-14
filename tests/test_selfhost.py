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
    for name in ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "AVATAR_MODAL_FUNCTION", "PROVIDER_API_KEYS_JSON"):
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


def test_provider_env_key_overrides_cms_without_decrypting(monkeypatch):
    import character_chat.main as main
    from types import SimpleNamespace
    sentinel = "fixture-provider-key"
    monkeypatch.setenv("PROVIDER_API_KEYS_JSON", '{"https://provider.invalid/v1/":"fixture-provider-key"}')
    monkeypatch.setattr(main, "decrypt_admin_secret", lambda value: pytest.fail("Env key must override DB credential"))
    model = SimpleNamespace(api_base="https://provider.invalid/v1", api_key_encrypted="old-ciphertext")
    assert main.credential_for_model(None, model) == sentinel
    assert main.credential_for_base(None, model.api_base) == sentinel


def test_provider_env_absence_keeps_cms_key(monkeypatch):
    import character_chat.main as main
    from types import SimpleNamespace
    monkeypatch.setenv("PROVIDER_API_KEYS_JSON", "{}")
    monkeypatch.setattr(main, "decrypt_admin_secret", lambda value: "fixture-cms-key")
    model = SimpleNamespace(api_base="https://provider.invalid/v1", api_key_encrypted="ciphertext")
    assert main.credential_for_model(None, model) == "fixture-cms-key"


@pytest.mark.parametrize("raw", ['{"broken":"SECRET_MARKER"}', '["SECRET_MARKER"]', "SECRET_MARKER"])
def test_invalid_provider_env_does_not_expose_key(valid_environment, monkeypatch, raw):
    import character_chat.main as main
    from fastapi import HTTPException
    monkeypatch.setenv("PROVIDER_API_KEYS_JSON", raw)
    with pytest.raises(RuntimeError) as error:
        entrypoint().validate()
    assert "PROVIDER_API_KEYS_JSON" in str(error.value) and "SECRET_MARKER" not in str(error.value)
    with pytest.raises(HTTPException) as error:
        main.environment_credential("https://provider.invalid/v1")
    assert "SECRET_MARKER" not in error.value.detail
