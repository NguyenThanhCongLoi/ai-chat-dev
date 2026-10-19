"""Authored chapter goals, safe conversation choices and navigation for Worlds.

No provider calls. Quest receipts and routes are server validated. Character identity
always comes from the shared catalog; chapter roles do not replace their persona.
"""
from collections import deque

TASKS = (
    ("witness", "tavern", "Theo dấu người giữ đèn", "Follow the lamplighter"),
    ("mirror", "forest", "Một lời buộc tội cần đối chứng", "An accusation needs evidence"),
    ("ritual", "tower", "Cái giá của nghi lễ", "The cost of the ritual"),
)
HOMES = ("square", "tavern", "tower")


def pick(s, vi, en):
    return vi if s["language"] == "vi" else en


def contacts(s):
    roles = (("Người đối chiếu", "The investigator"), ("Người dò đường", "The scout"), ("Người giữ nghi lễ", "The ritual keeper"))
    return [{**c, "location": HOMES[i], "role": pick(s, *roles[i])} for i, c in enumerate(s["cast"])]


def route(s, destination, locations):
    """Shortest connected path, including origin, never accepts a client supplied path."""
    graph = {p[0]: p[6] for p in locations}
    if destination not in graph:
        raise ValueError("Unknown destination")
    queue = deque([[s["location"]]])
    seen = {s["location"]}
    while queue:
        path = queue.popleft()
        if path[-1] == destination:
            return path
        for target in graph[path[-1]]:
            if target not in seen:
                seen.add(target)
                queue.append(path + [target])
    raise ValueError("No available route")


def quests(s):
    accepted = s.get("quests", {})
    people = contacts(s)
    result = []
    for i, (ident, target, vi, en) in enumerate(TASKS):
        person = people[i % len(people)]
        previous = i == 0 or accepted.get(TASKS[i - 1][0]) == "done"
        status = accepted.get(ident, "available" if previous else "locked")
        found = any(c["location"] == target for c in s["clues"])
        ready = status == "active" and found
        result.append({"id": ident, "title": pick(s, vi, en), "giver": person["id"],
                       "giver_name": person["name"], "home": person["location"], "target": target,
                       "status": status, "ready": ready})
    return result


def guidance(s):
    """Only the requested hint is displayed; computing it exposes no secret text."""
    if s["ending"]:
        return {"text": pick(s, "Chuyến đi đã kết thúc. Mở Nhật ký để chơi một nhánh khác.", "The journey is complete. Open Journal to explore another branch."), "action": None, "value": ""}
    if not any(c["location"] == "square" for c in s["clues"]):
        return {"text": pick(s, "Bắt đầu bằng việc quan sát quảng trường.", "Start by observing the square."),
                "action": "search" if s["location"] == "square" else "go", "value": "" if s["location"] == "square" else "square"}
    q = next((q for q in quests(s) if q["status"] not in ("done", "locked")), None)
    if q:
        home = q["status"] == "available" or q["ready"]
        dest = q["home"] if home else q["target"]
        if s["location"] != dest:
            return {"text": pick(s, "Đi tới bước tiếp theo của nhiệm vụ: ", "Travel to the next quest step: ") + q["title"], "action": "go", "value": dest}
        if q["status"] == "available":
            return {"text": pick(s, "Nhận lời nhờ giúp từ ", "Accept a request from ") + q["giver_name"], "action": "accept", "value": q["id"]}
        if q["ready"]:
            return {"text": pick(s, "Kể lại bằng chứng cho ", "Report your findings to ") + q["giver_name"], "action": "report", "value": q["id"]}
        return {"text": pick(s, "Quan sát nơi này để tìm đối chứng.", "Search this place for evidence."), "action": "search", "value": ""}
    return {"text": pick(s, "Đến Đài Sao Cũ, lưu mốc rồi chọn cách giải quyết.", "Reach the Old Observatory, save a checkpoint, then choose a resolution."),
            "action": "go" if s["location"] != "observatory" else None, "value": "observatory"}


