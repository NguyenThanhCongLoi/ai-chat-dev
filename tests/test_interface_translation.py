import os
os.environ.setdefault("DATABASE_URL", "sqlite://")
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest
from character_chat.db import Base, AppSetting
import character_chat.main as main

@pytest.fixture
def translation_db():
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()

def test_long_translation_batches_have_enough_tokens(translation_db,monkeypatch):
    monkeypatch.setattr(main.llm,"purpose_models",{"suggestion":"cms-translator"})
    texts=[str(index)+"Một câu mô tả dài. "*40 for index in range(8)]
    calls=[]
    def translate(messages,**kwargs):
        values=json.loads(messages[-1]["content"])
        assert len(values)<=6
        assert len(values)==1 or sum(map(len,values))<=1800
        assert kwargs["max_tokens"]>=sum(map(len,values))*4
        assert kwargs["model"]=="cms-translator"
        calls.append(values)
        return json.dumps(["Translated "+value for value in values])
    monkeypatch.setattr(main.llm,"chat",translate)
    result=main.translate_interface_content({"language":"en","texts":texts},translation_db,"user")
    assert not result["failures"]
    assert len(calls)>1
    assert result["translations"]==[("Translated "+value).strip() for value in texts]

def test_model_assignment_failure_is_explicit(translation_db,monkeypatch):
    monkeypatch.setattr(main.llm,"purpose_models",{})
    monkeypatch.setattr(main.llm,"model","")
    result=main.translate_interface_content({"language":"ja","texts":["Chào bạn"]},translation_db,"user")
    assert result["failures"]==[{"index":0,"code":"model_not_assigned"}]
    assert translation_db.query(AppSetting).count()==0

@pytest.mark.parametrize("error,code",[
    ("Gateway HTTP 401 private-key-value","credentials"),
    ("ReadTimeout: The read operation timed out","timeout"),
    ("TokenLimitError: Model stopped at the token limit","output_limit"),
])
def test_gateway_errors_return_safe_failure_codes(translation_db,monkeypatch,error,code):
    monkeypatch.setattr(main.llm,"purpose_models",{"suggestion":"cms-translator"})
    def fail(*args,**kwargs):raise RuntimeError(error)
    monkeypatch.setattr(main.llm,"chat",fail)
    result=main.translate_interface_content({"language":"ja","texts":["Chào bạn"]},translation_db,"user")
    assert result["failures"]==[{"index":0,"code":code}]
    assert "private-key-value" not in json.dumps(result)
    assert translation_db.query(AppSetting).count()==0


def test_myanmar_cache_in_wrong_language_is_replaced(translation_db,monkeypatch):
    import hashlib
    source="Chào bạn, mình là Ruby."
    key="translation:my:"+hashlib.sha256(source.encode()).hexdigest()
    translation_db.add(AppSetting(key=key,value="Hello, I am Ruby."))
    translation_db.commit()
    calls=[]
    monkeypatch.setattr(main.llm,"purpose_models",{"suggestion":"cms-translator"})
    def translate(messages,**kwargs):
        calls.append(messages)
        assert "Burmese (Myanmar)" in messages[0]["content"]
        assert "language code: my" in messages[0]["content"]
        return json.dumps(["မင်္ဂလာပါ၊ Ruby ပါ။"],ensure_ascii=False)
    monkeypatch.setattr(main.llm,"chat",translate)
    result=main.translate_interface_content({"language":"my","texts":[source]},translation_db,"user")
    assert not result["failures"]
    assert result["translations"]==["မင်္ဂလာပါ၊ Ruby ပါ။"]
    assert translation_db.get(AppSetting,key).value==result["translations"][0]
    main.translate_interface_content({"language":"my","texts":[source]},translation_db,"user")
    assert len(calls)==1


def test_only_invalid_fields_are_repaired_and_cache_keeps_valid_fields(translation_db,monkeypatch):
    monkeypatch.setattr(main.llm,"purpose_models",{"suggestion":"cms-translator"})
    calls=[]
    def translate(messages,**kwargs):
        texts=json.loads(messages[-1]["content"])
        calls.append(texts)
        if len(texts)==2:
            return json.dumps(["မင်္ဂလာပါ။","English fallback"],ensure_ascii=False)
        return json.dumps(["သင်ဘယ်သူလဲ။"],ensure_ascii=False)
    monkeypatch.setattr(main.llm,"chat",translate)
    result=main.translate_interface_content({"language":"my","texts":["Xin chào","Bạn là ai"]},translation_db,"user")
    assert not result["failures"]
    assert calls==[["Xin chào","Bạn là ai"],["Bạn là ai"]]
    assert translation_db.query(AppSetting).count()==2


def test_malformed_batch_retries_as_individual_items(translation_db,monkeypatch):
    monkeypatch.setattr(main.llm,"purpose_models",{"suggestion":"cms-translator"})
    calls=[]
    def translate(messages,**kwargs):
        texts=json.loads(messages[-1]["content"])
        calls.append(texts)
        if len(texts)>1:return "not JSON"
        return json.dumps(["မင်္ဂလာပါ။"],ensure_ascii=False)
    monkeypatch.setattr(main.llm,"chat",translate)
    result=main.translate_interface_content({"language":"my","texts":["Xin chào","Chào bạn"]},translation_db,"user")
    assert not result["failures"]
    assert len(calls)==3


def test_invalid_myanmar_output_has_bounded_retry_and_is_not_cached(translation_db,monkeypatch):
    monkeypatch.setattr(main.llm,"purpose_models",{"suggestion":"cms-translator"})
    calls=[]
    def translate(messages,**kwargs):
        calls.append(messages)
        return json.dumps(["Hello"])
    monkeypatch.setattr(main.llm,"chat",translate)
    result=main.translate_interface_content({"language":"my","texts":["Xin chào"]},translation_db,"user")
    assert result["failures"]==[{"index":0,"code":"invalid_translation"}]
    assert len(calls)==2
    assert translation_db.query(AppSetting).count()==0


def test_translation_validation_preserves_placeholders_and_neutral_text():
    from character_chat.translation_validation import valid_translation
    assert valid_translation("Xin chào {name}","မင်္ဂလာပါ {name}","my")
    assert not valid_translation("Xin chào {name}","မင်္ဂလာပါ","my")
    assert valid_translation("…","…","my")
    assert valid_translation("မင်္ဂလာပါ","မင်္ဂလာပါ","my")
    assert not valid_translation("Xin chào","Hello","my")
