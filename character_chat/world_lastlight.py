"""The town that lost its dawn: authored inventory, puzzles, trades and endings.

All rewards/outcomes are deterministic server transitions. Free chat only narrates;
it never parses model prose into progress. Legacy Moonfall journeys remain separate.
"""
from copy import deepcopy
import uuid

ID="lastlight"
ITEMS=(
 ("key","☼","Chìa Khóa Bình Minh","Dawn Key","Tìm lại một bình minh","Recover a dawn",
  "tavern","Kim trên mặt khóa quán trọ đang trỏ số 6. Xoay kim nửa vòng: nó chỉ số nào?","The inn lock's pointer is on 6. Turn it half a circle: which number will it point to?",
  ("12","3","9"),0,
  ("Nửa vòng là sáu khoảng số.","Half a circle spans six numbers."),
  ("Bắt đầu ở 6, đi thêm sáu khoảng.","Start at six and move six spaces."),
  ("Chọn 12.","Choose 12.")),
 ("mirror","◇","Gương Gọi Tên","Naming Mirror","Tìm tên bị đánh cắp","Find the stolen name",
  "forest","Trên bia ghi: AN, BÌNH, CHÂU. Tấm gương đảo thứ tự ba cái tên. Tên nào ở giữa?","The stone lists AN, BINH, CHAU. The mirror reverses their order. Which name stays in the middle?",
  ("AN","BÌNH / BINH","CHÂU / CHAU"),1,
  ("Đảo thứ tự không có nghĩa là đảo chữ.","Reverse the order, not the letters."),
  ("Ba vị trí đổi thành 3–2–1.","The positions become 3–2–1."),
  ("BÌNH vẫn ở giữa.","BINH stays in the middle.")),
 ("bell","♧","Chuông Không Tiếng","Silent Bell","Lắng nghe điều bị bỏ quên","Hear what was forgotten",
  "tower","Ba dây chuông ghi 2, 4, 8, ?. Mỗi số gấp đôi số trước. Kéo dây mang số nào?","Bell cords read 2, 4, 8, ?. Each number doubles. Which numbered cord should you pull?",
  ("10","12","16"),2,
  ("Quy luật là nhân, không phải cộng hai.","The rule multiplies; it does not add two."),
  ("Lấy 8 nhân với 2.","Multiply eight by two."),
  ("Kéo dây 16.","Pull cord 16.")),
)
HOMES=("square","tavern","tower")

def tr(s,vi,en):return vi if s["language"]=="vi" else en

def seed():
 return {"id":ID,"version":1,"story_mode":ID,"owner":None,"status":"public","rating":"general",
 "title":{"vi":"Thị trấn đánh mất bình minh","en":"The Town That Lost Its Dawn"},
 "pitch":{"vi":"Chuông thứ mười ba sẽ xóa tên cả thị trấn. Ba cổ vật, ba lời nhờ giúp — và một điều bạn không thể cứu tất cả.","en":"The thirteenth bell will erase the town's names. Three relics, three requests—and a choice that cannot save everything."},
 "opening":{"vi":"Bạn tỉnh dậy trên quảng trường. Trời vẫn tối, nhưng mọi chiếc đồng hồ đều chỉ sáu giờ sáng. Tên trên tấm vé trong tay bạn đang phai đi.\n\nMột lá thư không người gửi viết: ‘Khi chuông thứ mười ba vang, chúng ta sẽ quên cả lý do mình ở đây. Tìm ba người còn nhớ. Đừng chọn thay họ — hãy nghe câu chuyện của họ trước.’\n\nNgười dẫn truyện: Hãy gặp người đầu tiên. Bạn có thể trò chuyện, nhận lời nhờ giúp, hoặc hỏi tôi cần làm gì tiếp.",
 "en":"You wake in the square. It is dark, but every clock reads six in the morning. Your name is fading from the ticket in your hand.\n\nAn unsigned letter reads: 'At the thirteenth bell we will forget why we are here. Find those who still remember. Hear their stories before choosing for them.'\n\nNarrator: Meet the first witness. Talk, accept a request, or ask me what to do next."},
 "lore":[{"id":"lastlight_rule","title":{"vi":"Luật của hồi chuông","en":"The bell's rule"},"text":{"vi":"Gợi ý không bị phạt. Chỉ trả lời sai câu đố mới làm vết nứt ký ức tăng lên; sai ba lần sẽ kết thúc chuyến đi. Không có đồng hồ đếm thời gian thật.","en":"Hints are free. Only wrong puzzle answers widen the memory fracture; three mistakes end the journey. There is no real-time countdown."},"scope":"public","unlock":"","canon":True,"keywords":["bell","chuông"]}],
 "narrator_model_id":"","narrator_prompt":""}

