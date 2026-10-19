"""Static authored text translations; CMS text always wins, no provider at render time."""
from functools import lru_cache
import hashlib,json
from pathlib import Path
@lru_cache(maxsize=1)
def catalog():
    p=Path(__file__).resolve().parents[1]/"story_data/moonfall_arc/translations.json"
    return json.loads(p.read_text(encoding="utf8")) if p.is_file() else {}
def translations(value):
    if not isinstance(value,dict) or not all(isinstance(value.get(k),str) for k in ("vi","en")):return {}
    key=hashlib.sha256(json.dumps({k:value[k] for k in ("vi","en")},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return catalog().get(key,{})
def enrich(value):
    if isinstance(value,dict):
        if all(isinstance(value.get(k),str) for k in ("vi","en")):return {**translations(value),**value}
        return {k:enrich(v) for k,v in value.items()}
    if isinstance(value,list):return [enrich(v) for v in value]
    return value

def observation_hint(title):
    from ..moonfall import localized,LANGUAGES
    patterns={"vi":"Hãy quan sát kỹ: {object}.","en":"Take a closer look at {object}.","ja":"{object}をよく調べてみよう。","zh":"仔细看看{object}。","ko":"{object}을 자세히 살펴보자.","my":"{object} ကို သေချာကြည့်ကြည့်ပါ။","km":"សាកពិនិត្យមើល {object} ឱ្យបានច្បាស់។"}
    return {lang:pattern.replace("{object}",localized(title,lang)) for lang,pattern in patterns.items()}