def projection(s):
    q = quests(s)
    g = guidance(s)
    hints = s.get("hint_level", 0)
    found = {c["location"] for c in s["clues"]}
    if hints == 1:
        hint = pick(s, "Đối chiếu lời kể với vật chứng. Người có vai trò khác có thể giúp bạn nhìn ra điều còn thiếu.", "Compare accounts with evidence. Another person's perspective may reveal what is missing.")
    elif hints == 2:
        task = next((x for x in q if x["status"] not in ("done", "locked")), None)
        hint = (pick(s, "Theo lời nhờ giúp của ", "Follow the request from ") + task["giver_name"]) if task else g["text"]
    else:
        hint = g["text"] if hints else ""
    if not found:
        chapter = pick(s, "I · Tiếng chuông tắt", "I · The silent bell")
    elif len(found) < 3:
        chapter = pick(s, "II · Những lời kể khác nhau", "II · Conflicting accounts")
    else:
        chapter = pick(s, "III · Điều đáng bảo vệ", "III · What deserves protection")
    selected = s.get("encounter") or s["cast"][0]["id"]
    return {"chapter": chapter, "contacts": [{"id": p["id"], "name": p["name"], "location": p["location"], "role": p["role"]} for p in contacts(s)],
            "quests": q, "next": g, "encounter": selected, "can_return": bool(s.get("return_trail")),
            "hint": hint, "hint_level": hints,
            "completed": sum(x["status"] == "done" for x in q),
            "tutorial": not s.get("tutorial_done", False)}


