import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from character_chat import main

def test_ui_translation_uses_friendly_style_but_character_translation_keeps_its_own_tone(monkeypatch,tmp_path):
    engine=create_engine("sqlite:///"+str(tmp_path/"locale.sqlite"))
    main.Base.metadata.create_all(engine)
    calls=[]
    monkeypatch.setattr(main.llm,"model","translation-model")
    monkeypatch.setattr(main.llm,"purpose_models",{})
    def translate(messages,**kwargs):
        calls.append(messages)
        return json.dumps(["We're getting things ready!"])
    monkeypatch.setattr(main.llm,"chat",translate)
    with sessionmaker(engine)() as db:
        db.add(main.User(id="u"));db.commit()
        result=main.translate_interface_content({"language":"en","texts":["Chờ chút nhé, mình đang chuẩn bị đây!"]},db,"u")
        assert result["translations"]==["We're getting things ready!"]
        assert "warm, welcoming, gently playful" in calls[-1][0]["content"]
        assert "never a literal proverb" in calls[-1][0]["content"]
        result=main.translate_interface_content({"language":"en","texts":["Một chiến binh lạnh lùng."],"kind":"character"},db,"u")
        assert result["translations"]==["We're getting things ready!"]
        assert "warm, welcoming, gently playful" not in calls[-1][0]["content"]
    engine.dispose()
