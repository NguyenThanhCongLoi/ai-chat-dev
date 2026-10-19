"""Moonfall Academy: deterministic social story. No provider or database I/O."""
from copy import deepcopy
import time
import json
import uuid

PLACES = (
 ("library","Thư viện ánh trăng","Moonlit Library","✧",48,40),
 ("garden","Vườn ngân nguyệt","Moon Garden","❀",25,70),
 ("hall","Đại sảnh","Academy Hall","♜",75,69),
 ("dorm","Ký túc xá","Dormitory","⌂",17,32),
 ("tower","Đài thiên văn","Observatory","☾",77,23),
)
ITEMS = (
 ("letter","✉","Thư không người gửi","Unsigned Letter"),
 ("flower","❀","Hoa lưu quang","Starlight Flower"),
 ("lens","◇","Thấu kính ký ức","Memory Lens"),
 ("tea","♧","Trà nguyệt quế","Moon Tea"),
 ("ticket","☽","Vé lễ hội","Festival Ticket"),
)
MISSIONS = (
 ("letter","Lá thư dưới ánh trăng","A Letter in Moonlight","library"),
 ("garden","Người giữ khu vườn","The Garden Keeper","garden"),
 ("truth","Đêm không ai bị lãng quên","A Night Without Forgotten Names","tower"),
)
EVENTS = (
 ("arrival","Một người đang chờ bạn bên thư viện.","Someone is waiting by the library."),
 ("letter","Một lá thư bị giấu trong sách trả muộn.","An unsigned letter waits inside an overdue book."),
 ("rumour","Hai nhân chứng kể hai phiên bản về đêm mất điện.","Two witnesses remember the blackout differently."),
 ("garden","Khu vườn ngừng phát sáng từ đêm ấy.","The garden has been dark since that night."),
 ("tea","Một tách trà được để dành cho bạn.","Someone saved you a cup of tea."),
 ("flower","Một bông hoa đáp lại ký ức được gọi tên.","A flower responds to a remembered name."),
 ("lens","Thấu kính phản chiếu người bị bỏ quên.","The lens reflects a forgotten friend."),
 ("tower","Đài thiên văn mở. Các nhân chứng chờ bạn.","The observatory is open. The witnesses await you."),
 ("festival","Lễ hội có thể bắt đầu, nhưng cần một quyết định.","The festival can begin, but a decision remains."),
 ("tomorrow","Ngày mai, cùng viết tên những người vắng mặt.","Tomorrow, help write the names of those absent."),
)

def tr(s, vi, en):
 return vi if s["language"] == "vi" else en

def pair(a,b):
 return "pair:"+json.dumps(sorted((a,b)),separators=(",",":"))

def fresh(owner, ids, language="vi", title="Moonfall Academy"):
 s=dict(id=uuid.uuid4().hex,owner=owner,language=language,title=title,
  revision=0,day=1,location="library",turn=0,members=list(ids),
  unlocked=["library","garden","hall","dorm"],completed=[],inventory=["tea"],
  discoveries=[],memories=[],scenes={},timeline=[],events=["arrival"],
  active_event="arrival",ending=None,last_seen=int(time.time()),receipts=[],relationships={})
 for a in ids:s["relationships"]["user:"+a]=dict(trust=20,affinity=20,respect=20,rivalry=0)
 for i,a in enumerate(ids):
  for b in ids[i+1:]:s["relationships"][pair(a,b)]=dict(trust=30,affinity=30,respect=30,rivalry=10)
 observe(s,"arrival",tr(s,"Bạn đến học viện trước lễ hội trăng.","You arrived before the moon festival."),ids,"story")
 return s

def positions(s):
 # One location per character. Legacy saves derive the same initial placement.
 initial={a:("library" if i<2 else "garden" if i==2 else "hall") for i,a in enumerate(s["members"])}
 return {a:s.get("positions",{}).get(a,place) for a,place in initial.items()}

def present(s, location=None):
 loc=location or s["location"]
 return [a for a,place in positions(s).items() if place==loc]

