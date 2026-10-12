"""Probe the deployed worker with fixture characters; no product DB access."""
import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import modal
from character_chat.group_decision import build_request
from character_chat.schemas import CharacterSpec,Identity
characters=[
    CharacterSpec(id="work",name="Morgan",description="Career and business advisor",identity=Identity(role="career advisor")),
    CharacterSpec(id="art",name="Luna",description="Creative music and art specialist",identity=Identity(role="artist")),
    CharacterSpec(id="health",name="Mira",description="Health and wellbeing specialist",identity=Identity(role="doctor")),
]
worker=modal.Cls.from_name("character-chat-group-router","GroupRouter")()
for message in ["Mình muốn đổi công việc nhưng vẫn theo đuổi âm nhạc, nên bắt đầu thế nào?",
                "Tôi bị mất ngủ và mệt mỏi, nên làm gì?"]:
    started=time.perf_counter()
    result=worker.decide.remote(build_request(message,characters))
    print(json.dumps({"message":message,"wall_ms":round((time.perf_counter()-started)*1000,2),
        "service_ms":result.get("service_ms"),"answers":result.get("answers")},ensure_ascii=False),flush=True)