def initial(s):
 s["adventure"]={"quests":{},"items":{},"mistakes":0,"hint_level":0,"hint":"","deliveries":[]}
 return s

def room_state(s):
 """Old single-transcript saves migrate into narrator history without guessing recipients."""
 a=s["adventure"]
 if "rooms" not in a:
  a["rooms"]={"narrator":deepcopy(s["history"])}
 for person in s["cast"]:a["rooms"].setdefault("npc:"+person["id"],[])
 a.setdefault("active_room","narrator")
 return a

def room_key(s,actor=None):
 if actor is None:return "narrator"
 key="npc:"+actor
 if key not in room_state(s)["rooms"]:raise ValueError("Unknown NPC room")
 return key

def room_history(s,key=None):
 a=room_state(s)
 return a["rooms"].get(key or a["active_room"],[])

def replace_event_text(s,event_id,text):
 # Narration replaces a committed authored event in both indexes.
 for events in [s["history"],*room_state(s)["rooms"].values()]:
  for event in events:
   if event["id"]==event_id:event.update(text=text,narration="ai")

def persona_snapshot(spec):
 raw=spec.model_dump(mode="json")
 return {key:raw.get(key) for key in ("name","description","system_prompt","identity",
   "personality","speech","support","motivations","goals","values","boundaries",
   "behavior_rules","sample_dialogues","likes","dislikes","persona_knowledge")}


def tasks(s):
 a=s["adventure"]; result=[]
 for i,item in enumerate(ITEMS):
  person=s["cast"][i%len(s["cast"])]
  prior=i==0 or a["quests"].get(ITEMS[i-1][0])=="done"
  status=a["quests"].get(item[0],"available" if prior else "locked")
  home=HOMES[(i%len(s["cast"]))]
  result.append({"id":item[0],"title":tr(s,item[4],item[5]),"giver":person["id"],"giver_name":person["name"],
   "home":home,"target":item[6],"status":status,"ready":status=="found"})
 return result

def contacts(s):
 return [{"id":c["id"],"name":c["name"],"location":HOMES[i],
  "role":tr(s,"Người còn giữ ký ức","A keeper of memory")} for i,c in enumerate(s["cast"])]

def guidance(s):
 if s["ending"]:return {"action":None,"value":"","text":tr(s,"Câu chuyện đã khép lại. Bạn có thể đọc lại hoặc trở về mốc đã lưu.","The story has ended. Read it again or return to a checkpoint.")}
 q=next((q for q in tasks(s) if q["status"] not in ("done","locked")),None)
 if not q:return {"action":"go" if s["location"]!="observatory" else None,"value":"observatory","text":tr(s,"Ba cổ vật đã thức tỉnh. Tới Đài Sao Cũ, lưu mốc rồi chọn cổ vật để trao cho người bạn tin.","Three relics are awake. Reach the observatory, save a checkpoint, then offer a relic to someone you trust.")}
 target=q["home"] if q["status"] in ("available","found") else q["target"]
 if s["location"]!=target:return {"action":"go","value":target,"text":tr(s,"Đi tiếp: ","Next stop: ")+q["title"]}
 if q["status"]=="available":return {"action":"accept","value":q["id"],"text":tr(s,"Gặp ","Meet ")+q["giver_name"]+tr(s," để nghe lời nhờ giúp."," to hear their request.")}
 if q["status"]=="found":return {"action":"give","value":q["id"],"text":tr(s,"Trao cổ vật vừa tìm cho ","Give the recovered relic to ")+q["giver_name"]}
 return {"action":None,"value":"","text":tr(s,"Đọc câu đố, chọn đáp án hoặc xin mẹo. Không cần gõ đúng một câu thần chú.","Read the puzzle, choose an answer or ask for a hint. No exact typed phrase is required.")}

