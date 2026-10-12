"""Dedicated Laya decision worker; no public endpoint or product database."""
import modal
app=modal.App("character-chat-group-router")
cache=modal.Volume.from_name("character-chat-group-router-models",create_if_missing=True)
image=(modal.Image.debian_slim(python_version="3.12")
    .pip_install("laya==0.3.20","torch==2.5.1","transformers==4.57.3","huggingface_hub>=0.34")
    .env({"HF_HOME":"/models/huggingface","USE_TF":"0","TOKENIZERS_PARALLELISM":"false"}))

@app.cls(image=image,gpu="T4",volumes={"/models":cache},
         timeout=120,scaledown_window=2,min_containers=0,max_containers=1)
class GroupRouter:
    @modal.enter()
    def load(self):
        import laya
        self.model=laya.load("convaiinnovations/laya",subfolder="multilingual",device="cuda")
        cache.commit()

    @modal.method()
    def decide(self,payload:dict):
        import time
        if not isinstance(payload.get("questions"),dict) or not 1<=len(payload["questions"])<=6:
            raise ValueError("Expected 1 to 6 questions")
        started=time.perf_counter()
        result=self.model.predict(payload.get("state",{}),payload["questions"],max_len=4096)
        return {**result,"service_ms":round((time.perf_counter()-started)*1000,2),
                "model":"laya-multilingual","device":"T4"}

@app.local_entrypoint()
def test():
    import time,json
    from character_chat.group_decision import build_request
    from character_chat.schemas import CharacterSpec,Identity
    characters=[
        CharacterSpec(id="work",name="Morgan",description="Career and business advisor",identity=Identity(role="career advisor")),
        CharacterSpec(id="art",name="Luna",description="Creative music and art specialist",identity=Identity(role="artist")),
        CharacterSpec(id="health",name="Mira",description="Health and wellbeing specialist",identity=Identity(role="doctor")),
    ]
    worker=GroupRouter()
    for message in ["Mình muốn đổi công việc nhưng vẫn theo đuổi âm nhạc, nên bắt đầu thế nào?",
                    "Tôi bị mất ngủ và mệt mỏi, nên làm gì?"]:
        started=time.perf_counter()
        result=worker.decide.remote(build_request(message,characters))
        print(json.dumps({"message":message,"wall_ms":round((time.perf_counter()-started)*1000,2),
                          "service_ms":result.get("service_ms"),"answers":result.get("answers")},ensure_ascii=False))