def observe(s,source,content,witnesses,kind="story"):
 m=dict(id=uuid.uuid4().hex,source=source,content=content,witnesses=list(witnesses),
  location=s["location"],day=s["day"],kind=kind,canon=True,importance=.8)
 s["memories"].append(m);s["timeline"].append(deepcopy(m))
 s["memories"]=s["memories"][-120:];s["timeline"]=s["timeline"][-120:]

def event(s,key):
 if key not in s["events"]:s["events"].append(key)
 s["active_event"]=key

def bond(s,actor,**changes):
 rel=s["relationships"]["user:"+actor]
 for k,d in changes.items():rel[k]=max(0,min(100,rel[k]+d))

def secrets(s,actor):
 """Only authorized secret text may leave the evaluator."""
 i=s["members"].index(actor)
 details=(
  ("Tôi đã cất lá thư để người nhận có thể tự quyết định khi nào trở về.","I kept the letter so its recipient could choose when to return."),
  ("Tôi từng gieo những bông hoa ghi nhớ tên người vắng mặt.","I planted flowers that remember absent friends."),
  ("Tôi sửa thấu kính để giữ một ký ức khỏi bị xóa.","I repaired the lens to preserve a fading memory."),
  ("Tôi giữ một chiếc vé lễ hội cho người chưa trở lại.","I saved a festival ticket for someone who hasn't returned."),
 )
 core=(
  ("Tôi giấu danh tính người bạn theo chính lời nhờ của họ.","I hid our friend's identity at their own request."),
  ("Khu vườn tắt sáng vì chúng tôi không còn gọi tên người bạn ấy.","The garden dimmed because we stopped naming our friend."),
  ("Thấu kính không tìm thủ phạm; nó lưu lời hẹn của cả nhóm.","The lens reveals no culprit; it holds our shared promise."),
  ("Lễ hội chỉ trọn vẹn nếu mọi người được chọn cách kể ký ức của mình.","The festival is whole only if everyone chooses how their memory is told."),
 )
 result=[]
 if s["relationships"]["user:"+actor]["trust"]>=30:
  result.append(dict(id=actor+":personal",text=tr(s,*details[i%4]),tier="personal"))
 if "garden" in s["completed"]:
  result.append(dict(id=actor+":core",text=tr(s,*core[i%4]),tier="secret"))
 return result

def choose_speakers(s,text,names):
 candidates=present(s)
 mentioned=[a for a in candidates if names.get(a,a).casefold() in text.casefold()]
 if mentioned:return mentioned[:2]
 last=next((e["speaker"] for e in reversed(s["scenes"].get(s["location"],[])) if e["speaker"] in candidates),None)
 return [next((a for a in candidates if a!=last),candidates[0])] if candidates else []

def context(s,actor):
 # Filter BEFORE ranking and token budgeting. Never include another scene blindly.
 result=dict(world=s["title"],day=s["day"],language=s["language"],location=s["location"],
  memories=[m for m in s["memories"] if actor in m["witnesses"]][-10:],
  secrets=secrets(s,actor),
  relationships={k:v for k,v in s["relationships"].items() if k=="user:"+actor or k.startswith("pair:") and actor in json.loads(k[5:])},
  conversation=[e for e in s["scenes"].get(s["location"],[]) if actor in e["witnesses"]][-12:])
 while len(json.dumps(result,ensure_ascii=False))>9000:
  if result["memories"]:result["memories"].pop(0)
  elif len(result["conversation"])>1:result["conversation"].pop(0)
  else:break
 return result

def line(s,speaker,text,mode="authored"):
 s["scenes"].setdefault(s["location"],[]).append(dict(id=uuid.uuid4().hex,speaker=speaker,
  text=text,witnesses=present(s),mode=mode))
 s["scenes"][s["location"]]=s["scenes"][s["location"]][-60:]

