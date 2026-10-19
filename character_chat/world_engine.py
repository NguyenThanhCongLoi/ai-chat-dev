"""Deterministic CPU story state; AI narrates committed events, never changes facts."""
from copy import deepcopy
import secrets
import uuid
import unicodedata
from . import world_chapter as chapter
from . import world_lastlight as lastlight

SUPPORTED_LANGUAGES = ("vi", "en")
LOCATIONS = [
    ("square", "Quảng trường Ngân Nguyệt", "Moonlit Square", "✧", 50, 77, ["tavern", "tower", "forest"]),
    ("tavern", "Quán trọ Cánh Hoa", "Petal Inn", "❋", 18, 50, ["square", "forest"]),
    ("tower", "Tháp Trăng", "Moon Tower", "♜", 80, 47, ["square", "observatory"]),
    ("forest", "Rừng Thì Thầm", "Whispering Forest", "♧", 27, 18, ["square", "tavern", "observatory"]),
    ("observatory", "Đài Sao Cũ", "Old Observatory", "☾", 72, 12, ["tower", "forest"]),
]
FINDINGS = {
    "vi": [
        ("Dấu sáp xanh", "Dấu sáp xanh thuộc kho lưu trữ, không phải túi của người lữ khách đang bị nghi ngờ."),
        ("Lời người giữ đèn", "Người giữ đèn thấy một bóng áo trắng mang chiếc hộp lên đài sao trước hồi chuông. Bạn vừa nghe riêng lời chứng này."),
        ("Trang nghi lễ", "Nguyệt Thạch giữ lời nguyền ngủ yên. Mang nó về sai lúc có thể làm phong ấn suy yếu."),
        ("Mảnh gương ký ức", "Trong gương, người mang chiếc hộp đang bảo vệ một đứa trẻ khỏi ánh trăng. Có thể đây là một cuộc giải cứu."),
        ("Lời nhắn cuối", "Chiếc hộp cần ít nhất ba lời chứng trước khi được mở. Người gửi muốn bạn tự kiểm tra, không tin họ vô điều kiện."),
    ],
    "en": [
        ("Blue wax seal", "The blue seal belongs to the archive, not the suspected traveller's bag."),
        ("The lamplighter's account", "The lamplighter saw a white cloak carrying the box to the observatory before the bell. You heard this account privately."),
        ("A ritual page", "The Moonstone keeps a curse asleep. Returning it at the wrong time could weaken the seal."),
        ("A memory mirror", "The person carrying the box is shielding a child from moonlight. This might be a rescue."),
        ("The final note", "The box needs at least three pieces of evidence before opening. The writer asks you to investigate, not trust blindly."),
    ],
}
def seed():
    return {"id":"moonfall", "version":1, "owner":None, "status":"public", "rating":"general",
        "title":{"vi":"Lời hẹn dưới trăng","en":"A Promise Beneath the Moon"},
        "pitch":{"vi":"Một viên đá mất tích. Năm lời kể. Bạn sẽ tin ai?","en":"A missing stone. Five accounts. Who will you trust?"},
        "opening":{"vi":"Chuông lễ hội vừa ngân thì ánh trăng trên tháp vụt tắt. Nguyệt Thạch đã biến mất. Trong tay bạn là lời nhắn: ‘Đừng tin lời kể đầu tiên.’","en":"The festival bell rings as the tower's moonlight fades. The Moonstone is missing. A note in your hand reads: 'Do not trust the first account.'"},
        "lore":[
            {"id":"festival","title":{"vi":"Lễ hội trăng","en":"Moon Festival"},"text":{"vi":"Thời gian trong truyện chỉ tiến khi bạn hành động. Các lối đi luôn mở.","en":"Story time advances only when you act. Paths remain open."},"scope":"public","unlock":"","canon":True,"keywords":["trăng","moon","festival"]},
            {"id":"rumor","title":{"vi":"Lời đồn","en":"A rumour"},"text":{"vi":"Có người buộc tội một lữ khách, nhưng chưa có bằng chứng.","en":"Some blame a traveller, but no evidence confirms it."},"scope":"rumor","unlock":"","canon":False,"keywords":["ren","trộm","thief"]},
            {"id":"seal","title":{"vi":"Phong ấn","en":"The seal"},"text":{"vi":"Nguyệt Thạch duy trì phong ấn; nghi lễ vội vàng có thể khiến nó suy yếu.","en":"The Moonstone sustains the seal. A rushed ritual could weaken it."},"scope":"discovered","unlock":"tower","canon":True,"keywords":["stone","đá","nghi lễ"]},
            {"id":"secret","title":{"vi":"Người trong ánh trăng","en":"Someone in the moonlight"},"text":{"vi":"Chiếc hộp đang che chở người vô tội. Danh tính họ cần được bảo vệ.","en":"The box shelters someone innocent. Their identity needs protection."},"scope":"discovered","unlock":"forest","canon":True,"keywords":["hộp","box","child"]}],
        "narrator_model_id":"", "narrator_prompt":""}