def projection(s):
 a=room_state(s);qs=tasks(s)
 q=next((q for q in qs if q["status"]=="active" and q["target"]==s["location"]),None)
 puzzle=None
 if q:
  item=next(i for i in ITEMS if i[0]==q["id"])
  puzzle={"id":item[0],"question":tr(s,item[7],item[8]),"options":[{"id":str(i),"label":v} for i,v in enumerate(item[9])]}
 items=[]
 for item in ITEMS:
  status=a["items"].get(item[0])
  # Unfound relics do not disclose their descriptions or ending outcome.
  items.append({"id":item[0],"symbol":item[1],"name":tr(s,item[2],item[3]) if status else tr(s,"Cổ vật chưa tìm","Undiscovered relic"),
   "status":status or "unknown","description":tr(s,"Đã phục hồi; có thể chọn cho hồi kết.","Restored; available for the final choice.") if status=="ready" else tr(s,"Mang về người giao nhiệm vụ để phục hồi.","Return it to the quest giver for restoration.") if status=="raw" else ""})
 return {"chapter":tr(s,"Ba lời nhờ giúp · Một hồi kết","Three requests · One ending"),"contacts":contacts(s),"quests":qs,
 "next":guidance(s),"encounter":s.get("encounter") or s["cast"][0]["id"],"can_return":False,"hint":a["hint"],
 "hint_level":a["hint_level"],"completed":sum(q["status"]=="done" for q in qs),"tutorial":False,
 "active_room":a["active_room"],"messages":room_history(s),
 "rooms":[{"id":"narrator","name":tr(s,"Người dẫn truyện","Narrator"),"npc_id":None,"count":len(a["rooms"]["narrator"])}]+[
   {"id":"npc:"+c["id"],"name":c["name"],"npc_id":c["id"],"count":len(a["rooms"]["npc:"+c["id"]])} for c in s["cast"]],
 "items":items,"puzzle":puzzle,"mistakes":a["mistakes"],"deliveries":a["deliveries"],
 "final_ready":all(q["status"]=="done" for q in qs)}

