"""Every earned chapter has a localized parchment; endings remain isolated."""
from copy import deepcopy
import pytest
from test_memory_adventure import play_to_final
from character_chat.adventure import engine
from character_chat.adventure.loader import seed
from character_chat.adventure.projection import view

LANGUAGES=("vi","en","ja","zh","ko","my","km")

@pytest.mark.parametrize("language",LANGUAGES)
def test_parchments_for_first_seven_chapters(language):
    s=play_to_final();bodies=[]
    for n in range(1,8):
        current=engine.select_chapter(s,f"selene_0{n}")
        current["content_language"]=language
        result=view(current,{"id":"selene","name":"Selene"})
        scroll=result["chapter_scroll"]
        assert scroll and all(isinstance(value,str) and value.strip() for value in scroll.values())
        bodies.append(scroll["scroll_body"])
        if language not in ("vi","en"):
            english=deepcopy(current);english["content_language"]="en"
            from character_chat.adventure.languages import enrich
            ch=engine.chapter(current)
            translated=n==1 or any(enrich(ch['localization'][ch[k]]).get(language) for k in ('summary_key','reflection_key'))
            english_body=view(english,{"id":"selene","name":"Selene"})["chapter_scroll"]["scroll_body"]
            # Revised VI/EN prose falls back honestly until new translations exist.
            assert (scroll['scroll_body']!=english_body)==translated
    assert len(set(bodies))==7

@pytest.mark.parametrize("index",[0,1,2,3])
@pytest.mark.parametrize("language",LANGUAGES)
def test_last_parchment_matches_only_chosen_ending(index,language):
    s=play_to_final()
    options=s["config"]["chapters"][7]["choice"]["options"]
    if index==3:s["ending_offer_at"]=0;choice="remember_without_becoming"
    else:choice=options[index]["id"]
    s=engine.advance(s,"choice",choice);s=engine.advance(s,"confirm_ending")
    if s["phase"]=="memory":s=engine.advance(s,"finish_memory_cinematic")
    s["content_language"]=language
    result=view(s,{"id":"selene","name":"Selene"})
    scroll=result["chapter_scroll"]
    assert scroll["scroll_title"]==result["ending"]["title"]
    from character_chat.moonfall import localized
    expected=next(e for e in s["config"]["adventure"]["endings"] if e["id"]==s["ending"])
    assert scroll["scroll_body"]=="\n\n".join(localized(e["text"],language) for e in expected["events"] if e["type"]=="narration")

def test_no_completion_copy_before_chapter_is_finished():
    s=engine.fresh("alice","selene","",seed(),"en",.5)
    assert view(s,{"id":"selene","name":"Selene"})["chapter_scroll"] is None
    final=play_to_final()
    assert view(final,{"id":"selene","name":"Selene"})["chapter_scroll"] is None
