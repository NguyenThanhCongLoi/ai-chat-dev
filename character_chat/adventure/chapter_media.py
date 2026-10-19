"""A stable preparation manifest for every scene of the active chapter."""
def asset_ids(s, assets):
    from .engine import chapter
    from .embedded_scenes import layout
    from .props import hotspot_art, inventory_art
    from .story_enrichment import extra, visuals
    ch = chapter(s)
    selected = {ch["memory"]["video"], ch["memory"].get("background", "memory_space")}
    events = list(ch["memory"]["events"])
    for place in ch["scenes"]:
        selected.add(place["background"])
        painted = layout(s, place)
        if painted:
            selected.add(painted["asset"])
            if painted.get("after_inspection"):
                selected.add(painted["after_inspection"]["asset"])
        events.extend(place["events"])
        for obj in place["hotspots"]:
            ident = hotspot_art(obj, place).get("asset")
            if ident:
                selected.add(ident)
            if obj.get("item"):
                selected.add(inventory_art(obj["item"],assets))
            events.extend(obj["events"])
            events.extend(extra(s, obj["id"]))
    for puzzle in ch["puzzles"]:
        events.extend(puzzle["events"])
        events.extend(extra(s, puzzle["id"]))
    mapping = visuals(s["config"])
    keys = {e.get("visual_event") for e in events}
    keys.add({1: "LOCATION_ENTER", 3: "MAGIC_SEAL_ACTIVATE", 6: "VAULT_AWAKEN", 7: "MAGIC_SEAL_ACTIVATE", 8: "CHAPTER_COMPLETE"}.get(ch["order"], ""))
    for key in keys:
        ident = mapping.get(key, {}).get("cinematic")
        if ident:
            selected.add(ident)
    if ch["order"] == 1:
        selected.update(("enter_ruins_video","prop_ch02_petal_under_stone"))
    if ch["order"] == 8:
        from .replacement_media import DATA
        selected.update(DATA["ending_videos"].values())
        selected.update(("ending_video_hidden","official_bg_ch08_final_chamber_secret"))
    # A failed/skipped cinematic must already have a decoded fallback image.
    pending=list(selected)
    while pending:
        ident=pending.pop()
        fallback=assets.get(ident,{}).get("fallback")
        if fallback in assets and fallback not in selected:
            selected.add(fallback);pending.append(fallback)
    return selected & assets.keys()