def apply(s, action, value, speaker, locations, knowledge):
    """Return event text, speaker label, and user-facing action label."""
    person = next((p for p in contacts(s) if p["id"] == (speaker or s.get("encounter"))), contacts(s)[0])
    label = pick(s, "Tiếp tục hành trình", "Continue the journey")
    name = "narrator"
    if action in ("go", "visit", "return"):
        if action == "visit":
            person = next((p for p in contacts(s) if p["id"] == value), None)
            if person is None:
                raise ValueError("This character is not in your party")
            destination = person["location"]
        elif action == "return":
            if not s.get("return_trail"):
                raise ValueError("No previous encounter")
            previous = s["return_trail"][-1]
            destination = previous["location"]
        else:
            destination = value
        path = route(s, destination, locations)
        if action == "return":
            s["return_trail"].pop()
            s["encounter"] = previous.get("actor")
        elif destination != s["location"] or action == "visit":
            s["return_trail"] = (s.get("return_trail", []) + [{"location": s["location"], "actor": s.get("encounter")}])[-8:]
        s["location"] = destination
        if action == "visit":
            s["encounter"] = person["id"]
        place_names = {p[0]: p[1 if s["language"] == "vi" else 2] for p in locations}
        text = pick(s, "Lộ trình: ", "Route: ") + " → ".join(place_names[x] for x in path)
        if action == "visit":
            text += pick(s, ". Bạn gặp ", ". You meet ") + person["name"] + pick(s, ". Bạn có thể hỏi về nhiệm vụ hoặc chỉ trò chuyện.", ". Ask about the investigation, or simply talk.")
        label = pick(s, "Đi theo lối tắt", "Take the shortcut")
    elif action in ("accept", "report"):
        q = next((q for q in quests(s) if q["id"] == value), None)
        if not q or q["status"] == "locked":
            raise ValueError("Quest is not available yet")
        if s["location"] != q["home"]:
            raise ValueError(pick(s, "Hãy gặp người giao nhiệm vụ trước.", "Meet the quest giver first."))
        s["encounter"] = q["giver"]
        name = q["giver_name"]
        s.setdefault("quests", {})
        if action == "accept":
            if q["status"] != "available":
                raise ValueError("This request has already been accepted")
            s["quests"][q["id"]] = "active"
            prompts = {
                "witness": ("Ở quán trọ có người trực đèn đêm qua. Hãy tìm lời chứng của họ rồi trở lại; đừng kết tội ai vội.", "Someone at the inn tended the lamps last night. Find their account and return; do not accuse anyone yet."),
                "mirror": ("Lời chứng chưa đủ để kết luận. Tìm mảnh gương trong rừng, rồi cho tôi biết nó có xác nhận điều ta đang nghĩ không.", "An account alone proves little. Find the mirror in the forest and tell me whether it supports our theory."),
                "ritual": ("Trước khi trả Nguyệt Thạch, hãy tìm trang nghi lễ ở tháp. Tôi muốn biết việc làm đúng có thể gây hại như thế nào.", "Before returning the Moonstone, find the ritual page in the tower. We must know whether doing the right thing could cause harm."),
            }
            text = pick(s, *prompts[q["id"]])
        else:
            if not q["ready"]:
                raise ValueError(pick(s, "Cần nhận nhiệm vụ và tìm bằng chứng trước.", "Accept the request and find the evidence first."))
            clue = next(c for c in s["clues"] if c["location"] == q["target"])
            if q["giver"] not in clue["witnesses"]:
                clue["witnesses"].append(q["giver"])
            # Reporting shares this fact with the giver, not automatically everyone.
            s["quests"][q["id"]] = "done"
            s["trust"][q["giver"]] = min(100, s["trust"][q["giver"]] + 2)
            text = pick(s, "Bạn kể riêng điều vừa tìm được. ", "You privately report your findings. ") + clue["title"] + pick(s, ". Chúng ta đã tiến thêm một bước; hãy nghe lời nhờ giúp tiếp theo.", ". We have made progress. Follow the next request when you are ready.")
            following = next((x for x in quests(s) if x["status"] == "available"), None)
            if following:
                text += pick(s, " Người tiếp theo bạn có thể hỏi là ", " The next person to ask is ") + following["giver_name"] + "."
            else:
                token = pick(s, "Dấu ấn ba lời hẹn", "Token of three promises")
                if token not in s["inventory"]:s["inventory"].append(token)
                text += pick(s, " Ba lời hẹn đã được giữ. Bạn nhận một kỷ vật và có thể cùng nhóm tới Đài Sao Cũ.", " Three promises kept. You receive a keepsake and can gather everyone at the observatory.")
            s["return_trail"] = []  # a reported request no longer needs a return breadcrumb
        label = pick(s, "Nhận lời nhờ giúp" if action == "accept" else "Báo cáo bằng chứng", "Accept the request" if action == "accept" else "Report evidence")
    elif action == "talk":
        if value not in ("motive", "personal", "evidence"):
            raise ValueError("Unknown conversation topic")
        s["encounter"] = person["id"]
        name = person["name"]
        idx = next(i for i, c in enumerate(s["cast"]) if c["id"] == person["id"])
        if value == "evidence":
            _, known = knowledge(s, person["id"])
            text = pick(s, "Điều tôi biết lúc này: ", "What I know right now: ") + (known[-1]["title"] if known else pick(s, "lời đồn chưa phải bằng chứng.", "a rumour is not evidence."))
        elif value == "motive":
            responses = (
                ("Tôi muốn biết điều gì thực sự đã xảy ra. Nếu chỉ tin lời kể đầu tiên, ta có thể làm tổn thương nhầm người.", "I want to know what really happened. Trusting the first account could hurt the wrong person."),
                ("Tôi muốn tìm đường mà người khác bỏ qua. Một câu chuyện thường thú vị nhất ở phần chưa ai chịu hỏi.", "I look for paths others overlook. The interesting part is often the question nobody asks."),
                ("Tôi muốn mọi người trở về an toàn. Một lời giải đẹp không đáng giá nếu nó khiến ai đó phải trả giá thay ta.", "I want everyone to return safely. A neat solution is worth little if someone else pays its price."),
            )
            text = pick(s, *responses[idx % 3])
        else:
            responses = (
                ("Tạm gác cuộc điều tra cũng được. Tôi thích khoảnh khắc ta có thể ngồi yên và thật sự lắng nghe nhau. Bạn không cần giải quyết mọi chuyện ngay hôm nay.", "We can put the investigation aside. There is value in sitting quietly and listening to each other. You do not have to solve everything today."),
                ("Một chuyến đi cần cả những lúc chẳng tìm thấy gì, trừ một người chịu nghe mình kể chuyện. Hôm nay cứ coi đó là phần thưởng đi.", "A journey needs moments when you find nothing except someone willing to listen. Let that be today's reward."),
                ("Nếu bạn mệt, chúng ta nghỉ một chút. Chuyện lớn có thể chờ; người đang đứng cạnh mình cũng đáng được quan tâm.", "If you are tired, we can rest. Great mysteries can wait; the person beside us deserves attention too."),
            )
            text = pick(s, *responses[idx % 3])
        label = pick(s, {"motive": "Điều gì khiến bạn ở lại?", "personal": "Nói chuyện ngoài nhiệm vụ", "evidence": "Bạn biết điều gì?"}[value],
                     {"motive": "Why are you helping?", "personal": "Talk beyond the quest", "evidence": "What do you know?"}[value])
    elif action == "hint":
        s["hint_level"] = min(3, s.get("hint_level", 0) + 1)
        text = projection(s)["hint"]
        label = pick(s, "Xin một gợi ý", "Ask for a hint")
    else:
        raise ValueError("Unknown chapter action")
    s["tutorial_done"] = True
    return text, name, label
