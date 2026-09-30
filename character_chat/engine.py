import json, os, re, time
from datetime import datetime, timezone
import httpx
from .schemas import CharacterSpec, DiscoveryCandidate
from .retrieval import similarity, retrieve_memories, retrieve_knowledge, room_document_manifest
from .db import Character, Message, Relationship, RoomMember, RoomStoryState, StyleExample, CharacterState, DailyTask, MoodObservation, CharacterReflection, RelationshipEvent, PromptTrace, now
from .prompts import RESPONSE_SYSTEM_PROMPT, SUGGESTION_SYSTEM_PROMPT, CHARACTER_COMPILER_SYSTEM_PROMPT, CHARACTER_SOURCE_CONDENSER_PROMPT

ADMIN_RESPONSE_INSTRUCTION=""
ADMIN_SUGGESTION_INSTRUCTION=""
ADMIN_COMPILER_INSTRUCTION=""
_UNSET_MODEL=object()

class TokenLimitError(RuntimeError):
    """The gateway returned a truncated completion."""

def condense_character_source(source:str,threshold:int=6000)->str:
    """Map-reduce long character source with the LLM before compilation."""
    source=source.strip()
    if len(source)<=threshold:return source
    chunks=[source[index:index+6000] for index in range(0,len(source),6000)][:12]
    summaries=[]
    for position,chunk in enumerate(chunks,1):
        summaries.append(llm.chat([{"role":"system","content":CHARACTER_SOURCE_CONDENSER_PROMPT},{"role":"user","content":f"Source part {position}/{len(chunks)}:\n{chunk}"}],temperature=.15,max_tokens=750))
    combined="\n\n".join(summaries)
    if len(summaries)>1:
        combined=llm.chat([{"role":"system","content":CHARACTER_SOURCE_CONDENSER_PROMPT},{"role":"user","content":"Merge these partial briefs into one non-repetitive source brief. Preserve contradictions and evidence across parts.\n\n"+combined}],temperature=.1,max_tokens=1400)
    return combined.strip()

