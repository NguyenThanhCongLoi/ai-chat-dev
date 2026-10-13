"""Start actual Uvicorn twice to check the service and migrated CMS."""
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from cryptography.fernet import Fernet
from test_service_package import service

ROOT = Path(__file__).resolve().parents[1]


def request(base, path, auth=False):
    headers = {}
    if auth:
        headers["Authorization"] = "Basic " + base64.b64encode(b"test:service-test-only").decode()
    try:
        with urllib.request.urlopen(urllib.request.Request(base + path, headers=headers), timeout=3) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def run_server(data, temp):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ)
    env.pop("DATABASE_URL", None)
    env.update(DATA_DIR=str(data), FRONTEND_DIST=str(ROOT / "frontend/dist"), DOCS_USERNAME="test", DOCS_PASSWORD="service-test-only", DEMO_AUTH_ENABLED="false", CHAT_TRANSPORT="direct", GROUP_ROUTER_MODE="local", REACTION_GENERATOR_MODE="disabled", LLM_API_KEY="", AIMP_API_KEY="", OPENAI_API_KEY="", AVATAR_MODAL_FUNCTION="")
    log = (temp / ("server-" + str(port) + ".log")).open("w", encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "character_chat.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = "http://127.0.0.1:" + str(port)
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise AssertionError("Server exited; see " + log.name)
            try:
                if request(base, "/health")[0] == 200:
                    return process, log, base
            except OSError:
                pass
            time.sleep(.2)
        raise AssertionError("Startup timed out; see " + log.name)
    except Exception:
        process.terminate()
        process.wait(timeout=15)
        log.close()
        raise


def stop(process, log):
    process.terminate()
    process.wait(timeout=15)
    log.close()


def test_startup_and_restored_cms(tmp_path):
    assert (ROOT / "frontend/dist/index.html").is_file(), "Build frontend before startup test"
    data = tmp_path / "data"
    process, log, base = run_server(data, tmp_path)
    try:
        assert request(base, "/")[0] == 200
        assert request(base, "/admin")[0] == 401
        assert request(base, "/admin", True)[0] == 200
        assert request(base, "/v1/rooms")[0] == 401
        assert request(base, "/v1/admin/settings")[0] == 401
        assert request(base, "/v1/admin/settings", True)[0] == 200
    finally:
        stop(process, log)
    # Synthetic encrypted CMS credential; no production key is touched.
    cipher = Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"ai-role-play-model-vault:service-test-only").digest()))
    encrypted = cipher.encrypt(b"test-credential-not-real").decode()
    with closing(sqlite3.connect(data / "character_chat.sqlite")) as db:
        db.execute("INSERT OR REPLACE INTO app_settings (key,value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP)", ("credential:avibi", encrypted))
        db.execute("INSERT OR REPLACE INTO app_settings (key,value,updated_at) VALUES (?,?,CURRENT_TIMESTAMP)", ("default_temperature", "0.42"))
        db.commit()
    archive = tmp_path / "cms.zip"
    service.backup(data, archive)
    restored = tmp_path / "restored"
    service.restore(archive, restored)
    process, log, base = run_server(restored / "data", tmp_path)
    try:
        status, body = request(base, "/v1/admin/settings", True)
        assert status == 200
        assert float(json.loads(body)["default_temperature"]) == .42
        with closing(sqlite3.connect(restored / "data/character_chat.sqlite")) as db:
            value = db.execute("SELECT value FROM app_settings WHERE key='credential:avibi'").fetchone()[0]
        assert cipher.decrypt(value.encode()) == b"test-credential-not-real"
    finally:
        stop(process, log)
