"""Small, declarative condition groups; the same evaluator serves gates and endings."""
def allows(condition,state):
    if not condition:return True
    if "all" in condition:return all(allows(c,state) for c in condition["all"])
    if "any" in condition:return any(allows(c,state) for c in condition["any"])
    if "not" in condition:return not allows(condition["not"],state)
    if "flag" in condition:return bool(state["flags"].get(condition["flag"]))
    if "inventory" in condition:return condition["inventory"] in state["inventory"]
    if "memory" in condition:return condition["memory"] in state["core_memories"]
    if "chapter" in condition:return condition["chapter"] in state["completed_chapters"]
    if "choice" in condition:return any(c["id"]==condition["choice"] for c in state["choices"])
    if "stat" in condition:return state["stats"].get(condition["stat"],0)>=condition.get("gte",0)
    for field,target in (("echo_count","echoes"),("memory_count","core_memories"),("lore_count","lore_fragments")):
        if field in condition:return len(state[target])>=condition[field].get("gte",0)
    return False
