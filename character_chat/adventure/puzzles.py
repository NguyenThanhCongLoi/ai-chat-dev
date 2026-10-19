"""Reusable deterministic checks; solutions are never projected to the browser."""
TYPES={"rune_order","symbol_match","fragment_assembly","timeline_order","evidence_deduction","artifact_slot"}
def check(puzzle,answer,state):
    if puzzle["type"] not in TYPES:raise ValueError("Unsupported puzzle")
    if not set(puzzle["required_items"])<=set(state["inventory"]):return False
    expected=puzzle["solution"]
    if puzzle["type"]=="artifact_slot":
        return isinstance(answer,list) and len(answer)==len(set(answer)) and set(answer)==set(expected)
    return type(answer) is type(expected) and answer==expected
