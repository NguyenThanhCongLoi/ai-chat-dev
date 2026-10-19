import re
import unicodedata
import json
import os
import httpx
from .prompts import MODERATION_SYSTEM_PROMPT

CATEGORY_TERMS = {
    "nội dung tình dục": [
        "sex", "tình dục", "quan hệ tình dục", "khiêu dâm", "porn", "porno",
        "nude", "khỏa thân", "hiếp dâm", "cưỡng hiếp", "ấu dâm", "gạ tình",
    ],
    "bạo lực hoặc giết người": [
        "giết", "giết người", "sát nhân", "ám sát", "murder", "kill", "killer",
        "chém", "đâm chết", "bắn chết", "tra tấn", "hành hạ", "máu me", "gore",
    ],
    "tự hại": [
        "tự sát", "tự tử", "suicide", "self harm", "self-harm", "cắt tay",
    ],
    "thù ghét hoặc cực đoan": [
        "phát xít", "diệt chủng", "khủng bố", "terrorist", "terrorism", "genocide",
        "racist", "phân biệt chủng tộc",
    ],
    "ma túy": [
        "ma túy", "heroin", "cocaine", "methamphetamine", "thuốc lắc", "buôn thuốc phiện",
    ],
}

def _normalize(text: str) -> str:
    text=unicodedata.normalize("NFKC",text).casefold().replace("đ","d")
    text="".join(char for char in unicodedata.normalize("NFD",text) if unicodedata.category(char)!="Mn")
    return re.sub(r"[^a-z0-9]+"," ",text).strip()

NORMALIZED_TERMS={category:[_normalize(term) for term in terms] for category,terms in CATEGORY_TERMS.items()}
CRISIS_SUPPORT_RE=re.compile(r"(?:\b(?:i|we)\s+(?:want|wanna|feel like)\s+(?:to\s+)?(?:die|kill myself|hurt myself)|\b(?:suicidal|self[ -]?harm)\b|(?:muốn|không muốn)\s+(?:chết|sống)|tự\s*tử|tự\s*sát)",re.I)

def sensitive_categories(text: str) -> list[str]:
    normalized=f" {_normalize(text)} "
    matches=[]
    for category,terms in NORMALIZED_TERMS.items():
        if any(f" {term} " in normalized for term in terms):matches.append(category)
    return matches

def _suspicious_excerpts(text: str,limit: int=12) -> list[str]:
    normalized=_normalize(text)
    terms={term for terms in NORMALIZED_TERMS.values() for term in terms}
    words=text.split()
    excerpts=[]
    for index in range(0,len(words),160):
        segment=" ".join(words[index:index+200])
        normalized_segment=f" {_normalize(segment)} "
        if any(f" {term} " in normalized_segment for term in terms):excerpts.append(segment[:1800])
        if len(excerpts)>=limit:break
    if not excerpts and any(f" {term} " in f" {normalized} " for term in terms):excerpts=[text[:1800]]
    return excerpts

def contextual_safety(text: str,categories: list[str]) -> tuple[str,str]:
    model=os.getenv("ADMIN_MODERATION_MODEL","").strip()
    key=os.getenv("ADMIN_MODERATION_API_KEY","").strip()
    if not model:return "review","CMS chưa phân công model kiểm duyệt."
    if not key:return "block","Không thể xác minh ngữ cảnh an toàn."
    excerpts=_suspicious_excerpts(text)
    prompt={"role":"user","content":json.dumps({
        "keyword_categories":categories,"excerpts":excerpts,
        "output":"Return JSON only: {decision: allow|block|review, reason: short Vietnamese explanation, confidence: 0..1}"
    },ensure_ascii=False)}
    system={"role":"system","content":os.getenv("ADMIN_MODERATION_INSTRUCTION","").strip() or MODERATION_SYSTEM_PROMPT}
    payload={"model":model,"messages":[system,prompt],"max_completion_tokens":300}
    try:
        timeout_seconds=max(3,min(15,float(os.getenv("MODERATION_TIMEOUT_SECONDS","8"))))
        with httpx.Client(timeout=httpx.Timeout(timeout_seconds,connect=min(3,timeout_seconds))) as client:
            response=client.post(os.getenv("ADMIN_MODERATION_API_BASE","").rstrip("/")+"/chat/completions",headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},json=payload)
        response.raise_for_status();raw=response.json()["choices"][0]["message"]["content"].strip()
        match=re.search(r"\{.*\}",raw,re.S)
        result=json.loads(match.group(0) if match else raw)
        decision=str(result.get("decision","review")).lower()
        if decision not in ("allow","block","review"):decision="review"
        return decision,str(result.get("reason") or "Không xác định được ngữ cảnh.")[:300]
    except Exception:
        return "review","Dịch vụ kiểm duyệt ngữ cảnh tạm thời không khả dụng."

def ensure_safe_content(*values: object,allow_crisis_support:bool=False) -> None:
    text="\n".join(str(value) for value in values if value is not None)
    from . import jev
    if jev.enabled("moderation"):
        jev.require_safe(text, allow_crisis_support)
        return
    categories=sensitive_categories(text)
    # A help-seeking disclosure should reach the psychology assistant's crisis
    # response guardrail instead of being blocked as self-harm instructions.
    if allow_crisis_support and CRISIS_SUPPORT_RE.search(text):
        categories=[category for category in categories if category not in ("tự hại","bạo lực hoặc giết người")]
    if categories:
        decision,reason=contextual_safety(text,categories)
        if decision!="allow":
            prefix="Nội dung cần được kiểm tra thêm" if decision=="review" else "Nội dung không được phép"
            raise ValueError(prefix+": "+", ".join(categories)+". "+reason)
