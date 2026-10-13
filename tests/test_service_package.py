import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("service_data", ROOT / "scripts/service_data.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


def fixture_data(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    with sqlite3.connect(source / "character_chat.sqlite") as db:
        db.execute("CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO app_settings VALUES (?,?)", ("character:elf", "CMS preserved"))
        db.execute("CREATE TABLE clips (content BLOB)")
        db.execute("INSERT INTO clips VALUES (?)", (b"voice sample bytes",))
    (source / "uploads").mkdir()
    (source / "uploads/avatar.png").write_bytes(b"avatar")
    return source


def test_backup_restore_preserves_cms_blobs_files_and_music(tmp_path):
    source = fixture_data(tmp_path)
    music = tmp_path / "music"
    music.mkdir()
    (music / "track.mp3").write_bytes(b"music")
    archive = tmp_path / "backup.zip"
    service.backup(source, archive, music)
    target = tmp_path / "restored"
    service.restore(archive, target)
    with sqlite3.connect(target / "data/character_chat.sqlite") as db:
        assert db.execute("SELECT value FROM app_settings").fetchone()[0] == "CMS preserved"
        assert db.execute("SELECT content FROM clips").fetchone()[0] == b"voice sample bytes"
    assert (target / "data/uploads/avatar.png").read_bytes() == b"avatar"
    assert (target / "music/track.mp3").read_bytes() == b"music"
    with pytest.raises(ValueError, match="must not exist"):
        service.restore(archive, target)


def test_backup_refuses_missing_db_and_overwrite(tmp_path):
    with pytest.raises(ValueError, match="Missing"):
        service.backup(tmp_path, tmp_path / "bad.zip")
    source = fixture_data(tmp_path)
    archive = tmp_path / "backup.zip"
    service.backup(source, archive)
    before = archive.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        service.backup(source, archive)
    assert archive.read_bytes() == before


@pytest.mark.parametrize("name", ["data/../../outside", "data/file"])
def test_restore_rejects_traversal_or_corrupt_content(tmp_path, name):
    archive = tmp_path / "bad.zip"
    manifest = {"format": 1, "tables": {}, "files": {name: hashlib.sha256(b"expected").hexdigest()}}
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr(name, b"corrupted")
        out.writestr("manifest.json", json.dumps(manifest))
    target = tmp_path / "restore"
    with pytest.raises(ValueError):
        service.restore(archive, target)
    assert not target.exists()
    assert not (tmp_path / "outside").exists()


def test_entrypoint_rejects_missing_secrets_and_missing_ui(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("entry", ROOT / "scripts/service_entrypoint.py")
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    monkeypatch.delenv("DOCS_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="must be configured"):
        entry.validate()
    monkeypatch.setenv("DOCS_USERNAME", "test")
    monkeypatch.setenv("DOCS_PASSWORD", "test-only")
    monkeypatch.setenv("DEMO_AUTH_ENABLED", "false")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    with pytest.raises(RuntimeError, match="Missing built UI"):
        entry.validate()
