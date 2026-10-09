from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from character_chat import bundled_expressions as module
from character_chat.models import Base, CharacterExpressionAsset, AppSetting


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:yield db
    engine.dispose()


@pytest.mark.parametrize("name,expected", [
    ("Hà","ha"),("Kim Anh","kimanh"),("Trịnh Khải Nguyên","trinhkhainguyen"),
    ("Mira Sunpetal","mira"),("Lyra Moonveil","lyra"),("Aurelion Dawn","aurelion"),("Ruby","ruby"),("Nguyễn Vũ","nguyenvu"),("Merr","merr"),
])
def test_named_sheets_match_only_known_names(name,expected):
    assert module.sheet_for(SimpleNamespace(name=name,display_name=name))[0]==expected
    assert module.sheet_for(SimpleNamespace(name="Renato",display_name="Renato")) is None


def test_sets_are_shared_persisted_and_replaced_when_sheet_changes(database,tmp_path,monkeypatch):
    root=tmp_path/"react";root.mkdir()
    monkeypatch.setenv("CHARACTER_IMAGE_DIR",str(tmp_path))
    image=Image.new("RGB",(1600,1600),"white")
    # Distinct cell colors make cross-cell and caption inclusion detectable.
    colors=[(180+i*7,20+i*10,30+i*8) for i in range(9)]
    from PIL import ImageDraw
    draw=ImageDraw.Draw(image)
    _,columns,rows=module.LAYOUTS["ha"]
    for i,color in enumerate(colors):
        x1,x2=columns[i%3];y1,y2=rows[i//3]
        draw.rectangle((x1,y1,x2,y2),fill=color)
        draw.rectangle((x1,y2+3,x2,y2+25),fill="black")
    path=root/"ha.webp";image.save(path,lossless=True)
    item=SimpleNamespace(name="Hà",display_name="Hà")
    source=module.ensure_bundled_expressions(database,item)
    assets=database.query(CharacterExpressionAsset).filter_by(character_id=source).all()
    assert len(assets)==11
    for index,label in enumerate(module.CELL_NAMES):
        asset=next(row for row in assets if row.emotion==label)
        with Image.open(BytesIO(asset.content)) as crop:
            assert crop.size==(512,512)
            assert all(abs(a-b)<6 for a,b in zip(crop.getpixel((256,256)),colors[index]))
    ids={row.id for row in assets}
    assert module.ensure_bundled_expressions(database,item)==source
    assert {row.id for row in database.query(CharacterExpressionAsset).filter_by(character_id=source)}==ids
    old_version=database.get(AppSetting,"avatar_expression_version:"+source).value
    Image.new("RGB",(1600,1600),"blue").save(path,lossless=True)
    module.ensure_bundled_expressions(database,item)
    assert database.get(AppSetting,"avatar_expression_version:"+source).value!=old_version
    assert database.query(CharacterExpressionAsset).filter_by(character_id=source).count()==11


def test_new_sheets_override_existing_generated_source(database):
    from character_chat.main import expression_source_id,character_expression
    from character_chat.models import Character
    from character_chat.presets import presets
    card=presets()[1].model_copy(deep=True)
    character=Character(id="sheet-test-ha",user_id="sheet-user",name=card.name,spec=card.model_dump_json())
    database.add(character)
    database.add(CharacterExpressionAsset(id="old-sheet",character_id=character.id,emotion="happy",mime_type="image/png",content=b"old"))
    database.commit()
    assert expression_source_id(database,character)=="__bundled__:ha"
    response=character_expression(character.id,"happy",database,"sheet-user")
    assert response.media_type=="image/webp"
    with Image.open(BytesIO(response.body)) as portrait:
        assert portrait.size==(512,512)
    # The original custom asset is preserved, not deleted on an unrelated path.
    assert database.get(CharacterExpressionAsset,"old-sheet").content==b"old"


def test_all_supplied_sheets_decode():
    root=Path("image/react")
    for path in root.glob("*.webp"):
        key=module.name_key(path.stem)
        assert key in module.LAYOUTS
        info=path.stat()
        version,images=module.split_sheet(key,str(path.resolve()),info.st_mtime_ns,info.st_size)
        assert version.startswith("bundled-sheet-v2:")
        assert len(images)==11
        assert all(len(content)<300000 for content in images.values())

def test_normal_smile_and_separate_thinking_portrait(database):
    from character_chat.main import normalized_expression,reply_expression,character_expression
    from character_chat.models import Character
    from character_chat.presets import presets
    card=presets()[1].model_copy(deep=True)
    row=Character(id="thinking-ha",user_id="think-user",name=card.name,spec=card.model_dump_json())
    database.add(row);database.commit()
    neutral=character_expression(row.id,"neutral",database,"think-user")
    happy=character_expression(row.id,"happy",database,"think-user")
    thinking=character_expression(row.id,"thinking",database,"think-user")
    assert neutral.body==happy.body
    assert thinking.body!=neutral.body
    assert normalized_expression("thinking")=="thinking"
    assert reply_expression("*She pauses, thinking.* Let us take a moment.")=="thinking"
    assert reply_expression("*Cô ấy trầm ngâm suy nghĩ.* Đợi mình một chút.")=="thinking"
    assert reply_expression("What do you think I should do?")=="neutral"
    assert reply_expression("*She looks at you.* What do you think?")=="neutral"
