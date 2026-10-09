"""Language metadata is part of the existing LLM stream, never a second LLM call."""
import re
from .engine import detect_message_language

LANGUAGE_INSTRUCTION = (
    "Prefix EVERY spoken sentence or language change with [[lang:xx]], where xx is its actual "
    "ISO language code (vi, en, ja, zh, ko, my, etc.). Include these markers only as metadata; "
    "keep the roleplay reply and action formatting otherwise unchanged. Never label an unsupported "
    "language as en. Example: [[lang:vi]]Chào bạn! [[lang:en]]How are you?"
)

def spoken_text(text):
    return re.sub(r"\s+"," ",re.sub(r"\*\*[^*]+\*\*|\*[^*]+\*"," ",text)).strip()

def detect_speech_language(text,hint=None):
    text=spoken_text(text)
    if not text:return "none"
    for pattern,language in [(r"[\u1780-\u17ff]","km"),(r"[\u3040-\u30ff]","ja"),(r"[\uac00-\ud7af]","ko"),(r"[\u4e00-\u9fff]","zh"),(r"[\u1000-\u109f\uaa60-\uaa7f]","my"),(r"[\u0600-\u06ff]","ar"),(r"[\u0590-\u05ff]","he"),(r"[\u0900-\u097f]","hi"),(r"[\u0e00-\u0e7f]","th"),(r"[\u0400-\u04ff]","ru")]:
        if re.search(pattern,text):return language
    detected=detect_message_language(text,"unknown")
    if detected not in {"unknown","vi","en"}:return detected
    if detected=="vi" and re.search(r"[ăâđêôơư]",text.casefold()):return "vi"
    if hint and re.fullmatch(r"[a-z]{2}",hint):return hint
    return detected

class LanguageStream:
    def __init__(self):self.buffer=""
    def feed(self,text,final=False):
        self.buffer+=text;events=[]
        while self.buffer:
            start=self.buffer.find("[[lang:")
            if start>=0:
                if start:events.append(("delta",self.buffer[:start]));self.buffer=self.buffer[start:]
                end=self.buffer.find("]]")
                if end<0:
                    if len(self.buffer)>40:self.buffer="";events.append(("language","unknown"))
                    break
                code=self.buffer[7:end].strip().lower()
                events.append(("language",code if re.fullmatch(r"[a-z]{2}",code) else "unknown"))
                self.buffer=self.buffer[end+2:];continue
            keep=0
            if not final:
                for length in range(1,min(7,len(self.buffer))+1):
                    if "[[lang:".startswith(self.buffer[-length:]):keep=length
            emit=self.buffer[:-keep] if keep else self.buffer
            if emit:events.append(("delta",emit))
            self.buffer=self.buffer[-keep:] if keep else "";break
        if final:self.buffer=""  # Never expose an incomplete control marker.
        return events

def sentence_segments(text,metadata=None):
    from .incremental_voice import SentenceBuffer
    parts=SentenceBuffer().feed(text,final=True)
    if metadata and spoken_text(" ".join(item.get("text","") for item in metadata))==spoken_text(text):
        return [{"text":item["text"],"language":detect_speech_language(item["text"],item.get("language"))}
                for item in metadata if spoken_text(item.get("text",""))]
    return [{"text":part,"language":detect_speech_language(part)} for part in parts if spoken_text(part)]

def voice_language_enabled(spec,language):
    if language in {"unknown","none"}:return False
    config=spec.tts_languages.get(language) if spec else None
    if config is not None:
        return config.enabled and (language in {"vi","en"} or bool(config.voice_id.strip()))
    return language in {"vi","en"}

def speech_info(text,metadata=None,spec=None):
    languages=list(dict.fromkeys(item["language"] for item in sentence_segments(text,metadata)))
    return {"speech_languages":languages,"speech_supported":bool(languages) and all(voice_language_enabled(spec,code) for code in languages)}

def configured_voice(spec,language):
    config=spec.tts_languages.get(language)
    if config and config.voice_id.strip():return config.voice_id.strip()
    if language not in {"vi","en"}:return ""
    if spec.tts_voice_mode=="separate":
        return (spec.tts_voice_vi if language=="vi" else spec.tts_voice_en).strip()
    return spec.tts_voice_id.strip()

def parse_language_reply(raw):
    parser=LanguageStream();events=parser.feed(raw,final=True)
    text="";parts=[];current="";language=None
    for event,value in events:
        if event=="language":
            if current:parts.append({"text":current,"language":language});current=""
            language=value
        else:text+=value;current+=value
    if current:parts.append({"text":current,"language":language})
    return text,parts
