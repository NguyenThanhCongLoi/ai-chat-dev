"""Ordered sentence TTS: independent of the text stream, durable audio cache."""
import asyncio
import base64
import io
import json
import queue
import re
import threading
import time
import wave
from .speech_language import detect_speech_language, voice_language_enabled

_slots=threading.BoundedSemaphore(8)

class SentenceBuffer:
    def __init__(self):
        self.pending=""
    def feed(self,text,final=False):
        self.pending+=text
        result=[]
        # Wait for closing action markers; never speak an incomplete *action*.
        cursor=0;marker=None;index=0
        while index<len(self.pending):
            char=self.pending[index]
            if char=="*":
                end=index
                while end<len(self.pending) and self.pending[end]=="*":end+=1
                token=self.pending[index:end]
                if marker is None:marker=token
                elif token==marker:marker=None
                index=end;continue
            if marker is None and (char in "!?。！？\n" or (char=="." and index+1<len(self.pending) and self.pending[index+1].isspace())):
                part=self.pending[cursor:index+1].strip()
                if part:result.append(part)
                cursor=index+1
            elif marker is None and index-cursor>=240 and char.isspace():
                part=self.pending[cursor:index+1].strip()
                if part:result.append(part)
                cursor=index+1
            index+=1
        self.pending=self.pending[cursor:]
        if final and self.pending.strip():
            result.append(self.pending.strip());self.pending=""
        return result