def label(value, language):
    return value.get(language) or value.get("vi") or next((v for v in value.values() if v), "") if isinstance(value,dict) else str(value)

def places(language):
    return [{"id":p[0],"name":p[1 if language=="vi" else 2],"symbol":p[3],"x":p[4],"y":p[5],"links":p[6]} for p in LOCATIONS]

def _legacy_fresh(world, cast, language, memory_mode, memories):
    return {"world":deepcopy(world),"language":language,"location":"square","turn":0,"cast":cast,
        "memory_mode":memory_mode,"memories":memories,"clues":[],"inventory":[],"notes":[],
        "trust":{c["id"]:c.get("initial_trust",0) for c in cast},"ending":None,"moments_seen":[],
        "history":[{"id":uuid.uuid4().hex,"speaker":"narrator","kind":"opening","text":label(world["opening"],language)}],
        "journal":[],"quests":{},"encounter":cast[0]["id"],"return_trail":[],"hint_level":0}

def fresh(world, cast, language, memory_mode, memories):
    state=_legacy_fresh(world,cast,language,memory_mode,memories)
    return lastlight.initial(state) if world.get("story_mode")==lastlight.ID else state


def knowledge(state, speaker=None, query=""):
    # Scope is checked before relevance; raw world definitions never enter actor prompts.
    discovered={c["location"] for c in state["clues"]}
    lore=[e for e in state["world"]["lore"] if e["scope"] in ("public","rumor") or
          e["scope"]=="discovered" and e["unlock"] in discovered]
    def folded(value):
        return "".join(c for c in unicodedata.normalize("NFD",value.casefold().replace("đ","d")) if unicodedata.category(c)!="Mn")
    normalized=folded(query)
    lore.sort(key=lambda e:(-sum(folded(k) in normalized for k in e.get("keywords",[]) if k),not e["canon"]))
    selected=[];budget=4500
    for entry in lore:
        cost=len(label(entry["text"],state["language"]))
        if cost<=budget:
            selected.append(entry);budget-=cost
    lore=selected
    clues=[c for c in state["clues"] if c["scope"]=="public" or speaker is None or speaker in c["witnesses"]]
    return [{"id":e["id"],"title":label(e["title"],state["language"]),"text":label(e["text"],state["language"]),"scope":e["scope"],"canon":e["canon"]} for e in lore[:6]], clues