def advance(original,action,value="",actor=""):
 s=deepcopy(original);w=present(s)
 if action=="visit":
  if value not in s["unlocked"]:raise ValueError("Location is locked")
  s["positions"]=positions(s)
  if value=="tower":
   s["positions"]={a:"tower" for a in s["members"]}
  elif not present(s,value):
   # A companion follows the player into an empty scene rather than appearing twice.
   s["positions"][s["members"][0]]=value
  s["location"]=value
 elif action=="hint":
  line(s,"narrator",tr(s,
   "Thư viện: tìm thư và nghe cả hai bên. Khu vườn: khôi phục ký ức. Khi đài thiên văn mở, mang bằng chứng đến đó.",
   "Library: find the letter and hear both sides. Garden: restore the memory. When the observatory opens, take the evidence there."))
 elif action=="choice":
  if value=="investigate" and s["location"]=="library" and "letter" not in s["completed"]:
   s["completed"].append("letter");s["inventory"].append("letter")
   for key in ("letter","rumour","garden"):event(s,key)
   for a in w:bond(s,a,trust=6)
   observe(s,"letter",tr(s,"Bạn tìm thấy lá thư, nhưng chọn nghe nhân chứng trước khi kết tội.","You found the letter and chose to hear witnesses before blaming anyone."),w,"discovery")
   line(s,w[0],tr(s,"Đây không phải lời thú tội. Nhìn vết phấn hoa trên mép thư — người viết đã đến khu vườn.","This isn't a confession. Look at the pollen. The writer visited the garden."))
  elif value in ("reconcile","accuse") and s["location"]=="library" and "letter" in s["completed"] and "debate" not in s["discoveries"]:
   s["discoveries"].append("debate")
   for a in w:bond(s,a,trust=5 if value=="reconcile" else -5,rivalry=0 if value=="reconcile" else 5)
   if len(w)>1:
    rel=s["relationships"][pair(*w[:2])]
    rel["trust"]=min(100,rel["trust"]+(8 if value=="reconcile" else 0))
    rel["rivalry"]=max(0,min(100,rel["rivalry"]+(-5 if value=="reconcile" else 8)))
   observe(s,value,tr(s,"Bạn chọn hòa giải." if value=="reconcile" else "Bạn yêu cầu đối chất khi chưa đủ bằng chứng.",
    "You chose reconciliation." if value=="reconcile" else "You confronted the witnesses before gathering all evidence."),w,"relationship")
   line(s,w[-1],tr(s,"Nếu cùng tìm hiểu, có lẽ chúng ta sẽ nhớ ra điều đã bỏ lỡ.","If we look together, perhaps we'll remember what we missed."))
  elif value=="restore" and s["location"]=="garden" and "letter" in s["completed"] and "garden" not in s["completed"]:
   s["completed"].append("garden");s["inventory"]+=["flower","lens"];s["unlocked"].append("tower")
   for key in ("flower","lens","tower","festival"):event(s,key)
   for a in w:bond(s,a,trust=8,respect=4)
   observe(s,"garden",tr(s,"Bạn gọi tên người vắng mặt. Khu vườn phát sáng; đài thiên văn mở cửa.","You named the absent friend. The garden glowed and the observatory opened."),w,"discovery")
   line(s,w[0],tr(s,"Chúng tôi không đánh mất ánh trăng. Chúng tôi quên người từng cùng ngắm nó. Mang thấu kính lên đài thiên văn nhé.","We didn't lose the moonlight. We forgot who used to watch it with us. Bring the lens to the observatory."))
  elif value in ("remember","protect") and s["location"]=="tower" and "garden" in s["completed"] and not s["ending"]:
   s["completed"].append("truth");s["inventory"].append("ticket");s["ending"]=value
   observe(s,"ending",tr(s,"Bạn chia sẻ ký ức với sự đồng ý của nhân chứng." if value=="remember" else "Bạn giữ kín danh tính và cùng mọi người viết lại lời hẹn.",
    "With the witnesses' consent, you shared the memory." if value=="remember" else "You protected the identity and renewed everyone's promise."),w)
   event(s,"tomorrow")
   line(s,"narrator",tr(s,
    "Những cái tên được đọc lên dưới ánh trăng. Các nhân chứng tự kể phần ký ức của mình; không ai bị buộc phải tha thứ. Ngày mai, chiếc ghế trống sẽ mang một cái tên.\n\nChương một khép lại: một ký ức được chia sẻ, một tình bạn được chọn." if value=="remember" else "Bạn gấp lá thư và trả lại cho người giữ nó. Giữa vòng bạn bè, một chiếc ghế trống được đặt lại mà không cần công khai danh tính. Có những lời hẹn được giữ bằng sự im lặng.\n\nChương một khép lại: một bí mật được bảo vệ, một cánh cửa vẫn mở.",
    "The witnesses speak their memories beneath the moon. No one is forced to forgive. Tomorrow, the empty chair will carry a name.\n\nChapter one closes: a memory shared, a friendship chosen." if value=="remember" else "You fold the letter and return it to its keeper. An empty chair returns to the circle without revealing an identity. Some promises are kept in silence.\n\nChapter one closes: a secret protected, a door left open."))
   s["ending_text"]=s["scenes"]["tower"][-1]["text"]

  else:raise ValueError("Choice unavailable or already resolved")
 elif action=="gift":
  if actor not in w or value not in s["inventory"] or value not in ("tea","flower"):raise ValueError("Gift unavailable")
  s["inventory"].remove(value);bond(s,actor,trust=6,affinity=8);event(s,"tea")
  observe(s,"gift",tr(s,"Bạn chia sẻ một món quà nhỏ trong khoảnh khắc yên tĩnh.","You shared a small gift in a quiet moment."),[actor],"relationship")
  line(s,actor,tr(s,"Cảm ơn. Ngồi lại một chút nhé? Không phải chuyện gì cũng cần trở thành nhiệm vụ.","Thank you. Stay a little? Not everything has to become a quest."))
 else:raise ValueError("Unknown action")
 if action not in ("visit","hint"):s["turn"]+=1
 return s

