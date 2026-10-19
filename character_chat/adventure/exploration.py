"""Exploration gates derived from saved inspections, never browser timing."""
from .conditions import allows

def scene_open(s, target):
    from .engine import chapter
    ch = chapter(s)
    if s.get('admin_preview') or s.get('reviewing') or ch['id'] in s['completed_chapters']:
        return True
    if ch['id'] + ':' + target['id'] in s['visited']:
        return True
    required = set(ch['required_inspections'])
    before = []
    for place in ch['scenes']:
        if place['id'] == target['id']:
            return set(before) <= set(s['inspected'])
        before.extend(o['id'] for o in place['hotspots'] if o['id'] in required)
    return False

def next_object(s, place):
    """One unresolved target per physical map; optional clues never block the route."""
    from .engine import chapter
    candidates = [(origin, obj) for origin in chapter(s)["scenes"]
                  if same_map(s, origin["id"], place["id"]) and scene_open(s, origin)
                  for obj in origin["hotspots"]
                  if obj["id"] not in s["inspected"] and allows(obj.get("requires"), s)]
    return next((pair for pair in candidates if not pair[1]["optional"]),
                candidates[0] if candidates else None)

def object_open(s, place, obj):
    if not allows(obj.get("requires"), s):
        return False
    if obj["id"] in s["inspected"] or s.get("reviewing"):
        return True
    target = next_object(s, place)
    return bool(target and target[1]["id"] == obj["id"])

def map_key(s, place):
    from .embedded_scenes import DATA
    visual = DATA["scenes"].get(s["chapter_id"] + ":" + place["id"])
    if visual and visual.get("background", place["background"]) == place["background"]:
        return visual.get("physical_map",visual["path"])
    asset = next((a for a in s["config"]["assets"] if a["id"] == place["background"]), None)
    return asset["path"] if asset else place["background"]

def same_map(s, first, second):
    from .engine import chapter
    places = {p["id"]: p for p in chapter(s)["scenes"]}
    return map_key(s, places[first]) == map_key(s, places[second])

def advance_same_map(s):
    from .engine import chapter, scene, enter_scene
    if s.get("reviewing"):
        return
    ch, place = chapter(s), scene(s)
    needed = {o["id"] for o in place["hotspots"] if o["id"] in ch["required_inspections"]}
    if not needed or not needed <= set(s["inspected"]):
        return
    index = ch["scenes"].index(place)
    if index + 1 < len(ch["scenes"]):
        target = ch["scenes"][index + 1]
        if same_map(s, place["id"], target["id"]) and scene_open(s, target):
            enter_scene(s, target["id"])

def locations(s):
    from .engine import chapter
    groups = {}
    for place in chapter(s)["scenes"]:
        groups.setdefault(map_key(s, place), []).append(place)
    preferred = {"ancient_gate", "side_path", "outer_ruins", "inner_ruins", "moonflower_garden", "archive",
                 "descent", "chamber", "past", "collapse_passage", "records", "witch_house",
                 "vault", "mirror_hall", "corridor", "temple", "pale_chamber", "memory_space", "pendant_echo", "final_chamber"}
    result = []
    for rows in groups.values():
        current = next((p for p in rows if p["id"] == s["location"]), None)
        opened = [p for p in rows if scene_open(s, p)]
        unexplored = [p for p in opened if s["chapter_id"] + ":" + p["id"] not in s["visited"]]
        target = current or (unexplored[0] if unexplored else opened[-1] if opened else rows[0])
        # A cleared stage does not send the player back through old dialogue.
        if not current and s.get("reviewing"):
            target = rows[0]
        name = next((p["title"] for p in rows if p["id"] in preferred), rows[0]["title"])
        from .embedded_scenes import layout
        painted=layout(s,target)
        result.append(dict(id=target["id"], title=name, background=painted["asset"] if painted else target["background"],
                           locked=not bool(opened), scene_ids=[p["id"] for p in rows]))
    return result
