import atexit, json, os, time
import requests

base=os.getenv("CHARACTER_CHAT_URL","https://nguyenthanhcongloi332004--character-chat-web.modal.run")
session=requests.Session();session.headers.update({"X-Demo-User-Id":"smoke-"+str(int(time.time()))})
created_characters=[]
def call(path,method="GET",body=None):
    response=session.request(method,base+path,json=body,timeout=600)
    response.raise_for_status();return response.json()

def cleanup():
    for character_id in reversed(created_characters):
        try:session.delete(base+f"/v1/characters/{character_id}",timeout=120)
        except Exception:pass
atexit.register(cleanup)

assert call("/health")["status"]=="ok"
presets=call("/v1/presets")["characters"]
mia=call("/v1/characters","POST",next(x for x in presets if x["preset_type"]=="entertainment_lover"))
leo=call("/v1/characters","POST",next(x for x in presets if x["preset_type"]=="ideal_boyfriend"))
created_characters.extend([mia["id"],leo["id"]])
single=call("/v1/rooms","POST",{"character_ids":[mia["id"]]})
group=call("/v1/rooms","POST",{"character_ids":[mia["id"],leo["id"]]})
reply=call(f'/v1/rooms/{single["id"]}/messages',"POST",{"message":"Chào Mia, hôm nay mình hơi mệt."})
assert reply["responses"] and reply["responses"][0]["text"]
print("single:",reply["responses"][0]["text"])
single_events=[]
with session.post(base+f'/v1/rooms/{single["id"]}/messages/stream',json={"message":"Mia ơi, bạn đang làm gì vậy?","speaker_mode":"auto"},stream=True,timeout=600) as response:
    response.raise_for_status()
    for line in response.iter_lines(decode_unicode=True):
        if line.startswith("event:"):single_events.append(line.split(":",1)[1].strip())
assert single_events==["user_message","typing","character_message","done"]
print("single stream events:",single_events)
reply=call(f'/v1/rooms/{group["id"]}/messages',"POST",{"message":"@Leo kể một câu đùa ngắn nhé"})
assert len(reply["responses"])==1 and reply["responses"][0]["character_id"]==leo["id"]
print("group:",reply["responses"][0]["text"])
events=[]
with session.post(base+f'/v1/rooms/{group["id"]}/messages/stream',json={"message":"Cả hai chào mình một câu nhé","speaker_mode":"everyone"},stream=True,timeout=600) as response:
    response.raise_for_status()
    for line in response.iter_lines(decode_unicode=True):
        if line.startswith("event:"):events.append(line.split(":",1)[1].strip())
assert events[0]=="user_message"
assert events.count("typing")==2 and events.count("character_message")==2
assert events.index("typing")<events.index("character_message")<events.index("typing",events.index("typing")+1)
print("stream events:",events)
print("SMOKE PASSED",base)
