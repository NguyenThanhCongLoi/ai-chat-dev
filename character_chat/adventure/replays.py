"""A replay starts a separate attempt; browsing finished chapters never rerolls it."""
from copy import deepcopy
import time
from .conditions import allows

def collected(s):
    result=deepcopy(s.get("ending_collection",{}))
    if s.get("ending") and not (s.get("admin_preview") or s.get("debug_only")):
        result.setdefault(s["ending"],{"attempt":s.get("attempt_id",s["id"]),"at":s.get("created_at",0)})
    return result

def full_route(s):
    chapters=s["config"]["chapters"]
    expected=[c["id"] for c in chapters[:-1]]
    done=[c for c in s["completed_chapters"] if c in expected]
    choices=[c["chapter"] for c in s["choices"] if c["chapter"] in expected]
    return done==expected and choices==expected

def restart(old):
    from .engine import fresh
    if not old.get("ending") or len(old["completed_chapters"])!=8:raise ValueError("Finish the current attempt first")
    new=fresh(old["owner"],old["character_id"],old["source_id"],old["config"],old["content_language"],old["world_trust"])
    if old.get("admin_preview"):
        new["admin_preview"]=True;new["debug_only"]=True
    new["attempt_id"]=new["id"]
    new["id"]=old["id"]
    new["revision"]=old["revision"]
    new["attempt_number"]=old.get("attempt_number",1)+1
    new["ending_collection"]=collected(old)
    new["finished_attempts"]=deepcopy(old.get("finished_attempts",[]))+[dict(attempt=old.get("attempt_id",old["id"]),ending=old["ending"],completed_at=time.time(),memories=deepcopy(old["memories"]))]
    return new

def record(s):
    if s.get("admin_preview") or s.get("debug_only"):return
    collection=collected(s)
    # Called before s.ending is set so only the winning attempt is recorded.
    ending=s["pending_ending"]
    s["ending_is_new"]=ending not in collection
    collection.setdefault(ending,{"attempt":s.get("attempt_id",s["id"]),"at":time.time()})
    s["ending_collection"]=collection

def ending_allowed(s,ending):
    # All outcomes require the current attempt's full route. Hidden ending also
    # checks authored clues, behaviour and flags gathered during that attempt.
    if not s.get("admin_preview") and not full_route(s):return False
    if s.get("admin_preview"):return ending in {e["id"] for e in s["config"]["adventure"]["endings"]}
    if ending=="between_memory_and_moonlight":
        return allows(s["config"]["adventure"]["hidden_ending"],s)
    return ending in {"remember_me","let_me_forget","new_keeper"}


def preview_ending(old,ending):
    """Owner-isolated admin preview; no normal attempt or collection is changed."""
    from .engine import replay_preview,begin_memory
    if not old.get("admin_preview"):raise ValueError("Admin preview required")
    definition=next((e for e in old["config"]["adventure"]["endings"] if e["id"]==ending),None)
    if not definition:raise ValueError("Unknown ending")
    final=old["config"]["chapters"][-1]
    s=replay_preview(old,final["id"])
    s["pending_ending"]=ending;s["proposed_ending"]=ending
    s["ending_is_new"]=True
    s["choices"].append(dict(id=ending,chapter=final["id"],label=deepcopy(definition["title"])))
    begin_memory(s)
    return s