def finish(s,item,person=None):
 names=", ".join(c["name"] for c in s["cast"])
 if item=="loss":
  title=tr(s,"Những cái tên trong sương","Names in the Mist")
  paragraphs=[tr(s,"Hồi chuông thứ mười ba vang lên trước khi những mảnh ký ức nối lại. Tên trên tấm vé biến mất. Bạn vẫn nhận ra bàn tay người đồng hành, nhưng không còn nhớ lần đầu mình gặp họ.","The thirteenth bell rings before the fragments reconnect. Your ticket loses its name. You recognise a companion's hand, but not your first meeting."),
   tr(s,"Không ai trách bạn. Trước khi thị trấn tan vào sương, một giọng nói nhắc: ‘Lần sau, hãy hỏi thêm một câu.’ Một mốc đã lưu vẫn có thể đưa bạn trở lại.","Nobody blames you. As the town dissolves into mist, a voice says, 'Next time, ask one more question.' A saved checkpoint can still bring you back.")]
  outcome="loss"
 else:
  titles={"key":("Bình minh không còn bạn","A Dawn Without You"),"mirror":("Thị trấn nhớ tên mình","The Town Remembers Its Name"),"bell":("Chuyến tàu cuối cùng","The Last Train")}
  title=tr(s,*titles[item]);who=person["name"]
  body={
   "key":(" xoay Chìa Khóa Bình Minh. Cánh cửa phía đông mở ra; mặt trời trở lại, nhưng thị trấn phải trả bằng ký ức về người đã cứu nó. Những người bạn đã gặp bước ngang qua bạn như một người lạ. Bạn vẫn giữ tấm vé không tên — và biết họ còn sống.",
          " turns the Dawn Key. The eastern door opens and sunlight returns, at the cost of the town's memory of its rescuer. Your friends pass you like a stranger. You keep the nameless ticket—and know they are alive."),
   "mirror":(" nâng Gương Gọi Tên. Trong gương không có thủ phạm, chỉ có những người đã giấu nỗi đau vì sợ bị quên. Họ gọi tên nhau cho đến khi hồi chuông dừng lại. Bình minh đến muộn, thị trấn vẫn còn những vết nứt, nhưng không ai phải biến mất.",
             " raises the Naming Mirror. It reveals no villain, only people who hid their pain for fear of being forgotten. They speak each other's names until the bell stops. Dawn comes late; the town keeps its scars, but nobody disappears."),
   "bell":(" rung chiếc Chuông Không Tiếng. Một chuyến tàu hiện ra trên đường ray bỏ hoang. Bạn dẫn mọi người rời khỏi thị trấn; những ngôi nhà hóa thành sao sau lưng. Không cứu được nơi chốn, nhưng những con người và câu chuyện của họ còn tiếp tục.",
           " rings the Silent Bell. A train appears on the abandoned track. You lead everyone away as the houses become stars behind you. The place is lost, but its people and their stories continue.")
  }
  paragraphs=[who+tr(s,*body[item]),tr(s,"Trên tấm vé, bạn viết lại tên những người đã cùng mình đi qua đêm: ","On the ticket, you write the names of those who shared the night: ")+names+".",
   tr(s,"Bạn không chọn được một thế giới hoàn hảo. Bạn đã chọn điều mình sẵn sàng bảo vệ.","You did not choose a perfect world. You chose what you were willing to protect.")]
  outcome="win" if item=="mirror" else "bittersweet"
 s["ending"]={"id":item,"title":title,"outcome":outcome,"paragraphs":paragraphs}
 return "\n\n".join([title,*paragraphs])

