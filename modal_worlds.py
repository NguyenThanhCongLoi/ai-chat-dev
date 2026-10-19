"""Isolated CPU-only Modal world experiment; never deploys over character-chat."""
import os
import shutil
import subprocess
from pathlib import Path
import modal

ROOT=Path(__file__).resolve().parent

def build_ui():
    npm=shutil.which("npm.cmd") or shutil.which("npm")
    node=Path(r"D:\Chatbot\.tools\node-v24.21.0-win-x64")
    if not npm and (node/"npm.cmd").is_file():npm=str(node/"npm.cmd")
    if not npm:raise RuntimeError("Build requires Node/npm on the deploying machine")
    env=os.environ.copy()
    if node.exists():env["PATH"]=str(node)+os.pathsep+env.get("PATH","")
    if not (ROOT/"frontend/node_modules").exists():
        subprocess.run([npm,"ci"],cwd=ROOT/"frontend",env=env,check=True)
    subprocess.run([npm,"run","build"],cwd=ROOT/"frontend",env=env,check=True)

# This module is imported again in the CPU container, which already carries dist.
if Path(__file__).parent!=Path("/root"):build_ui()
app=modal.App("character-chat-worlds-demo")
data=modal.Volume.from_name("character-chat-worlds-demo-data",create_if_missing=True)
image=(modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi>=0.115","uvicorn>=0.30","sqlalchemy>=2","pydantic>=2","python-multipart>=0.0.9",
                 "httpx>=0.27","pillow>=10.4","pymupdf>=1.24","python-docx>=1.1","python-pptx>=1.0",
                 "openpyxl>=3.1","cryptography>=43")
    .add_local_dir("character_chat",remote_path="/root/character_chat")
    .add_local_dir("frontend/dist",remote_path="/root/frontend/dist")
    .add_local_dir("image",remote_path="/root/image")
    .add_local_file("docs/UI_LOCALIZATION_STYLE.md",remote_path="/root/docs/UI_LOCALIZATION_STYLE.md"))
# Existing provider secrets are optional: authored choices do not call an LLM.
provider_secrets=[]
if os.getenv("WORLDS_USE_PROVIDER_SECRETS","false").lower()=="true":
    provider_secrets=[modal.Secret.from_name("character-chat-llm"),modal.Secret.from_name("character-chat-moderation")]
@app.function(image=image,volumes={"/data":data},min_containers=0,max_containers=1,
              scaledown_window=30,timeout=600,secrets=[modal.Secret.from_name(os.getenv("WORLDS_DOCS_SECRET","character-chat-docs")),*provider_secrets],
              env={"DATA_DIR":"/data","FRONTEND_DIST":"/root/frontend/dist","CHARACTER_IMAGE_DIR":"/root/image",
                   "DEMO_AUTH_ENABLED":"false","WORLD_DEMO_ENABLED":"true","CHAT_TRANSPORT":"direct",
                   "GROUP_ROUTER_MODE":"local","REACTION_GENERATOR_MODE":"disabled","AVATAR_GENERATOR_MODE":"default",
                   "BUILD_VERSION":"worlds-chapter-v2"})
@modal.concurrent(max_inputs=8,target_inputs=4)
@modal.asgi_app()
def web():
    from character_chat.main import app as api
    return api