def advance(state, action, value="", speaker=None, roll=None):
    if state["world"].get("story_mode")==lastlight.ID:return lastlight.advance(state,action,value,speaker)
    s=deepcopy(state); vi=s["language"]=="vi"; name="narrator"; dice=None
    choose=lambda a,b:a if vi else b
    locs={p["id"]:p for p in places(s["language"])}
    if s["ending"]:raise ValueError(choose("Chuyến đi đã kết thúc. Hãy mở checkpoint để chơi nhánh khác.","This journey has ended. Branch from a checkpoint to explore another ending."))
    chapter_action=action in ("go","visit","return","accept","report","talk","hint")
    chapter_label=None
    if chapter_action:
        text,name,chapter_label=chapter.apply(s,action,value,speaker,LOCATIONS,knowledge)
    elif action=="travel":
        if value not in locs[s["location"]]["links"]:raise ValueError(choose("Hãy chọn địa điểm nối liền.","Choose a connected location."))
        s["location"]=value
        text=choose("Bạn đến ","You arrive at ")+locs[value]["name"]+choose(". Hãy quan sát, hỏi chuyện hoặc tiếp tục khám phá.",". Observe, talk, or keep exploring.")
    elif action in ("search","interview"):
        if action=="interview":
            person=next((p for p in chapter.contacts(s) if p["id"]==speaker and p["location"]==s["location"]),None)
            if person is None:raise ValueError(choose("Hãy tới gặp nhân vật này trước khi hỏi chuyện.","Visit this character before asking for evidence."))
            s["encounter"]=speaker
            name=person["name"]
        if any(c["location"]==s["location"] for c in s["clues"]):
            text=choose("Bạn đã ghi lại manh mối ở đây.","You have already recorded the evidence here.")
        else:
            dice=(roll or (lambda:secrets.randbelow(20)+1))() if s["location"]=="forest" else None
            if dice is not None and dice<7:
                text=choose("Sương phủ lối mòn. Bạn chưa tìm được vật gì; có thể thử lại hoặc đi lối khác.","Mist hides the path. You find nothing yet; try again or choose another route.")
            else:
                index=[p[0] for p in LOCATIONS].index(s["location"])
                title,text=FINDINGS[s["language"]][index]
                s["clues"].append({"id":uuid.uuid4().hex,"location":s["location"],"title":title,"text":text,
                    "scope":"witnessed" if s["location"]=="tavern" else "public",
                    "witnesses":["user"]+([speaker] if speaker else []),"origin":"admin","turn":s["turn"]+1})
                s["inventory"].append(title)
        if action=="interview":
            text=choose("Ta kể lại điều có thể kiểm chứng: ","Here is what can be checked: ")+text
    elif action=="share":
        clue=next((c for c in s["clues"] if c["id"]==value),None)
        if not clue:raise ValueError("Unknown evidence")
        clue["scope"]="public"
        text=choose("Bạn chia sẻ lời chứng. Cả nhóm giờ có thể nhắc tới nó.","You share the account. Everyone in your party can now discuss it.")
    elif action=="resolve":
        if s["location"]!="observatory" or len(s["clues"])<3:raise ValueError(choose("Cần tới Đài Sao Cũ với ít nhất ba manh mối.","Reach the observatory with at least three clues."))
        if value not in ("protect","reveal","seal"):raise ValueError("Invalid ending")
        endings={"protect":("Người giữ lời hẹn","Keeper of the Promise","Bạn giữ kín danh tính người vô tội và trao bằng chứng cho người giữ phong ấn.","You protect the innocent person's identity and give the evidence to the keeper."),
            "reveal":("Sự thật dưới ánh trăng","Truth in the Moonlight","Bạn công khai bằng chứng, xóa lời buộc tội. Câu hỏi về người cần bảo vệ vẫn còn đó.","You reveal the evidence and clear the accusation. Protecting the innocent remains a question."),
            "seal":("Một bình minh khác","Another Dawn","Bạn hoãn nghi lễ, cùng nhóm gia cố phong ấn. Không ai phải trả giá cho sự vội vàng.","You postpone the ritual and strengthen the seal together. Nobody pays for a rushed decision.")}
        e=endings[value];s["ending"]={"id":value,"title":e[0 if vi else 1]};text=e[2 if vi else 3]
        for c in s["cast"]:s["trust"][c["id"]]=min(100,s["trust"][c["id"]]+(5 if value=="protect" else 3))
    elif action=="wait":
        text=choose("Bạn ngồi nghỉ. Người đồng hành không giục bạn. Xa xa, tiếng chuông đổi nhịp.","You rest. Your companion does not rush you. Far away, the bells change rhythm.")
    elif action=="listen":
        if s["location"]!="square" or (s["turn"]//4)%4!=1:
            raise ValueError(choose("Tiếng chuông chỉ rõ khi trăng lên ở quảng trường.","The echo is clearest in the square at moonrise."))
        if "bell_echo" in s.get("moments_seen",[]):
            text=choose("Bạn đã giữ giai điệu này trong nhật ký.","You have already kept this melody in your journal.")
        else:
            s.setdefault("moments_seen",[]).append("bell_echo")
            s["inventory"].append(choose("Mảnh ký âm ánh trăng","A moonlit melody"))
            if speaker:s["trust"][speaker]=min(100,s["trust"][speaker]+1)
            text=choose("Bạn và người đồng hành cùng nghe ra một nốt nhạc ngược chiều gió. Bạn giữ nó như kỷ vật của chuyến đi, không phải bằng chứng buộc tội ai.","You and your companion hear a note carried against the wind. You keep it as a memento, not evidence against anyone.")
    elif action=="say":
        if not value.strip():raise ValueError("Empty message")
        person=next((c for c in s["cast"] if c["id"]==speaker),None)
        name=person["name"] if person else "narrator"
        _,clues=knowledge(s,speaker,value)
        hint=clues[-1]["title"] if clues else choose("lời đồn chưa phải sự thật","a rumour is not a fact")
        text=choose("Điều chúng ta có thể dựa vào lúc này là ","What we can rely on now is ")+hint+choose(". Bạn muốn đối chiếu lời kể hay tìm quanh đây?",". Shall we compare accounts or look around?")
    else:raise ValueError("Unsupported action")
    if action!="hint":s["turn"]+=1
    phase=["Hoàng hôn","Trăng lên","Đêm bạc","Trước bình minh"] if vi else ["Dusk","Moonrise","Silver night","Before dawn"]
    s["phase"]=phase[(s["turn"]//4)%4]
    event={"id":uuid.uuid4().hex,"speaker":name,"kind":action,"text":text,"turn":s["turn"],"roll":dice,"narration":"rules"}
    usertext=value if action=="say" else choose({"travel":"Đi tới "+locs.get(value,locs[s["location"]])["name"],"search":"Tìm manh mối","share":"Chia sẻ lời chứng","resolve":"Đưa ra lựa chọn","wait":"Nghỉ một lát","listen":"Lắng nghe tiếng chuông"}.get(action,action),
        {"travel":"Travel to "+locs.get(value,locs[s["location"]])["name"],"search":"Look for evidence","share":"Share evidence","resolve":"Make a choice","wait":"Rest","listen":"Listen to the bells"}.get(action,action))
    if action=="interview":usertext=choose("Hỏi nhân vật để tìm manh mối","Ask the character for a clue")
    if chapter_label:usertext=chapter_label
    s["history"]=(s["history"]+[{"id":uuid.uuid4().hex,"speaker":"user","text":usertext,"kind":"user"},event])[-80:]
    s["journal"]=(s["journal"]+[{"id":event["id"],"turn":s["turn"],"text":text,"location":s["location"]}])[-100:]
    return s,event

def public_world(world, language):
    return {"id":world["id"],"version":world["version"],"title":label(world["title"],language),
        "pitch":label(world["pitch"],language),"rating":world["rating"],"status":world["status"]}

def view(campaign):
    s=campaign["state"];lore,_=knowledge(s)
    return {"id":campaign["id"],"revision":campaign["revision"],"title":campaign["title"],"branch_of":campaign.get("branch_of"),
        "world":public_world(s["world"],s["language"]),"language":s["language"],"location":s["location"],"phase":s.get("phase",""),
        "places":places(s["language"]),"cast":[{"id":c["id"],"name":c["name"],"origin":c["origin"]} for c in s["cast"]],
        **{key:s[key] for key in ("turn","memory_mode","clues","inventory","notes","trust","ending","history","journal","memories")},
        "adventure":lastlight.projection(s) if s["world"].get("story_mode")==lastlight.ID else None,
        "chapter":lastlight.projection(s) if s["world"].get("story_mode")==lastlight.ID else chapter.projection(s),"lore":lore,"checkpoints":[{"id":c["id"],"title":c["title"],"turn":c["turn"]} for c in campaign["checkpoints"]]}
