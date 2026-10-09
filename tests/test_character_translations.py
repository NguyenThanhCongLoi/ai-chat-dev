
import json
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from character_chat.models import Base,AppSetting,User
from character_chat import main

def test_any_source_language_translates_to_vi_and_persists_per_user(monkeypatch):
    engine=create_engine("sqlite://");Base.metadata.create_all(engine)
    outputs={'"Hello, I am Mia."':'"Xin chào, tôi là Mia."','"Good morning, Mia."':'"Chào buổi sáng, Mia."',"你好，我是Mia。":"Hello, I am Mia."}
    calls=[]
    monkeypatch.setattr(main.llm,"model","test")
    monkeypatch.setattr(main.llm,"purpose_models",{})
    def chat(messages,**kwargs):
        sources=json.loads(messages[-1]["content"]);calls.append(sources)
        return json.dumps([outputs[source] for source in sources],ensure_ascii=False)
    monkeypatch.setattr(main.llm,"chat",chat)
    with sessionmaker(engine)() as db:
        db.add_all([User(id="one"),User(id="two")]);db.commit()
        source='"Hello, I am Mia."'
        for user in ["one","one","two"]:
            result=main.translate_interface_content({"language":"vi","texts":[source],"kind":"character"},db,user)
            assert result["translations"]==[outputs[source]] and not result["failures"]
            digest=hashlib.sha256(source.encode()).hexdigest()
            assert db.get(AppSetting,f"character_translation:v3:{user}:vi:{digest}").value==outputs[source]
        assert len(calls)==1
        changed='"Good morning, Mia."'
        result=main.translate_interface_content({"language":"vi","texts":[changed],"kind":"character"},db,"one")
        assert result["translations"]==[outputs[changed]] and len(calls)==2
        result=main.translate_interface_content({"language":"en","texts":["你好，我是Mia。"],"kind":"character"},db,"one")
        assert result["translations"]==["Hello, I am Mia."] and not result["failures"]
        result=main.translate_interface_content({"language":"vi","texts":["Xin chào, tôi là Mia."],"kind":"character"},db,"one")
        assert result["translations"]==["Xin chào, tôi là Mia."] and len(calls)==3
    engine.dispose()

def test_regular_vi_ui_does_not_need_inference(monkeypatch):
    monkeypatch.setattr(main.llm,"chat",lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("No gateway call")))
    assert main.translate_interface_content({"language":"vi","texts":["Tất cả"]},None,"user")=={"translations":["Tất cả"]}
