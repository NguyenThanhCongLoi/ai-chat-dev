"""Fast group turn planning without a network call or a routing LLM."""
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
import re
import time
import unicodedata
from .retrieval import vector

def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold().replace("đ","d")) if not unicodedata.combining(c))

# Shared topic features bridge common role/domain words across supported UI languages.
TOPICS = {
    "study": ("study","school","learn","homework","hoc","truong","bai tap","学习","学校","勉強","学校","공부","학교","សិក្សា","ကျောင်း"),
    "work": ("work","job","career","business","viec","cong viec","kinh doanh","工作","仕事","직장","ការងារ","အလုပ်"),
    "health": ("health","doctor","medical","suc khoe","bac si","benh","健康","医生","医者","건강","សុខភាព","ကျန်းမာ"),
    "art": ("art","artist","music","creative","nghe thuat","nghe si","am nhac","艺术","音乐","芸術","音楽","예술","សិល្បៈ","အနုပညာ"),
    "comfort": ("sad","worried","anxious","comfort","empathy","buon","lo lang","an ui","悲伤","难过","悲しい","슬프","ពិបាកចិត្ត","ဝမ်းနည်း"),
    "fun": ("fun","joke","humor","funny","dua","hai huoc","vui","笑话","冗談","농담","កំប្លែង","ဟာသ"),
}
def topics(text):
    value=normalize(text)
    return {topic for topic,words in TOPICS.items() if any(
        re.search(r"(?<!\w)"+re.escape(normalize(word))+r"(?!\w)",value) if word.isascii() else normalize(word) in value
        for word in words)}

@lru_cache(maxsize=512)
def profile_features(text):
    return vector(normalize(text)),topics(text)

def matches_name(message, character, require_at=False):
    for name in (character.name,character.display_name):
        name=normalize(name.strip())
        if len(name)<2:continue
        prefix="@" if require_at else "@?"
        if re.search(r"(?<!\w)"+prefix+re.escape(name)+r"(?!\w)",normalize(message)):
            return True
    return False

EVERYONE=("everyone","all of you","each of you","ca nhom","moi nguoi","tat ca cac ban","大家","所有人","みんな","여러분","모두","ទាំងអស់គ្នា","အားလုံး")
PAIR=("both","two of you","compare","different opinions","ca hai","hai ban","so sanh","hai goc nhin","两位","两个人","二人","둘 다","ទាំងពីរ","နှစ်ယောက်")
EXCHANGE=("discuss","debate","ask each other","ask for","trao doi","thao luan","hoi y kien","tranh luan","讨论","商量","相談","토론","ពិភាក្សា","ဆွေးနွေး")
FOLLOWUP=("why","how so","really","tell me more","what do you mean","tai sao","vi sao","that a","noi tiep","ke tiep","y la sao","为什么","なぜ","왜","ហេតុអ្វី","ဘာကြောင့်")
def contains(text, phrases):
    return any(re.search(r"(?<!\w)"+re.escape(normalize(p))+r"(?!\w)",text) if p.isascii() else normalize(p) in text for p in phrases)

@dataclass
class GroupPlan:
    speakers: list
    interaction: str = "single"
    reason: str = "single_room"
    scores: dict = field(default_factory=dict)
    latency_ms: float = 0

    def metadata(self):
        return {"speaker_ids":[c.id for c in self.speakers],"interaction":self.interaction,
                "reason":self.reason,"scores":self.scores,"latency_ms":self.latency_ms,
                "router":"local_rules_topics_v1"}

    def instruction(self, character_id):
        if len(self.speakers)<2:return ""
        position=next(i for i,c in enumerate(self.speakers) if c.id==character_id)
        names=", ".join(c.display_name or c.name for c in self.speakers)
        base=f"GROUP TURN PLAN: Participants speaking this turn, in order: {names}. You speak only your own turn. "
        if self.interaction=="exchange":
            if position==0:
                peer=self.speakers[1].display_name or self.speakers[1].name
                return base+f"Give one brief useful perspective, then ask {peer} one concrete question relevant to the user's request. Do not invent their reply."
            return base+"Answer the preceding participant's question using your own expertise and personality, then address the human user with a concise takeaway. Do not repeat their advice."
        if position==0:return base+"Give your own concise perspective. Leave room for another distinct perspective; do not speak for others."
        return base+"Contribute a brief distinct perspective or relevant disagreement, grounded in the preceding replies. Do not restate their advice. Address the human user."

