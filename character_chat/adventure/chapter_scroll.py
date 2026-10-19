"""Completion parchment uses only the chapter and outcome already earned."""
from .engine import chapter
from .story_enrichment import outro

def projection(s,loc):
    ch=chapter(s)
    if ch["id"] not in s["completed_chapters"]:return None
    if ch["order"]==1:
        from .chapter_one import config
        cfg=config(s)
        return {key:loc(cfg[key]) for key in ("chapter_end","scroll_title","scroll_body")}
    if ch["order"]==8:
        # Never substitute M08's hidden outcome for another ending.
        ending=next((e for e in s["config"]["adventure"]["endings"] if e["id"]==s.get("ending")),None)
        if not ending:return None
        paragraphs=[loc(e["text"]) for e in ending["events"] if e["type"]=="narration"]
        return dict(chapter_end=loc(outro(s)),scroll_title=loc(ending["title"]),scroll_body="\n\n".join(dict.fromkeys(paragraphs)))
    paragraphs=[loc(ch["localization"][ch[key]]) for key in ("summary_key","reflection_key")]
    return dict(chapter_end=loc(outro(s)),scroll_title=loc(ch["memory"]["title"]),scroll_body="\n\n".join(dict.fromkeys(paragraphs)))
