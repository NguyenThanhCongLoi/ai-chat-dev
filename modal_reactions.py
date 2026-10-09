"""Optional GPU worker: create reusable reaction sets outside the chat service."""
import os
import modal

app = modal.App("character-reactions")
cache = modal.Volume.from_name("character-reactions-models", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "git")
    .env({"HF_HOME":"/models/huggingface", "TORCH_HOME":"/models/torch"})
    .pip_install("chatterbox-tts==0.1.7", "modal>=1.5,<2")
    .add_local_dir("character_chat",remote_path="/root/character_chat"))
secrets = [modal.Secret.from_name(os.environ["REACTION_HF_SECRET"])] if os.getenv("REACTION_HF_SECRET") else []

PROMPTS = {
    "neutral": ["Hmm.", "Mhm."],
    "happy": ["[chuckle]", "[laugh]"],
    "sad": ["[sigh]", "Mm..."],
    "angry": ["[groan]", "Tch."],
    "surprised": ["Huh?", "Oh?"],
    "shy": ["Mm.", "[chuckle]"],
}

@app.function(image=image, gpu="L4", memory=8192, timeout=900, max_containers=1,
              scaledown_window=60, volumes={"/models":cache}, secrets=secrets)
def generate_reactions(reference: bytes, filename: str, repeat_short: bool=False, slots: list|None=None):
    import io
    import tempfile
    import wave
    import numpy as np
    import torch
    from pathlib import Path
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    allowed={(emotion,variant) for emotion,prompts in PROMPTS.items() for variant in range(len(prompts))}
    requested=allowed if slots is None else {tuple(slot) for slot in slots}
    if not requested or not requested.issubset(allowed):raise ValueError("Invalid reaction slots")
    if len(reference)>20*1024*1024: raise ValueError("Reference exceeds 20 MB")
    global _model
    if "_model" not in globals():
        _model = ChatterboxTurboTTS.from_pretrained(device="cuda")
        cache.commit()
    extension = Path(filename).suffix.lower()
    if extension not in {".wav",".mp3",".flac",".ogg",".m4a"}: raise ValueError("Unsupported reference format")
    with tempfile.TemporaryDirectory() as directory:
        sample=Path(directory)/("reference"+extension)
        sample.write_bytes(reference)
        if repeat_short:
            import librosa
            from character_chat.reaction_reference import reference_repeat_count
            original,sr=librosa.load(str(sample),sr=24000,mono=True)
            repeats=reference_repeat_count(len(original),sr)
            if repeats>1:
                overlap=min(round(sr*.02),len(original)//4)
                extended=original.copy()
                fade=np.linspace(0,1,overlap,dtype=np.float32)
                for _ in range(repeats-1):
                    join=extended[-overlap:]*(1-fade)+original[:overlap]*fade
                    extended=np.concatenate((extended[:-overlap],join,original[overlap:]))
                sample=Path(directory)/"repeated-reference.wav"
                with wave.open(str(sample),"wb") as wav:
                    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(sr)
                    wav.writeframes((np.clip(extended,-1,1)*32767).astype("<i2").tobytes())
        _model.prepare_conditionals(str(sample))
        result=[]
        for emotion, prompts in PROMPTS.items():
            for variant,text in enumerate(prompts):
                if (emotion,variant) not in requested:continue
                with torch.inference_mode():
                    audio=_model.generate(text).detach().cpu().numpy().reshape(-1)
                # Remove silent edges, cap duration and avoid clipped peaks.
                voiced=np.flatnonzero(np.abs(audio)>.004)
                if not len(voiced): raise ValueError("Model generated silent reaction")
                margin=int(_model.sr*.04)
                audio=audio[max(0,int(voiced[0])-margin):min(len(audio),int(voiced[-1])+margin+1)]
                if len(audio)/_model.sr>4: raise ValueError("Reaction is too long; retry generation")
                if len(audio)/_model.sr<.15: audio=np.pad(audio,(0,int(.15*_model.sr)-len(audio)))
                peak=float(np.max(np.abs(audio)))
                if peak>0: audio=audio*(min(.85/peak,4))
                pcm=(np.clip(audio,-1,1)*32767).astype("<i2")
                buffer=io.BytesIO()
                with wave.open(buffer,"wb") as wav:
                    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(_model.sr);wav.writeframes(pcm.tobytes())
                result.append({"emotion":emotion,"variant":variant,"audio":buffer.getvalue()})
        return result