def plan_group(message, characters, mode="auto", history=()):
    started=time.perf_counter()
    chars=list(characters)[:6]
    def result(selected,interaction="single",reason="single_room",scores=None):
        return GroupPlan(selected,interaction,reason,scores or {},round((time.perf_counter()-started)*1000,3))
    if not chars:raise ValueError("Room has no characters")
    if len(chars)==1:return result(chars)
    text=normalize(message)
    explicit=[c for c in chars if matches_name(message,c,True)]
    mentioned=explicit or [c for c in chars if matches_name(message,c)]
    if len(mentioned)==1:return result(mentioned,reason="addressed_character")
    if mode.startswith("character:"):
        selected=[c for c in chars if c.id==mode.split(":",1)[1]]
        if not selected:raise ValueError("Selected character is not in this room")
        return result(selected,reason="selected_character")
    if mode=="everyone" or contains(text,EVERYONE):
        return result(chars,"everyone","user_requested_everyone")
    if len(mentioned)>1:
        return result(mentioned[:2],"exchange" if contains(text,EXCHANGE) else "complement","addressed_pair")
    turns=[];current=[]
    for item in history:
        if item["sender_type"]=="user":
            if current:turns.append(current)
            current=[]
        elif item["sender_type"]=="character" and item.get("character_id") in {c.id for c in chars} and item["text"].strip():
            current.append(item["character_id"])
    if current:turns.append(current)
    last=turns[-1][-1] if turns else None
    if last and contains(text,FOLLOWUP) and len(message.split())<=12:
        return result([next(c for c in chars if c.id==last)],reason="followup")
    query=message
    if len(message.split())<=8:
        previous_users=[item["text"] for item in history if item["sender_type"]=="user"]
        if previous_users:query=previous_users[-1][-600:]+" "+message
    query_vec=vector(normalize(query));query_topics=topics(query)
    counts=Counter(id for turn in turns[-6:] for id in turn)
    scores={};features={}
    for c in chars:
        profile=" ".join([c.description,c.identity.role,c.identity.backstory,*c.goals,*c.likes,c.support.primary_role,*c.support.strengths])
        pv,pt=profile_features(profile);features[c.id]=(pv,pt)
        relevance=sum(v*pv.get(k,0) for k,v in query_vec.items())
        topic_fit=len(query_topics&pt)/max(1,len(query_topics))
        affinity=(c.personality.empathy*.18 if "comfort" in query_topics else 0)+(c.personality.humor*.12 if "fun" in query_topics else 0)
        fairness=.07/(1+counts[c.id])-(.045 if c.id==last else 0)
        scores[c.id]=round(relevance*.5+topic_fit*.5+affinity+fairness,5)
    ranked=sorted(chars,key=lambda c:(-scores[c.id],counts[c.id],chars.index(c)))
    first,second=ranked[:2]
    pair_requested=contains(text,PAIR) or contains(text,EXCHANGE)
    # At least three single turns between spontaneous two-person interactions.
    cooldown=any(len(set(turn))>1 for turn in turns[-3:])
    eligible=(scores[second.id]>=.20 and scores[first.id]-scores[second.id]<.25)
    different=features[first.id][1]!=features[second.id][1] or first.identity.role!=second.identity.role
    if pair_requested or (not cooldown and len(turns)>=3 and eligible and different):
        exchange=contains(text,EXCHANGE) or (not pair_requested and len(turns)%4==3)
        return result([first,second],"exchange" if exchange else "complement","requested_pair" if pair_requested else "distinct_perspectives",scores)
    return result([first],"single","relevance_and_turn_balance",scores)

def plan_room(db, room_id, message, characters, mode="auto", exclude_message_id=None):
    from .db import Message
    rows=db.query(Message).filter_by(room_id=room_id)
    if exclude_message_id:rows=rows.filter(Message.id!=exclude_message_id)
    rows=rows.order_by(Message.created_at.desc(),Message.id.desc()).limit(60).all()
    history=[{"sender_type":row.sender_type,"character_id":row.character_id,"text":row.text} for row in reversed(rows)]
    return plan_group(message,characters,mode,history)
