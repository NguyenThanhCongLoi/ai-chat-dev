"""Production entrypoint: one web process for the current SQLite release."""
import os
from pathlib import Path
import sys


def validate():
    for name in ("DOCS_USERNAME", "DOCS_PASSWORD"):
        if not os.getenv(name, "").strip():
            raise RuntimeError(name + " must be configured; copy deploy/service.env.example")
    if os.getenv("DEMO_AUTH_ENABLED", "false").lower() != "false":
        raise RuntimeError("Production service requires DEMO_AUTH_ENABLED=false")
    dist = Path(os.getenv("FRONTEND_DIST", "frontend/dist"))
    for name in ("index.html", "admin.html"):
        if not (dist / name).is_file():
            raise RuntimeError("Missing built UI: " + str(dist / name))
    directory = Path(os.getenv("DATA_DIR", "data"))
    directory.mkdir(parents=True, exist_ok=True)
    probe = directory / ".service-write-test"
    with probe.open("x"):
        pass
    probe.unlink()


if __name__ == "__main__":
    try:
        validate()
    except (RuntimeError, OSError) as exc:
        sys.exit("Service configuration error: " + str(exc))
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "character_chat.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"])