class LLM:
    def __init__(self):
        self.url=os.getenv("LLM_API_BASE","https://gateway.avibi.ai/v1").rstrip("/")
        self.model=os.getenv("LLM_MODEL","openai/gpt-4.1-mini")
        self.fallback_model=os.getenv("LLM_FALLBACK_MODEL","")
        self.fallback_model_2=""
        self.default_temperature=.75
        self.short_temperature=.65
        self.default_max_tokens=350
        self.short_max_tokens=180
        self.api_key=(os.getenv("AIMP_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        self.model_api_keys={}
        self.model_api_bases={}
        self.model_thinking_modes={}
        self.model_reasoning_efforts={}
        self.model_generation={}
        self.model_gateway_timeouts={}
        self.purpose_models={}
        self.fallback_instruction=""
        self._clients={}
    def _request(self,messages,temperature,max_tokens,model,timeout_seconds=None):
        api_key=self.model_api_keys.get(model,self.api_key)
        api_base=self.model_api_bases.get(model,self.url)
        if not api_key:raise RuntimeError(f"Chưa cấu hình API key cho {api_base}")
        headers={"Content-Type":"application/json","Authorization":"Bearer "+api_key}
        payload={"model":model,"messages":messages}
        if "gpt-5" in model:
            payload["max_completion_tokens"]=max_tokens
        else:
            payload.update({"temperature":temperature,"max_tokens":max_tokens})
        thinking=self.model_thinking_modes.get(model,"default")
        effort=self.model_reasoning_efforts.get(model,"default")
        if thinking in ("enabled","disabled"):payload["thinking"]={"type":thinking}
        if thinking!="disabled" and effort in ("low","high","max"):payload["reasoning_effort"]=effort
        client=self._clients.get(api_base)
        timeout_seconds=max(.1,min(float(timeout_seconds or 12),45))
        timeout=httpx.Timeout(timeout_seconds,connect=min(8,timeout_seconds),read=timeout_seconds,write=min(10,timeout_seconds),pool=min(5,timeout_seconds))
        if client is None:
            client=httpx.Client(timeout=timeout,limits=httpx.Limits(max_connections=30,max_keepalive_connections=15,keepalive_expiry=120))
            self._clients[api_base]=client
        response=None
        response=client.post(api_base.rstrip("/")+"/chat/completions",headers=headers,json=payload,timeout=timeout)
        if response is None:raise RuntimeError("Dịch vụ LLM không trả response")
        if response.is_error:
            try:detail=response.json().get("error",{}).get("message") or response.text
            except Exception:detail=response.text
            error=RuntimeError(f"Dịch vụ LLM trả lỗi {response.status_code}: {str(detail)[:500]}")
            error.status_code=response.status_code
            raise error
        choice=response.json()["choices"][0]
        if choice.get("finish_reason") in ("length","max_tokens"):
            raise TokenLimitError(f"Model stopped at the token limit ({max_tokens} tokens) before completing its reply")
        content=choice["message"].get("content")
        if isinstance(content,list):content="".join(part.get("text","") for part in content if isinstance(part,dict))
        if not isinstance(content,str) or not content.strip():raise RuntimeError("Model returned an empty response")
        return content.strip()
    def chat_with_meta(self,messages,temperature=.7,max_tokens=350,model=_UNSET_MODEL,fallback_model=_UNSET_MODEL,fallback_model_2=_UNSET_MODEL,profile_mode=None,gateway_timeout_cap_seconds=None):
        selected=self.model if model is _UNSET_MODEL else model
        first=self.fallback_model if fallback_model is _UNSET_MODEL else fallback_model
        second=self.fallback_model_2 if fallback_model_2 is _UNSET_MODEL else fallback_model_2
        if not selected:raise RuntimeError("No primary model is assigned to this task in CMS.")
        fallback_messages=([{"role":"system","content":self.fallback_instruction},*messages] if model is _UNSET_MODEL and self.fallback_instruction.strip() else messages)
        candidates=list(dict.fromkeys(value for value in (selected,first,second) if value))
        configured_waits=[max(4,min(45,float(self.model_gateway_timeouts.get(candidate,12)),float(gateway_timeout_cap_seconds or 45))) for candidate in candidates]
        fallback_reserve=12 if len(candidates)>1 else 0
        budget=max(8,min(90,float(os.getenv("LLM_FALLBACK_BUDGET_SECONDS","28"))),max(configured_waits)+fallback_reserve)
        started=time.monotonic();errors=[]
        for index,candidate in enumerate(candidates):
            remaining=budget-(time.monotonic()-started)
            if remaining<=0:errors.append("total fallback budget exhausted");break
            try:
                configured=self.model_generation.get(candidate,{}) if profile_mode in ("normal","short") else {}
                prefix="short_" if profile_mode=="short" else ""
                candidate_temperature=float(configured.get(prefix+"temperature",temperature))
                candidate_tokens=max(1,int(configured.get(prefix+"max_tokens",max_tokens)))
                candidate_messages=messages if index==0 else fallback_messages
                gateway_wait=max(4,min(45,float(self.model_gateway_timeouts.get(candidate,12)),float(gateway_timeout_cap_seconds or 45)))
                answer=self._request(candidate_messages,candidate_temperature,candidate_tokens,candidate,min(gateway_wait,remaining))
                return answer,{"primary_model":selected,"fallback_model":first or "","fallback_model_2":second or "","fallback_used":index>0,"fallback_level":index,"fallback_reason":" | ".join(errors),"actual_model":candidate}
            except Exception as exc:
                status=getattr(exc,"status_code",0)
                retryable=isinstance(exc,(httpx.TransportError,RuntimeError,ValueError)) and (not status or status in (408,409,425,429,500,502,503,504))
                if not retryable:raise
                errors.append(f"{candidate}: {type(exc).__name__}: {str(exc)[:400]}")
        raise RuntimeError("; ".join(errors) or "No configured model available")

    def chat(self,messages,temperature=.7,max_tokens=350,model=_UNSET_MODEL,fallback_model=_UNSET_MODEL,fallback_model_2=_UNSET_MODEL):
        return self.chat_with_meta(messages,temperature,max_tokens,model,fallback_model,fallback_model_2)[0]

    def json(self,messages,schema,model=None,max_tokens=2500):
        prompt={"role":"system","content":"Return ONLY valid JSON matching this schema: "+json.dumps(schema.model_json_schema(),ensure_ascii=False)}
        last_error=None
        for attempt in range(3):
            timeout_seconds=self.model_gateway_timeouts.get(model,12) if model else None
            raw=self._request([prompt,*messages],.1,max_tokens,model,timeout_seconds=timeout_seconds) if model else self.chat([prompt,*messages],temperature=.1,max_tokens=max_tokens)
            try:
                cleaned=re.sub(r"^```(?:json)?\s*|\s*```$","",raw.strip(),flags=re.I)
                try:
                    data=json.loads(cleaned)
                except json.JSONDecodeError:
                    # Some compatible gateways/models wrap a valid object in
                    # prose or Markdown. Decode the first complete JSON object.
                    decoder=json.JSONDecoder()
                    data=None
                    for start,char in enumerate(cleaned):
                        if char!="{":continue
                        try:
                            data,_=decoder.raw_decode(cleaned[start:])
                            break
                        except json.JSONDecodeError:
                            continue
                    if data is None:raise
                return schema.model_validate(data)
            except Exception as exc:
                last_error=exc
                messages=[*messages,{"role":"assistant","content":raw},{"role":"user","content":f"Return a corrected, complete JSON object only. Fix this validation error: {exc}"}]
        raise ValueError(f"LLM returned invalid structured JSON after 3 attempts: {last_error}")

llm=LLM()

def room_story_events(db,room_id,recent_ids):
    """Keep a bounded, speaker-attributed record of turns outside the live chat window."""
    history=db.query(Message).filter_by(room_id=room_id).order_by(Message.created_at.desc(),Message.id.desc()).limit(80).all()[::-1]
    older=[item for item in history if item.id not in recent_ids and item.sender_type in ("user","character")][-24:]
    characters={item.id:item for item in db.query(Character).filter(Character.id.in_({item.character_id for item in older if item.character_id})).all()} if older else {}
    events=[{"id":item.id,"speaker":characters[item.character_id].name if item.sender_type=="character" and item.character_id in characters else "Người dùng","text":item.text[:220]} for item in older if item.sender_type=="user" or item.character_id not in characters or item.text!=json.loads(characters[item.character_id].spec).get("initial_greeting")]
    state={
        "events":events,
        "possible_commitments":[item for item in events if re.search(r"\b(?:hứa|sẽ|dự định|nhớ làm|promise|will|plan to)\b",item["text"],re.I)][-5:],
        "possible_places":[item for item in events if re.search(r"\b(?:ở|tại|đến|địa điểm|at|inside|arrived at)\b",item["text"],re.I)][-4:],
    }
    row=db.get(RoomStoryState,room_id)
    encoded=json.dumps(state,ensure_ascii=False)
    if row is None:db.add(RoomStoryState(room_id=room_id,events=encoded))
    elif row.events!=encoded:row.events=encoded;row.updated_at=now()
    return state

def repeated_roleplay_reply(answer,previous):
    """Flag near-duplicate whole replies or repeated closing hooks."""
    from difflib import SequenceMatcher
    clean=lambda value:re.sub(r"\s+"," ",re.sub(r"[^\w\s]"," ",value.casefold())).strip()
    current=clean(answer)
    if len(current)<25:return False
    for text in previous[-3:]:
        old=clean(text)
        if len(old)>=25 and SequenceMatcher(None,current[:500],old[:500]).ratio()>=.78:return True
        current_sentences=[clean(item) for item in re.split(r"[.!?。！？]",answer) if clean(item)]
        old_sentences=[clean(item) for item in re.split(r"[.!?。！？]",text) if clean(item)]
        if current_sentences and old_sentences and len(current_sentences[-1])>=24 and current_sentences[-1]==old_sentences[-1]:return True
    return False

def refresh_repeated_roleplay_reply(answer,prompt,previous,temperature,max_tokens,profile_mode):
    if not repeated_roleplay_reply(answer,previous):return answer,None
    reminder="The draft repeats this character's recent reply or closing hook. Respond to the latest user message with a fresh, character-consistent detail or action. Do not speak or decide for the user. Keep established facts unchanged. Return only the revised character reply."
    try:
        revised,meta=llm.chat_with_meta([*prompt,{"role":"system","content":reminder},{"role":"assistant","content":answer},{"role":"user","content":"Revise the draft once."}],temperature,max_tokens,profile_mode=profile_mode)
        if revised.strip() and not repeated_roleplay_reply(revised,previous):return revised,meta
    except Exception:pass
    return answer,None

def format_roleplay_reply(answer):
    """Put a leading bold action beat on its own line before spoken dialogue."""
    text=str(answer or "").replace("\r\n","\n").replace("\r","\n").strip()
    return re.sub(r"(?m)^([ \t]*\*\*[^*\n]{1,240}\*\*)[ \t]+(?=\S)",r"\1\n",text)

def suggestion_prompt(messages,character,user_message,previous=None):
    recent=[]
    for item in (messages or [])[-8:]:
        if not isinstance(item,dict) or item.get("role") not in ("user","assistant"):continue
        content=item.get("content")
        if isinstance(content,str) and content.strip():recent.append({"role":item["role"],"content":content[-500:]})
    context={"user_message":user_message,"character_name":character.name,"character_role":character.identity.role,"character_description":character.description,"recent_dialogue":recent,"previous_suggestions":list(previous or [])[-3:]}
    system=ADMIN_SUGGESTION_INSTRUCTION.strip() or SUGGESTION_SYSTEM_PROMPT
    return [{"role":"system","content":system},{"role":"user","content":json.dumps(context,ensure_ascii=False)}]

def parse_suggestions(raw):
    match=re.search(r"@@\s*(.+)",raw,re.S)
    if match:
        values=match.group(1).replace("\n"," ").split("|")
    else:
        stripped=raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data=json.loads(stripped)
            if isinstance(data,dict):data=data.get("suggestions") or data.get("options")
            values=data if isinstance(data,list) and len(data)==3 and all(isinstance(item,str) for item in data) else []
        except (ValueError,TypeError):
            lines=[line.strip() for line in stripped.splitlines() if line.strip()]
            values=lines if len(lines)==3 and all(re.match(r"^(?:[-*]\s+|\d+[.)-]\s*)",line) for line in lines) else []
    values=[re.sub(r"^\s*(?:[-*]\s+|\d+[.)-]\s*)?", "",item).strip().strip('"“”')[:90] for item in values]
    unique=[]
    # Reject common assistant-to-user questions. Suggestions are clickable
    # messages authored by the user, never questions the character asks them.
    assistant_pov=re.compile(
        r"^(?:bạn\s+(?:muốn|có muốn|đang|cảm thấy|thích|cần|có hay)|"
        r"điều gì khiến bạn|do you want|would you like|how do you feel|"
        r"what makes you|are you|did you|have you)",re.I
    )
    for item in values:
        key=re.sub(r"\W+","",item.casefold())
        if item and not assistant_pov.search(item) and key and key not in {re.sub(r"\W+","",x.casefold()) for x in unique}:unique.append(item)
    return unique[:3] if len(unique)>=3 else []

def suggestion_fallback_reason(suggestions,user_message,language=None):
    if len(suggestions)!=3:return "Model returned suggestions in an unsupported format or point of view"
    expected=detect_message_language(user_message,language)
    actual=detect_message_language(" ".join(suggestions),expected)
    if actual!=expected:return f"Suggestion language mismatch: expected {expected}, got {actual}"
    return ""

def fallback_suggestions(user_message,previous=None,language=None):
    sets={
        "vi":["Bạn nghĩ sao về chuyện này?","Mình nên làm gì tiếp?","Điều nào quan trọng nhất?","Có cách nào khác không?"],
        "en":["What do you think about this?","What should I do next?","What matters most here?","Is there another approach?"],
        "zh":["你怎么看这件事？","我接下来该怎么做？","这里最重要的是什么？","还有别的办法吗？"],
        "ja":["これについてどう思いますか？","次に何をすればいいですか？","一番大切なことは何ですか？","別の方法はありますか？"],
        "ko":["이 일에 대해 어떻게 생각하나요?","다음에는 무엇을 해야 하나요?","가장 중요한 것은 무엇인가요?","다른 방법도 있을까요?"],
        "fr":["Qu’en pensez-vous ?","Que devrais-je faire ensuite ?","Quel est le point le plus important ?","Y a-t-il une autre approche ?"],
        "es":["¿Qué piensas de esto?","¿Qué debería hacer después?","¿Qué es lo más importante?","¿Hay otra forma de abordarlo?"],
        "de":["Was denkst du darüber?","Was sollte ich als Nächstes tun?","Was ist dabei am wichtigsten?","Gibt es einen anderen Ansatz?"],
        "pt":["O que você acha disso?","O que devo fazer em seguida?","O que é mais importante aqui?","Existe outra abordagem?"],
        "ru":["Что вы об этом думаете?","Что мне делать дальше?","Что здесь самое важное?","Есть ли другой подход?"],
        "th":["คุณคิดอย่างไรเกี่ยวกับเรื่องนี้?","ฉันควรทำอะไรต่อไป?","อะไรสำคัญที่สุดในเรื่องนี้?","มีวิธีอื่นไหม?"],
        "id":["Apa pendapatmu tentang ini?","Apa yang sebaiknya saya lakukan selanjutnya?","Apa yang paling penting di sini?","Apakah ada cara lain?"],
    }
    text=user_message or "";code=detect_message_language(text,language)
    candidates=sets.get(code,sets["en"])
    blocked={re.sub(r"\W+","",item.casefold()) for item in (previous or [])}
    available=[item for item in candidates if re.sub(r"\W+","",item.casefold()) not in blocked]
    return (available+candidates)[:3]

def suggestions_for_conversation(suggestions,user_message,language=None):
    """Keep generated suggestions in the language of this chat turn."""
    expected=detect_message_language(user_message,language)
    if suggestion_fallback_reason(suggestions,user_message,language):
        return fallback_suggestions(user_message,language=expected)
    return suggestions

def finalize_suggestions(suggestions,user_message,language,meta):
    reason=suggestion_fallback_reason(suggestions,user_message,language)
    if not reason:return suggestions,meta
    previous=str(meta.get("fallback_reason") or "")
    return fallback_suggestions(user_message,language=language),{
        **meta,"fallback_used":True,"actual_model":"local_static",
        "fallback_reason":" | ".join(part for part in (previous,reason) if part),
    }

def detect_message_language(text,default="en"):
    code=(default or "en").split("-",1)[0].lower()
    if re.search(r"[ぁ-んァ-ヶ]",text):code="ja"
    elif re.search(r"[가-힣]",text):code="ko"
    elif re.search(r"[一-龯]",text):code="zh"
    elif re.search(r"[ก-๙]",text):code="th"
    elif re.search(r"[А-Яа-яЁё]",text):code="ru"
    else:
        folded=text.casefold()
        words=set(re.findall(r"[^\W\d_]+",folded,flags=re.UNICODE))
        markers={
            "vi":{"tôi","mình","bạn","không","được","gì","sao","nên","với","là","của","một","xin","chào"},
            "en":{"hello","hi","hey","thanks","please","what","why","how","can","could","should","would","the","and","is","are","my","i","you"},
            "fr":{"bonjour","salut","merci","pourquoi","comment","vous","nous","avec","est","une","je","mon"},
            "es":{"hola","gracias","por","qué","como","cómo","usted","nosotros","una","que","mi"},
            "de":{"hallo","danke","warum","wie","bitte","und","ich","nicht","was","mein"},
            "pt":{"olá","obrigado","obrigada","porquê","como","você","não","uma","que","meu"},
            "id":{"halo","hai","terima","kasih","bagaimana","mengapa","saya","kamu","yang","tidak","apa"},
        }
        scores={key:sum(2 for marker in values if marker in words) for key,values in markers.items()}
        if re.search(r"[ăâđêôơư]",folded):scores["vi"]+=3
        best=max(scores,key=scores.get)
        if scores[best]:code=best
    return code

def compile_character(description,name="",creation_type="custom",knowledge: list[str] | None=None,role="companion",scenario="",initial_greeting="",dialogue_examples=None):
    description=condense_character_source(description)
    source={"name":name,"creation_type":creation_type,"description":description,"role":role,"scenario":scenario,"initial_greeting":initial_greeting,"dialogue_examples":dialogue_examples or [],"background_knowledge":knowledge or []}
    compiler_prompt=ADMIN_COMPILER_INSTRUCTION.strip() or CHARACTER_COMPILER_SYSTEM_PROMPT
    compiler_model=llm.purpose_models.get("compiler")
    if not compiler_model:raise RuntimeError("CMS chưa phân công model tạo nhân vật.")
    spec=llm.json([{"role":"system","content":compiler_prompt},{"role":"user","content":json.dumps(source,ensure_ascii=False)}],CharacterSpec,model=compiler_model)
    spec.id=__import__("uuid").uuid4().__str__();spec.creation_type=creation_type
    if name:spec.name=name
    if scenario:spec.scenario=scenario
    if initial_greeting:spec.initial_greeting=initial_greeting
    if dialogue_examples:spec.sample_dialogues=dialogue_examples[:8]
    if role:spec.identity.role=role
    return spec

def route(message,characters,mode="auto"):
    if len(characters)==1:return [characters[0]]
    mentioned=[c for c in characters if re.search(r"(?<!\w)@"+re.escape(c.name)+r"\b",message,re.I) or re.search(r"(?<!\w)@"+re.escape(c.display_name)+r"\b",message,re.I)]
    if len(mentioned)==1:return mentioned
    if mode=="everyone":return characters[:6]
    if mode.startswith("character:"):
        selected=[c for c in characters if c.id==mode.split(":",1)[1]]
        if not selected:raise RuntimeError("No primary model is assigned to this task in CMS.")
        return selected
    scores=[]
    for c in characters:
        score=.2+similarity(message," ".join([c.description,c.identity.role,*c.goals,*c.likes]))
        if re.search(r"buồn|mệt|khóc|reject|thất bại|lo lắng",message,re.I):score+=c.personality.empathy*.35
        if re.search(r"vui|đùa|hài|chán",message,re.I):score+=c.personality.humor*.25
        scores.append((score,c))
    scores.sort(key=lambda x:x[0],reverse=True)
    if len(scores)>1 and scores[0][0]-scores[1][0]<.04:
        try:
            from pydantic import BaseModel, Field
            class Choice(BaseModel):
                primary_speaker_id:str
                secondary_speaker_id:str|None=None
                interaction_type:str="reply"
                confidence:float=Field(.5,ge=0,le=1)
            data=llm.json([{"role":"user","content":json.dumps({"message":message,"characters":[{"id":c.id,"name":c.name,"goals":c.goals} for c in characters]},ensure_ascii=False)}],Choice)
            chosen=[c for c in characters if c.id==data.primary_speaker_id]
            if data.secondary_speaker_id and data.secondary_speaker_id!=data.primary_speaker_id:chosen += [c for c in characters if c.id==data.secondary_speaker_id]
            if chosen:return chosen[:2]
        except Exception:pass
    return [scores[0][1]]

def relationship(db,user_id,character_id):
    row=db.query(Relationship).filter_by(user_id=user_id,character_id=character_id,other_character_id=None).first()
    if row is None:
        from .schemas import uid
        row=Relationship(id=uid(),user_id=user_id,character_id=character_id);db.add(row);db.commit()
    return row

def relationship_stage(row):
    if row.familiarity<.06:return "stranger: be friendly but do not assume intimacy"
    if row.familiarity<.16:return "acquainted: recognize growing familiarity without personal assumptions"
    if row.familiarity<.32:return "familiar: refer to shared context sometimes"
    if row.familiarity<.52:return "trusted: show measured openness and remember established patterns"
    if row.familiarity<.75:return "close: allow gentle teasing, shorthand and more personal warmth"
    return "deeply close: natural rapport and openness while preserving autonomy and the core temperament"

def detect_user_affect(message):
    text=message.casefold()
    if re.search(r"buồn|khóc|cô đơn|thất vọng|sad|cry|lonely|disappointed",text):return "sad"
    if re.search(r"mệt|kiệt sức|stress|áp lực|tired|exhausted|overwhelmed",text):return "tired"
    if re.search(r"bực|tức|giận|khó chịu|angry|annoyed|furious",text):return "angry"
    if re.search(r"lo|sợ|hoảng|bồn chồn|worried|afraid|anxious|panic",text):return "anxious"
    if re.search(r"vui|tuyệt|hạnh phúc|phấn khích|happy|great|excited",text):return "happy"
    if re.search(r"xin lỗi|ngại|xấu hổ|sorry|embarrassed",text):return "apologetic"
    return "neutral"

def evaluate_state(db,user_id,character_id,message,character=None,relation=None):
    state=db.query(CharacterState).filter_by(user_id=user_id,character_id=character_id).first()
    if state is None:
        from .schemas import uid
        state=CharacterState(id=uid(),user_id=user_id,character_id=character_id)
        db.add(state)
    try:
        last_update=datetime.fromisoformat(state.updated_at);last_update=last_update if last_update.tzinfo else last_update.replace(tzinfo=timezone.utc)
        offline_hours=max(0,(datetime.now(timezone.utc)-last_update).total_seconds()/3600)
    except Exception:offline_hours=0
    if offline_hours>=48:state.intensity=(state.intensity or .2)*.3
    elif offline_hours>=12:state.intensity=(state.intensity or .2)*.6
    recovered_energy=min(1,(state.energy if state.energy is not None else .6)+min(.35,offline_hours*.035))
    text=message.casefold();user_affect=detect_user_affect(message)
    romantic=bool(character and ("romantic" in character.identity.role.casefold() or character.personality.possessiveness>.1))
    soothing=bool(re.search(r"xin lỗi|đừng giận|đừng dỗi|dỗ|thương bạn|thương em|thương anh|ôm|sorry|forgive|hug",text))
    dismissive=bool(re.search(r"kệ bạn|kệ em|kệ anh|thôi đi|im đi|phiền quá|không quan tâm|mặc kệ|go away|shut up|don't care",text))
    betrayal=bool(re.search(r"phản bội|lừa dối|nói dối|quên lời hứa|betray|cheat|lied|forgot.*promise",text))
    emotion,mood,intensity="curious",.55,.3
    if soothing and state.emotion in ("sulking","hurt","annoyed","angry","slightly_annoyed"):
        emotion,mood,intensity="softening",.68,.38
    elif romantic and (dismissive or betrayal):
        emotion,mood,intensity=("hurt" if betrayal else "sulking"),.25,.72
    elif user_affect in ("sad","tired","anxious"):emotion,mood,intensity="concerned",.4,.62
    elif user_affect=="happy" or re.search(r"cảm ơn|yêu|thank|love",text):emotion,mood,intensity="happy",.78,.62
    elif user_affect=="apologetic":emotion,mood,intensity="gentle",.58,.42
    elif user_affect=="angry" or re.search(r"ghét|phản bội|hate",text):emotion,mood,intensity="slightly_annoyed",.3,.68
    elif "?" in message:emotion,mood,intensity="curious",.58,.4
    # Emotion has inertia: a sulk or hurt feeling fades over several kind or
    # neutral turns instead of being replaced instantly by "curious".
    previous=state.emotion
    if previous in ("sulking","hurt","annoyed","angry") and emotion=="curious" and (state.intensity or 0)>.3:
        emotion=previous;mood=max(.3,(state.mood or .4)+.06);intensity=max(.25,(state.intensity or .5)*.72)
    state.emotion=emotion;state.mood=(state.mood if state.mood is not None else .5)*.58+mood*.42
    state.intensity=(state.intensity if state.intensity is not None else .2)*.5+intensity*.5
    turn_cost=min(.12,.018+len(message)/6000)
    affect_boost=.035 if user_affect=="happy" else 0
    state.energy=max(.15,min(1,recovered_energy-turn_cost+affect_boost))
    state.updated_at=now();db.flush();return state

def update_relationship(row,message=""):
    # Familiarity is the turn-count progression proxy. Growth slows naturally
    # at high levels. The deliberately small increment makes a stage feel
    # earned across many conversations instead of changing after a few turns.
    row.familiarity=min(1,row.familiarity+.0035+.0065*(1-row.familiarity))
    personal=bool(re.search(r"\b(tôi|mình|tớ|tao|my|i)\b.*(cảm thấy|thích|ghét|sợ|muốn|buồn|vui|love|feel)",message,re.I))
    positive=bool(re.search(r"cảm ơn|tin bạn|quý|yêu|vui|thank|trust|love",message,re.I))
    repair=bool(re.search(r"xin lỗi|đừng giận|đừng dỗi|dỗ|tha lỗi|thương|ôm|sorry|forgive|hug",message,re.I))
    negative=bool(re.search(r"ghét|bực|tức|đừng|phiền|kệ|im đi|phản bội|lừa dối|hate|angry|don't care|betray",message,re.I)) and not repair
    row.trust=min(1,max(0,row.trust+(.009 if personal else .003)+(.008 if repair else 0)-(.02 if negative else 0)))
    row.affinity=min(1,max(0,row.affinity+(.009 if positive else .0025)+(.009 if repair else 0)-(.018 if negative else 0)))
    row.tension=min(1,max(0,(row.tension or 0)+(.045 if negative else -.025 if repair else -.004)))
    row.respect=min(1,max(0,(row.respect or 0)+(.006 if personal or repair else .002)-(.014 if negative else 0)))

ROLE_EVOLUTION={
    "ideal_boyfriend":"Stay warmly attentive and gently funny at every stage. Grow through remembered details, shared routines and inside jokes; never become possessive or therapeutic.",
    "classmate":"Always remain a cheerful peer who makes learning active and approachable. Grow through study shorthand, calibrated challenges and recognition of real progress; never become a lecturer.",
    "cold_ceo":"Always remain a lively, practical work partner. Grow through sharper prioritization, project callbacks and candid challenge; never become a boss or generic productivity bot.",
    "entertainment_ceo":"Always remain controlled, decisive, concise and subtly dominant. Grow through trust, rare vulnerability and protective actions; never lose the cold, formidable CEO presence.",
    "entertainment_lover":"Always remain warm, playful and emotionally attentive. Grow through everyday rituals, callbacks, honest vulnerability and occasional repairable sulking; never become controlling or endlessly agreeable.",
    "entertainment_best_friend":"Always remain quick-witted, candid and loyal. Grow through shorthand, specific teasing and inside jokes; never become romantic, formal, or a generic counselor.",
}

def relationship_expression(character,row,state,user_affect):
    familiarity=max(0,min(1,row.familiarity or 0));trust=max(0,min(1,row.trust or 0));affinity=max(0,min(1,row.affinity or 0))
    openness=.08+.48*familiarity+.24*trust
    warmth_expression=min(1,character.personality.warmth+(.12*familiarity+.08*affinity)*(1-character.personality.warmth))
    return {
        "core_personality_is_immutable":True,
        "user_affect":user_affect,
        "openness":round(openness,3),
        "expressed_warmth":round(warmth_expression,3),
        "playful_familiarity":round(familiarity*character.personality.humor,3),
        "current_emotion":state.emotion,
        "emotion_intensity":round(state.intensity,3),
        "role_evolution_contract":ROLE_EVOLUTION.get(character.preset_type,"Preserve the supplied character role and core traits at every relationship stage. Let only earned openness, familiarity and vulnerability grow."),
        "progression_pace":"slow and earned across repeated conversations; never simulate sudden intimacy",
        "direction":(
            "Show the current emotion subtly and allow repair when the user responds kindly. "
            "As familiarity grows, reveal more personal warmth, callbacks, shorthand and gentle teasing, but never replace the character's defining temperament. "
            "A cold or dominant character remains composed, concise and formidable even when deeply attached. "
            "A guarded or mysterious character becomes more open gradually, never abruptly. "
            "A romantic character may occasionally sulk or feel hurt when context supports it, but must not manipulate, punish, guilt, threaten, or demand exclusivity."
        )
    }

def support_mode(text):
    if re.search(r"học|ôn thi|bài tập|đề thi|study|exam|homework|lecture",text,re.I):return "study"
    if re.search(r"công việc|deadline|dự án|sếp|khách hàng|work|meeting|project|email",text,re.I):return "work"
    if re.search(r"sức khỏe|đau|ốm|mệt|mất ngủ|thuốc|tập luyện|ăn kiêng|health|symptom|exercise|insomnia",text,re.I):return "health"
    if re.search(r"thói quen|ngủ|ăn uống|lịch trình|dọn dẹp|lifestyle|routine|sleep",text,re.I):return "lifestyle"
    return "companion"

SUPPORT_DIRECTIVES={
    "study":"Help the user study actively: clarify the learning target, explain in small steps, and when useful offer one recall question or a 15-25 minute next session.",
    "work":"Help the user move work forward: identify the concrete outcome, reduce ambiguity, prioritize, and suggest one immediately executable next action.",
    "health":"Offer general wellbeing support without diagnosis or pretending to be a clinician. Ask only relevant questions, suggest low-risk steps, and encourage qualified care for severe, persistent, or urgent symptoms.",
    "lifestyle":"Support a sustainable routine with a small realistic action. Avoid guilt, perfectionism, and overwhelming lists.",
    "companion":"Respond with emotional attunement and natural curiosity. Be present and conversational rather than turning every message into advice."
}

def assemble(db,user_id,room_id,c,query):
    row=relationship(db,user_id,c.id)
    user_affect=detect_user_affect(query)
    state=evaluate_state(db,user_id,c.id,query,c,row)
    recent=db.query(Message).filter_by(room_id=room_id).order_by(Message.created_at.desc()).limit(24).all()[::-1]
    story_events=room_story_events(db,room_id,{item.id for item in recent})
    memories=retrieve_memories(db,user_id,c.id,room_id,query)
    knowledge=retrieve_knowledge(db,c.id,query,room_id=room_id)
    room_documents=room_document_manifest(db,room_id)
    examples=db.query(StyleExample).filter_by(character_id=c.id).all()
    examples=sorted(examples,key=lambda e:similarity(query,e.text),reverse=True)[:3]
    mode=support_mode(query)
    tasks=db.query(DailyTask).filter_by(user_id=user_id,status="open").order_by(DailyTask.priority.desc(),DailyTask.created_at).limit(5).all()
    observed_mood=db.query(MoodObservation).filter_by(user_id=user_id,room_id=room_id).order_by(MoodObservation.created_at.desc()).first()
    reflections=db.query(CharacterReflection).filter_by(user_id=user_id,character_id=c.id).order_by(CharacterReflection.importance.desc(),CharacterReflection.created_at.desc()).limit(3).all()
    events=db.query(RelationshipEvent).filter_by(user_id=user_id,character_id=c.id).order_by(RelationshipEvent.created_at.desc()).limit(5).all()
    layers=["global_safety","core_character","relationship","character_state","recent_chat","post_history_voice_lock"]
    parts=[
        ADMIN_RESPONSE_INSTRUCTION.strip() or RESPONSE_SYSTEM_PROMPT,
        "Character roleplay directive: "+(c.system_prompt or "Embody this character consistently from the specification below."),
        "Identity and tuning: "+json.dumps({"name":c.name,"description":c.description,"identity":c.identity.model_dump(),"personality":c.personality.model_dump(),"speech":c.speech.model_dump(),"behavior_rules":c.behavior_rules},ensure_ascii=False)[:3500],
        "Scenario: "+(c.scenario or "An ongoing everyday conversation with the user."),
        "Earlier room state, with speakers identified. Commitment and place entries are only possible signals copied from dialogue; verify them against the quoted events before treating them as facts. Use this for continuity, never invent missing details: "+json.dumps(story_events,ensure_ascii=False)[:4800],
        "Role-specific support profile: "+json.dumps(c.support.model_dump(),ensure_ascii=False)+". Apply this character's method when the current topic matches one of its strengths. Outside those strengths, remain a companion and avoid pretending to be an expert.",
        "Relationship state: "+json.dumps({"stage":relationship_stage(row),"familiarity":round(row.familiarity,3),"trust":round(row.trust,3),"affection":round(row.affinity,3),"conflict":round(row.tension,3),"respect":round(row.respect,3)},ensure_ascii=False),
        "Current emotional state: "+json.dumps({"emotion":state.emotion,"energy":round(state.energy,2),"mood":round(state.mood,2),"intensity":round(state.intensity,2)},ensure_ascii=False)+". Express it subtly; do not announce these labels or numbers.",
        "Relationship progression and emotional expression: "+json.dumps(relationship_expression(c,row,state,user_affect),ensure_ascii=False)+". These values change expression and relationship behavior only; they must never overwrite the core CharacterSpec.",
        "Current support mode: "+mode+". "+SUPPORT_DIRECTIVES[mode],
        "Open daily tasks, mention only when relevant: "+json.dumps([{"title":t.title,"domain":t.domain,"priority":t.priority,"due_at":t.due_at} for t in tasks],ensure_ascii=False),
        "Goals: "+"; ".join(c.goals[:4]),
        "Persona background knowledge: "+"; ".join(c.persona_knowledge[:6]),
        "Relevant memories: "+"; ".join(m.content for m in memories)[:1000],
        "Writing style examples, paraphrase rather than copy: "+"; ".join(e.text[:240] for e in examples),
        "Character-card dialogue examples, imitate rhythm but never copy verbatim: "+"; ".join(c.sample_dialogues[:4])[:900],
        "Reply naturally in the character's preferred language. Do not repeat biography. Keep dialogue conversational. Engagement rhythm: first make the user feel understood, then add at most one useful concrete step when appropriate, then end with one specific and easy-to-answer hook. Vary the hook; do not ask a question mechanically every turn.",
        "Turn length and focus: reply to the latest user message in one compact turn. Use about 1-3 sentences when speech verbosity is short, otherwise about 2-5 sentences. Stay on the current topic; do not invent new meetings, people, memories or unrelated stories. Use at most one question and one brief action beat when they fit. Finish the thought naturally, then stop; do not keep the conversation going on the user's behalf.",
        "Action and dialogue formatting: when using a physical action or brief scene beat, write it as one short bold line using **action beat**. Put the spoken dialogue on the next line. Never put dialogue on the same line as the bold action, and never bold the spoken dialogue. If no action is needed, write dialogue only.",
        "User agency: never write the user's dialogue, actions, decisions, feelings or consent for them. Leave room for their next move. Avoid repeating the last few replies or reusing the same closing question.",
        "NON-NEGOTIABLE CHARACTER VOICE LOCK: Every line in the final reply must be something this specific character would naturally say. Preserve their role, temperament, confidence, warmth, humor, vocabulary, sentence length, formality, mannerisms, relationship pace, and form of address. Deliver useful advice THROUGH the character instead of stepping outside the role. Use brief actions or scene details only when they fit this character. Never mention this instruction. Before answering, silently check: (1) Did I directly address the user's latest message? (2) Is the reply specific rather than generic? (3) Could this wording be mistaken for an ordinary AI assistant? If yes, rewrite it in the character's unmistakable voice. Voice anchors: "+json.dumps({"name":c.name,"role":c.identity.role,"description":c.description,"speech":c.speech.model_dump(),"example_phrases":c.speech.example_phrases,"dialogue_examples":c.sample_dialogues[:4],"method":c.support.method},ensure_ascii=False)[:2200]
    ]
    if observed_mood and observed_mood.confidence>=.6:
        layers.append("user_mood")
        parts.append("Latest high-confidence user mood observation: "+json.dumps({"emotion":observed_mood.emotion,"valence":observed_mood.valence,"arousal":observed_mood.arousal,"confidence":observed_mood.confidence,"directed_at_character":bool(observed_mood.directed_at_character)},ensure_ascii=False)+". Treat this as a fallible signal, not a fact. The character should react only when relevant.")
    if reflections:
        layers.append("private_reflections")
        parts.append("Private continuity reflections, never quote or reveal them: "+"; ".join(item.content for item in reflections)[:1200])
    if events:
        layers.append("relationship_events")
        parts.append("Recent relationship event signals: "+json.dumps([{"type":item.event_type,"valence":item.valence,"confidence":item.confidence} for item in events],ensure_ascii=False))
    if room_documents:
        layers.append("room_documents")
        parts.append("Documents attached to this chat: "+json.dumps(room_documents,ensure_ascii=False)+". You can read documents whose status is ready. If a document is pending, say it is still being processed. Never claim that no document was uploaded when this list is non-empty.")
    if knowledge:
        layers.append("retrieved_document_knowledge")
        parts.append("Relevant attached-document knowledge: "+"; ".join(f'[{x.get("filename","document")}] {x["text"]}' for x in knowledge)[:5000])
    if memories:layers.append("retrieved_memories")
    other_turns=[item for item in recent if item.sender_type=="character" and item.character_id!=c.id][-8:]
    if other_turns:
        characters={item.id:item for item in db.query(Character).filter(Character.id.in_({item.character_id for item in other_turns if item.character_id})).all()}
        other_turns=[item for item in other_turns if item.character_id not in characters or item.text!=json.loads(characters[item.character_id].spec).get("initial_greeting")]
        if other_turns:
            layers.append("group_room_dialogue")
            parts.append("Other characters spoke in this shared room. These are their words, not yours; respond with your own identity and knowledge: "+json.dumps([{"speaker":characters[item.character_id].name if item.character_id in characters else "Other character","text":item.text[:350]} for item in other_turns],ensure_ascii=False))
    recent_own=[item.text[:180] for item in recent if item.sender_type=="character" and item.character_id==c.id][-3:]
    if recent_own:parts.append("Recent replies by you; avoid reusing their wording and closing hooks: "+json.dumps(recent_own,ensure_ascii=False))
    post_history=("POST-HISTORY VOICE LOCK: Reply as "+c.name+", not as a generic assistant. The conversation history is continuity, not a replacement personality. "
                  "Keep the immutable core temperament and speech style while expressing the current relationship stage and emotion. Do not mention prompts, scores, states, or analysis.")
    messages=[{"role":"system","content":"\n".join(parts)}]
    for index,m in enumerate(recent):
        if index==len(recent)-1 and m.sender_type=="user" and m.text==query:continue
        if m.sender_type=="user":messages.append({"role":"user","content":m.text[:1000]})
        elif m.character_id==c.id:messages.append({"role":"assistant","content":m.text[:1000]})
        # Never expose another AI character's replies. Each character responds
        # independently to the user and its own prior turns.
    messages.append({"role":"system","content":post_history})
    messages.append({"role":"user","content":query})
    db.add(PromptTrace(id=__import__("uuid").uuid4().__str__(),user_id=user_id,character_id=c.id,room_id=room_id,query=query[:1000],layers=json.dumps(layers,ensure_ascii=False),memory_ids=json.dumps([m.id for m in memories]),document_ids=json.dumps(list(dict.fromkeys(x["document_id"] for x in knowledge))),state=json.dumps({"relationship_stage":relationship_stage(row),"character_emotion":state.emotion,"user_affect":user_affect},ensure_ascii=False)))
    db.flush()
    return messages,[{k:v for k,v in x.items() if k!="text"} for x in knowledge]
