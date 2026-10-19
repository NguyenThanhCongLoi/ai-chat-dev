from collections import Counter
from test_memory_adventure import play_to_final
from character_chat.adventure import engine
from character_chat.adventure.loader import seed

def test_whole_arc_preserves_history_but_caps_main_utterances():
    s=play_to_final()
    counts=Counter((e.get("beat_id"),e.get("sequence_segment",0),e["type"]) for e in s["events"] if e.get("beat_id") and e.get("presentation")=="main" and e["type"] in ("NARRATION","CHARACTER_SPEECH"))
    assert counts and max(counts.values())==1
    assert any(e.get("presentation")=="archive" for e in s["events"])
    assert len(s["completed_chapters"])==7

def test_chapter_two_journal_does_not_queue_all_echoes():
    s=engine.fresh("a","s","",seed(),"en",.5);s["admin_preview"]=True
    s=engine.select_chapter(s,"selene_02")
    s=engine.advance(s,"go","archive")
    before={e["id"] for e in s["events"]}
    s=engine.advance(s,"inspect","selene_02_journal")
    fresh=[e for e in s["events"] if e["id"] not in before]
    assert sum(e["type"]=="CHARACTER_SPEECH" and e.get("auto_voice",True) for e in fresh)==1
    assert sum(e["type"]=="NARRATION" and e.get("presentation")=="main" for e in fresh)==1
    assert any(e.get("speaker")=="unknown_girl" for e in fresh)
    assert "selene_02_journal" in s["inspected"]

def test_memory_movie_reuses_the_exact_preloaded_asset_url():
    from character_chat.adventure.projection import view
    from test_chapter_one_sequence import gate_ready
    s=engine.advance(gate_ready(),"open_gate")
    s=engine.advance(s,"finish_gate_cinematic")
    out=view(s,{"id":"s","name":"Selene"})
    clip=out["memory_video"]
    assert clip["url"]==out["assets"][clip["id"]]["url"]
    assert "?v=" in clip["url"]
