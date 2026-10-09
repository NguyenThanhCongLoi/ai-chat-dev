import concurrent.futures, re
from urllib.parse import quote
import httpx

WIKI_API="https://{lang}.wikipedia.org/w/api.php"

def _wiki_search(lang,query):
    headers={"User-Agent":"AI-Role-Play/1.0 character research"}
    with httpx.Client(timeout=12,headers=headers,follow_redirects=True) as client:
        found=client.get(WIKI_API.format(lang=lang),params={"action":"query","list":"search","srsearch":query,"srlimit":3,"format":"json","utf8":1}).json()
        titles=[item["title"] for item in found.get("query",{}).get("search",[])][:3]
        if not titles:return []
        pages=client.get(WIKI_API.format(lang=lang),params={"action":"query","prop":"extracts","exintro":1,"explaintext":1,"titles":"|".join(titles),"format":"json","utf8":1}).json()
    result=[]
    for page in pages.get("query",{}).get("pages",{}).values():
        text=re.sub(r"\s+"," ",page.get("extract","")).strip()
        if text:result.append({"title":page.get("title",""),"text":text[:3500],"url":f"https://{lang}.wikipedia.org/wiki/{quote(page.get('title','').replace(' ','_'))}"})
    return result

def research_media_character(name,title=""):
    query=" ".join(x for x in (name,title) if x).strip()
    if not query:return {"brief":"","sources":[]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(_wiki_search,lang,query) for lang in ("vi","en")]
        sources=[]
        for future in futures:
            try:sources.extend(future.result())
            except Exception:continue
    unique=[];seen=set()
    for item in sources:
        key=item["title"].casefold()
        if key not in seen:seen.add(key);unique.append(item)
    brief="\n\n".join(f"Source: {x['title']}\n{x['text']}" for x in unique[:5])[:12000]
    return {"brief":brief,"sources":[{"title":x["title"],"url":x["url"]} for x in unique[:5]]}
