"""Run the desktop world experiment on loopback with its own persistent demo DB."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535")
    if not (ROOT / "frontend/dist/index.html").is_file():
        parser.error("Build frontend first: cd frontend; npm run build")
    # No production DB, provider secrets or Modal transport in this local demo.
    os.environ.pop("DATABASE_URL", None)
    for name in ("LLM_API_KEY", "AIMP_API_KEY", "OPENAI_API_KEY", "WORLD_MODERATION_API_KEY",
                 "PROVIDER_API_KEYS_JSON", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"):
        os.environ[name] = ""
    os.environ.update(
        DATA_DIR=str(ROOT / "artifacts/worlds-desktop/data"),
        FRONTEND_DIST=str(ROOT / "frontend/dist"),
        CHARACTER_IMAGE_DIR=str(ROOT / "image"),
        WORLD_DEMO_ENABLED="true", DEMO_AUTH_ENABLED="false",
        CHAT_TRANSPORT="direct", GROUP_ROUTER_MODE="local",
        REACTION_GENERATOR_MODE="disabled", AVATAR_GENERATOR_MODE="default",
        AVATAR_MODAL_FUNCTION="", BUILD_VERSION="worlds-desktop-demo",
    )
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    print(f"Desktop demo: http://127.0.0.1:{args.port}/worlds", flush=True)
    print("Create a test account first via the existing sign-in page. Ctrl+C stops the demo.", flush=True)
    print("Rules only: free text and publication require separately configured moderation.", flush=True)
    import uvicorn
    uvicorn.run("character_chat.main:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
