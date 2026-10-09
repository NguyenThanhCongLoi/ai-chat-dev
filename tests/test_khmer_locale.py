import json
import hashlib
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from character_chat.models import Base,AppSetting,User
from character_chat.translation_validation import valid_translation
from character_chat.speech_language import detect_speech_language,speech_info
import character_chat.main as main

def test_khmer_pack_covers_catalog_and_preserves_placeholders():
    pack=json.loads(Path("frontend/src/locales/km.json").read_text(encoding="utf-8"))
    catalog=json.loads(Path("frontend/src/locales/catalog.json").read_text(encoding="utf-8"))
    assert len(pack)>=len(catalog)
    assert all(valid_translation(item["source"],pack[item["source"]],"km") for item in catalog)
    assert valid_translation("Trò chuyện với {name}","ជជែកជាមួយ {name}","km")
    assert not valid_translation("Trò chuyện với {name}","ជជែកជាមួយអ្នក","km")
    assert not valid_translation("Trang chủ","Home","km")

def test_khmer_intro_translation_is_cached_and_shared(monkeypatch):
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    monkeypatch.setattr(main.llm,"model","test")
    monkeypatch.setattr(main.llm,"purpose_models",{})
    calls=[]
    def chat(messages,**kwargs):
        assert "Khmer (Cambodia)" in messages[0]["content"]
        calls.append(messages)
        return json.dumps(["ដៃគូដែលនៅក្បែរអ្នកជានិច្ច"],ensure_ascii=False)
    monkeypatch.setattr(main.llm,"chat",chat)
    with Session(engine) as db:
        db.add_all([User(id="one"),User(id="two")]);db.commit()
        source="A companion always by your side."
        for user in ["one","one","two"]:
            result=main.translate_interface_content({"language":"km","texts":[source],"kind":"character"},db,user)
            assert not result["failures"]
            assert result["translations"]==["ដៃគូដែលនៅក្បែរអ្នកជានិច្ច"]
            digest=hashlib.sha256(source.encode()).hexdigest()
            assert db.get(AppSetting,f"character_translation:v3:{user}:km:{digest}")
        assert len(calls)==1
    engine.dispose()

def test_khmer_is_not_mislabeled_as_english_voice():
    text="សួស្តី តើអ្នកសុខសប្បាយទេ?"
    assert detect_speech_language(text,"en")=="km"
    assert not speech_info(text)["speech_supported"]