def projection(s,actors):
 names={a["id"]:a for a in actors};done=s["completed"];choices=[]
 if s["location"]=="library":
  if "letter" not in done:choices=[("investigate","Khám phá lá thư","Examine the letter")]
  elif "debate" not in s["discoveries"]:choices=[("reconcile","Nghe cả hai người","Hear both sides"),("accuse","Yêu cầu lời giải thích","Demand an explanation")]
 if s["location"]=="garden" and "letter" in done and "garden" not in done:choices=[("restore","Gọi tên người bị lãng quên","Remember the absent friend")]
 if s["location"]=="tower" and not s["ending"]:choices=[("remember","Chia sẻ ký ức cùng mọi người","Share the memory together"),("protect","Giữ kín danh tính người bạn","Protect the friend's identity")]
 return dict(id=s["id"],revision=s["revision"],title=s["title"],language=s["language"],day=s["day"],
  location=s["location"],turn=s["turn"],ending=s["ending"],ending_text=s.get("ending_text"),progress=len(done)*100//3,
  characters=[dict(**names.get(a,dict(id=a,name="Unavailable character",origin="unknown")),
   location=positions(s)[a],bond=tr(s,"Thân thiết","Close") if s["relationships"]["user:"+a]["trust"]>=35 else tr(s,"Đang làm quen","Getting acquainted"),
   trust=s["relationships"]["user:"+a]["trust"],secrets=secrets(s,a)) for a in s["members"]],
  places=[dict(id=p[0],name=tr(s,p[1],p[2]),symbol=p[3],x=p[4],y=p[5],locked=p[0] not in s["unlocked"],
   present=present(s,p[0]),event=p[0]==("library" if "letter" not in done else "garden" if "garden" not in done else "tower")) for p in PLACES],
  present=present(s),messages=s["scenes"].get(s["location"],[]),
  choices=[dict(id=c[0],label=tr(s,c[1],c[2])) for c in choices],
  missions=[dict(id=m[0],title=tr(s,m[1],m[2]),location=m[3],status="completed" if m[0] in done else "active" if i==len(done) else "locked") for i,m in enumerate(MISSIONS)],
  inventory=[dict(id=i[0],symbol=i[1],name=tr(s,i[2],i[3]),giftable=i[0] in ("tea","flower")) for i in ITEMS if i[0] in s["inventory"]],
  timeline=s["timeline"],event=next(tr(s,e[1],e[2]) for e in EVENTS if e[0]==s["active_event"]),
  relationship_pairs=[dict(people=json.loads(k[5:]),**v) for k,v in s["relationships"].items() if k.startswith("pair:") and all(a in s["members"] for a in json.loads(k[5:]))])