class SentenceSpeech:
    def __init__(self,main,message_id,user,signature):
        if not _slots.acquire(blocking=False):raise RuntimeError("Voice preparation capacity reached")
        self.main=main;self.id=message_id;self.user=user;self.signature=signature
        with main.Session() as db:
            message=db.get(main.Message,message_id)
            self.spec=main.spec(db.get(main.Character,message.character_id))
        self.splitter=SentenceBuffer();self.parts=queue.Queue(maxsize=128);self.language=None
        self.stopped=threading.Event();self.final_text=None
        self.thread=threading.Thread(target=self.work,daemon=True,name="sentence-tts")
        self.thread.start()
    def change_language(self,language):
        if language!=self.language and self.splitter.pending:self.feed("",final=True,close=False)
        self.language=language
        if language is not None and not voice_language_enabled(self.spec,language):self.cancel("Unsupported spoken language")
    def feed(self,text,final=False,language=None,close=True):
        if self.stopped.is_set():return
        if language is not None:self.language=language
        for part in self.splitter.feed(text,final):
            code=detect_speech_language(part,self.language)
            if code=="none":continue
            if not voice_language_enabled(self.spec,code):self.cancel("Unsupported spoken language");return
            try:self.parts.put_nowait((part,code))
            except queue.Full:self.cancel("Too many voice segments");return
        if final and close:
            try:self.parts.put_nowait(None)
            except queue.Full:self.cancel("Too many voice segments")
    def finish(self,text):
        self.final_text=text;self.feed("",True)
    def cancel(self,error="Text stream interrupted"):
        self.stopped.set()
        try:self.parts.put_nowait(None)
        except queue.Full:pass
        with self.main.Session() as db:
            run=db.get(self.main.MessageSpeechRun,self.id)
            if run:run.status="error";run.error=error;db.commit()
    async def render(self,text,language,on_chunk=None):
        main=self.main
        with main.Session() as db:
            response=await main._roleplay_speech_stream(self.id,db,self.user,segment_text=text,segment_language=language)
            frames=[];rate=0;pending="";complete=False
            async for chunk in response.body_iterator:
                pending+=chunk.decode() if isinstance(chunk,bytes) else chunk
                while "\n\n" in pending:
                    block,pending=pending.split("\n\n",1)
                    data="\n".join(line[5:].strip() for line in block.splitlines() if line.startswith("data:"))
                    if not data:continue
                    event=json.loads(data)
                    if event.get("error"):
                        error=event["error"];raise RuntimeError(str(error.get("message") or error) if isinstance(error,dict) else str(error))
                    if event.get("type")=="speech.audio.delta":
                        next_rate=int(event["sample_rate"])
                        if rate and rate!=next_rate:raise RuntimeError("TTS sample rate changed")
                        rate=next_rate;content=base64.b64decode(event["audio"],validate=True);frames.append(content)
                        if on_chunk:on_chunk(content,rate)
                    if event.get("type")=="speech.audio.done":complete=True
            if not complete or not frames:raise RuntimeError("Sentence TTS incomplete")
            return b"".join(frames),rate
    def work(self):
        main=self.main;position=0;frames=[];rate=0;total=0;deadline=time.monotonic()+180
        empty=object();carry=empty
        try:
            while not self.stopped.is_set():
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError("Sentence TTS deadline exceeded")
                part=self.parts.get(timeout=remaining) if carry is empty else carry
                carry=empty
                if part is None:break
                part,language=part
                # Merge only sentences already queued; do not delay the first one.
                while len(part)<480:
                    try:following=self.parts.get_nowait()
                    except queue.Empty:break
                    if following is None:
                        carry=None;break
                    next_text,next_language=following
                    if next_language!=language or len(part)+len(next_text)+1>480:
                        carry=following;break
                    part+=" "+next_text
                with main.Session() as db:
                    message=db.get(main.Message,self.id)
                    character=db.get(main.Character,message.character_id) if message else None
                    if not character or main.speech_cache_signature(db,character,"")!=self.signature:
                        raise RuntimeError("Voice configuration changed")
                # Exclude roleplay actions before spending a TTS request.
                spoken=re.sub(r"\*\*[^*]+\*\*|\*[^*]+\*"," ",part).strip()
                if not spoken:continue
                total+=len(spoken)
                if total>4000:raise ValueError("Voice text exceeds 4000 characters")
                def publish(content,next_rate):
                    nonlocal position
                    if self.stopped.is_set():raise RuntimeError("Voice preparation cancelled")
                    if rate and rate!=next_rate:raise RuntimeError("TTS sample rate changed between sentences")
                    with main.Session() as db:
                        run=db.get(main.MessageSpeechRun,self.id)
                        if not run or run.signature!=self.signature or run.status!="generating":
                            raise RuntimeError("Voice preparation is no longer available")
                        db.add(main.MessageSpeechPart(message_id=self.id,position=position,sample_rate=next_rate,content=content));db.commit()
                    position+=1
                content,next_rate=asyncio.run(self.render(part,language,publish))
                if self.stopped.is_set():return
                if rate and rate!=next_rate:raise RuntimeError("TTS sample rate changed between sentences")
                rate=next_rate;frames.append(content)
                if sum(map(len,frames))>12*1024*1024:raise ValueError("Voice audio exceeds 12 MB")

            if self.stopped.is_set():return
            if not frames:raise ValueError("No spoken dialogue")
            output=io.BytesIO()
            with wave.open(output,"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(b"".join(frames))
            with main.Session() as db:
                message=db.get(main.Message,self.id);run=db.get(main.MessageSpeechRun,self.id)
                if not message or not run or message.text!=self.final_text or message.finish_status=="partial":return
                character=db.get(main.Character,message.character_id)
                if main.speech_cache_signature(db,character,"")!=self.signature:
                    run.status="error";run.error="Voice configuration changed";db.commit();return
                signature=main.speech_cache_signature(db,character,main.speech_message_text(db,message,character))
                db.merge(main.MessageSpeech(message_id=self.id,signature=signature,mime_type="audio/wav",content=output.getvalue()))
                run.status="ready"
                db.query(main.MessageSpeechPart).filter_by(message_id=self.id).delete()
                db.commit()
        except Exception as exc:
            self.cancel(str(exc)[:300])
        finally:
            _slots.release()

async def replay_parts(main,message_id,signature):
    """Poll durable parts, so playback also works on another server worker."""
    position=0;replay_bytes=0;deadline=time.monotonic()+185;last_rate=0
    while time.monotonic()<deadline:
        with main.Session() as db:
            run=db.get(main.MessageSpeechRun,message_id)
            if not run or run.signature!=signature:
                yield 'data: '+json.dumps({"error":{"message":"Voice preparation is no longer available"}})+'\n\n';return
            status=run.status
            rows=db.query(main.MessageSpeechPart).filter(main.MessageSpeechPart.message_id==message_id,main.MessageSpeechPart.position>=position).order_by(main.MessageSpeechPart.position).all()
            # Once compacted, recover any remaining PCM from the finished WAV.
            if status=="ready":
                cached=db.get(main.MessageSpeech,message_id)
                if cached:
                    with wave.open(io.BytesIO(cached.content),"rb") as wav:
                        rate=wav.getframerate();pcm=wav.readframes(wav.getnframes())
                    # Existing parts were sent before compaction; offset retained locally.
                    pcm=pcm[replay_bytes:]
                    rows=[type("Part",(),{"position":position,"sample_rate":rate,"content":pcm})()] if pcm else []
            error=run.error
            # Materialize before closing the session.
            values=[(row.position,row.sample_rate,row.content) for row in rows]
        for index,rate,content in values:
            last_rate=rate
            for start in range(0,len(content),24000):
                chunk=content[start:start+24000]
                yield 'data: '+json.dumps({"type":"speech.audio.delta","format":"pcm","sample_rate":rate,"audio":base64.b64encode(chunk).decode()})+'\n\n'
            replay_bytes+=len(content);position=index+1
        if status=="ready":
            yield 'data: {"type":"speech.audio.done"}\n\n';return
        if status=="error":
            yield 'data: '+json.dumps({"error":{"message":error or "Voice preparation failed"}})+'\n\n';return
        await asyncio.sleep(.15)
    yield 'data: {"error":{"message":"Voice preparation timed out"}}\n\n'