def advance(state,action,value="",speaker=None):
 s=deepcopy(state);a=room_state(s);name="narrator";g=guidance(s);person=next((c for c in s["cast"] if c["id"]==speaker),None)
 if action=="enter":
  if value not in a["rooms"]:raise ValueError("Unknown conversation room")
  a["active_room"]=value
  if value!="narrator":
   ident=value[4:]
   s["encounter"]=ident
   if s["location"]!="observatory":
    s["location"]=next(p["location"] for p in contacts(s) if p["id"]==ident)
  return s,{"id":uuid.uuid4().hex,"speaker":"narrator","kind":"enter","text":"","room":value}
 if s["ending"]:raise ValueError("The story has ended. Return to a checkpoint.")
 target_room=room_key(s,speaker) if action in ("say","talk","interview") else "narrator"
 qs=tasks(s)
 if action in ("go","travel","visit"):
  from .world_engine import LOCATIONS
  from .world_chapter import route
  dest=next((p["location"] for p in contacts(s) if p["id"]==value),None) if action=="visit" else value
  if not dest:raise ValueError("Unknown encounter")
  route(s,dest,LOCATIONS);s["location"]=dest
  if action=="visit":s["encounter"]=value;person=next(c for c in s["cast"] if c["id"]==value)
  text=tr(s,"Bạn bước qua những ngôi nhà có tên đang phai. ","You pass houses whose names are fading. ")+(tr(s,"Người chờ bạn là ","Waiting here is ")+person["name"]+"." if action=="visit" else guidance(s)["text"])
 elif action=="accept":
  q=next((q for q in qs if q["id"]==value and q["status"]=="available"),None)
  if not q or s["location"]!=q["home"]:raise ValueError("Meet the available quest giver first.")
  s["encounter"]=q["giver"];name=q["giver_name"];a["quests"][value]="active";target_room=room_key(s,q["giver"])
  requests={"key":("Chiếc đồng hồ quán trọ giữ một mảnh chìa khóa. Mang nó về cho tôi; tôi sẽ đổi một ký ức để nó hoạt động.","The inn clock holds a key fragment. Bring it to me; I will exchange a memory to make it work."),
  "mirror":("Trong rừng có tấm gương bị vỡ. Hãy tìm cái tên không đổi khi mọi thứ đảo ngược, rồi mang gương về. Tôi sẽ trả lại điều mình từng giấu.","A broken mirror waits in the forest. Find the name that survives reversal and bring it back. I will return what I once hid."),
  "bell":("Tháp có chiếc chuông không kêu. Đọc đúng nhịp số để tháo nó, rồi đưa tôi. Ta có thể nghe một con đường mà mắt không thấy.","The tower holds a silent bell. Read the number rhythm to release it, then bring it to me. We may hear a path no eye can see.")}
  text=tr(s,*requests[value]);a.update(hint_level=0,hint="")
 elif action=="solve":
  ident,sep,answer=value.partition(":")
  q=next((q for q in qs if q["id"]==ident and q["status"]=="active"),None)
  item=next((i for i in ITEMS if i[0]==ident),None)
  if not sep or not q or s["location"]!=q["target"] or answer not in ("0","1","2"):raise ValueError("No matching puzzle here.")
  if int(answer)==item[10]:
   a["quests"][ident]="found";a["items"][ident]="raw"
   text=tr(s,"Lớp niêm phong mở ra. Bạn nhận ","The seal opens. You receive ")+tr(s,item[2],item[3])+tr(s," — cổ vật còn ngủ. Hãy mang về người giao nhiệm vụ.","—the relic is still asleep. Return it to the quest giver.")
   a.update(hint_level=0,hint="")
  else:
   a["mistakes"]+=1
   text=finish(s,"loss") if a["mistakes"]>=3 else tr(s,"Một vết nứt chạy qua tấm vé. Chưa đúng; bạn có thể xin mẹo trước khi thử tiếp.","A crack crosses your ticket. Not yet; ask for a hint before trying again.")
 elif action=="hint":
  target_room=room_key(s,speaker)
  name=person["name"] if person else "narrator"
  q=next((q for q in qs if q["status"]=="active"),None)
  level=min(3,a["hint_level"]+1);a["hint_level"]=level
  item=next((i for i in ITEMS if q and i[0]==q["id"]),None)
  text=tr(s,*item[10+level]) if item else g["text"]
  if person and not q:
   next_q=next((x for x in qs if x["status"]=="available"),None)
   if next_q and next_q["giver"]==speaker:
    text=tr(s,"Tôi có một lời nhờ giúp. Nếu bạn sẵn lòng, hãy nghe và nhận nhiệm vụ để chúng ta bắt đầu.","I have a request. If you are willing, hear it and accept so we can begin.")
  a["hint"]=text
 elif action=="give":
  q=next((q for q in qs if q["id"]==value and q["status"]=="found"),None)
  if not q or s["location"]!=q["home"] or speaker!=q["giver"] or a["items"].get(value)!="raw":raise ValueError("Bring this relic to its quest giver and select that person.")
  name=q["giver_name"];target_room=room_key(s,q["giver"]);a["items"][value]="ready";a["quests"][value]="done"
  a["deliveries"].append({"item":value,"npc":speaker})
  s["trust"][speaker]=min(100,s["trust"][speaker]+2)
  exchanges={
   "key":("Họ nhớ lại lần đầu được đón vào thị trấn. Ánh vàng chảy vào chìa khóa. ‘Nó sẽ mở bình minh, nhưng người mở cửa có thể bị quên.’ Họ trả lại cổ vật đã thức tỉnh.","They recall first being welcomed into town. Gold flows into the key. 'It will open dawn, but the one who opens the door may be forgotten.' They return the awakened relic."),
   "mirror":("Họ lau gương và thú nhận: không ai đánh cắp bình minh. Thị trấn đã cùng chọn quên một đêm đau buồn, rồi quên cả tên mình. Gương có thể trả ký ức lại — nếu mọi người dám đối diện. Bạn nhận gương đã thức tỉnh.","They clean the mirror and admit that nobody stole dawn. The town chose to forget a painful night, then forgot its own name. The mirror can restore memory—if people dare to face it. You receive the awakened mirror."),
   "bell":("Họ không gõ chuông, chỉ lắng nghe. Từ chiếc chuông im lặng vọng ra tiếng tàu: có lối thoát dành cho tất cả, nhưng không mang theo được thị trấn. Họ trả lại cổ vật và nhờ bạn đừng chọn hộ bất kỳ ai.","They do not strike the bell; they listen. A train echoes inside it: there is an escape for everyone, but the town cannot come along. They return the relic and ask you not to choose another person's life for them.")
  }
  text=tr(s,"Bạn trao cổ vật cho ","You hand the relic to ")+name+". "+tr(s,*exchanges[value])
 elif action=="offer":
  if s["location"]!="observatory" or not all(q["status"]=="done" for q in qs) or a["items"].get(value)!="ready" or not person:raise ValueError("Bring the restored relics to the observatory and choose a recipient.")
  a["items"][value]="spent";text=finish(s,value,person)
 elif action in ("say","talk","interview"):
  if person and s["location"]!="observatory" and s["location"]!=next(p["location"] for p in contacts(s) if p["id"]==person["id"]):raise ValueError("Visit this character before talking.")
  if action=="say" and not value.strip():raise ValueError("Empty message")
  name=person["name"] if person else "narrator"
  text=(tr(s,"Tôi nhớ cảm giác được ai đó gọi đúng tên. Bạn không cần vội chọn kết thúc; nếu muốn, tôi sẽ ở đây nghe bạn kể. ","I remember how it feels to be called by name. You need not rush the ending; I can stay and listen. ") if person and value=="personal" else tr(s,"Chúng ta chưa biết ai phải trả giá cho bình minh. Hãy giữ điều đã hứa, và đừng ngại hỏi mẹo. ","We do not yet know who must pay for dawn. Keep your promises, and ask for a hint whenever you need one. "))+g["text"]
 elif action=="wait":text=tr(s,"Bạn ngồi nghỉ. Không có thời gian thật đếm ngược; người đồng hành chờ bạn.","You rest. No real-time clock is counting down; your companions wait.")
 else:raise ValueError("This action is unavailable in this story.")
 if action!="hint":s["turn"]+=1
 s["phase"]=tr(s,"Vết nứt ký ức ","Memory fractures ")+str(a["mistakes"])+"/3"
 a["active_room"]=target_room
 ev={"id":uuid.uuid4().hex,"speaker":name,"kind":action,"room":target_room,"text":text,"turn":s["turn"],"roll":None,"narration":"rules"}
 caption=value if action=="say" else tr(s,{"solve":"Thử đáp án","give":"Trao cổ vật để phục hồi","offer":"Chọn con đường cho hồi kết","hint":"Xin mẹo","accept":"Nhận lời nhờ giúp","visit":"Gặp nhân vật","go":"Đi tới địa điểm","talk":"Trò chuyện","wait":"Nghỉ chân"}.get(action,action),
 {"solve":"Try an answer","give":"Exchange and restore the relic","offer":"Choose an ending path","hint":"Ask for a hint","accept":"Accept the request","visit":"Meet a character","go":"Travel","talk":"Talk","wait":"Rest"}.get(action,action))
 user_event={"id":uuid.uuid4().hex,"speaker":"user","kind":"user","room":target_room,"text":caption}
 a["rooms"][target_room]=(a["rooms"][target_room]+[user_event,ev])[-80:]
 s["history"]=(s["history"]+[user_event,ev])[-80:]
 s["journal"]=(s["journal"]+[{"id":ev["id"],"turn":s["turn"],"text":text,"location":s["location"]}])[-100:]
 return s,ev
