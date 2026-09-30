import modal

app=modal.App("character-chat-probe")
image=modal.Image.debian_slim(python_version="3.12").pip_install("fastapi")

@app.function(image=image,timeout=60)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    probe=FastAPI()
    @probe.get("/health")
    def health():return {"status":"ok"}
    return probe
