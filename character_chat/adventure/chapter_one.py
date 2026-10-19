"""Chapter one's gate is a persisted interaction, not a video completion condition."""
from copy import deepcopy
DEFAULT={
 "enabled":True,
 "gate_prompt":{"vi":"Các dấu vết đã khớp. Hãy dùng chìa khóa để mở cổng cổ.","en":"The clues fit together. Use the key to open the ancient gate."},
 "chapter_end":{"vi":"Chương 1 khép lại — phía sau cánh cổng, một lời gọi vẫn chưa tìm được người đáp.","en":"Chapter 1 ends — beyond the gate, a voice still waits for an answer."},
 "scroll_title":{"vi":"Moonbrook — nơi những cái tên còn ngủ quên","en":"Moonbrook — where names lie sleeping"},
 "scroll_body":{"vi":"Từng có người đi qua những hành lang này với sách vở trong tay, tin rằng trăng sẽ còn soi sáng sân học viện vào ngày mai. Giờ chỉ những nét rune nhận ra người trở lại.\n\nCánh cổng đã mở, nhưng ký ức đầu tiên dừng lại trước một gương mặt. Ai đã gọi Selene? Và vì sao lời cảnh báo ấy vẫn còn vang giữa một nơi tưởng như đã quên tất cả?\n\nHãy mang câu hỏi đó trở về cùng cô. Có những câu chuyện chỉ hé tiếp khi hai người đủ sẵn lòng lắng nghe.","en":"People once walked these halls carrying books, certain that tomorrow's moon would still shine over the academy courtyard. Now only the runes recognize those who return.\n\nThe gate has opened, but the first memory stops just short of a face. Who called Selene? And why does that warning linger in a place that seems to have forgotten everything?\n\nTake the question home with her. Some stories unfold only when both of you are ready to listen."}
}
def config(s):
    from .languages import enrich
    return enrich(s["config"].get("adventure",{}).get("chapter_one_flow",DEFAULT))
def enabled(s):return s["chapter_id"]=="selene_01" and config(s).get("enabled",True) and not s.get("reviewing")
def await_gate(s):
    from .engine import emit
    s["phase"]="gate_ready";s["location"]="ancient_gate"
    emit(s,{"type":"narration","text":config(s)["gate_prompt"]})
def act(s,action):
    from .engine import ready,begin_memory
    if action=="open_gate":
        if not enabled(s) or s["phase"]!="gate_ready" or not ready(s) or not any(c["chapter"]=="selene_01" for c in s["choices"]):raise ValueError("The gate is not ready")
        s["gate_opened"]=True;s["phase"]="gate_cinematic"
    elif action=="finish_gate_cinematic":
        if not enabled(s) or s["phase"]!="gate_cinematic" or not s.get("gate_opened"):raise ValueError("No gate transition")
        begin_memory(s)
    return s
def projection(s,loc):
    if s["chapter_id"]!="selene_01":return None
    cfg=config(s)
    if not cfg.get("enabled",True):return None
    return dict(phase=s["phase"],gate_prompt=loc(cfg["gate_prompt"]),chapter_end=loc(cfg["chapter_end"]),scroll_title=loc(cfg["scroll_title"]),scroll_body=loc(cfg["scroll_body"]),
                cinematic="enter_ruins_video",key=s["id"]+":"+s.get("attempt_id","first")+":gate")
