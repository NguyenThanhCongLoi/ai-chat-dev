from sqlalchemy import create_engine,event
from sqlalchemy.orm import Session
from character_chat.models import Base,AppSetting
from character_chat.main import runtime_settings,SETTING_DEFAULTS

def test_runtime_settings_queries_only_setting_keys():
    engine=create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([AppSetting(key="default_temperature",value="0.42"),AppSetting(key="preset_asset:huge",value="x"*1000000),AppSetting(key="translation:en:sample",value="unrelated")])
        db.commit()
        queries=[]
        def capture(conn,cursor,statement,parameters,context,executemany):
            if "SELECT" in statement:queries.append((statement,parameters))
        event.listen(engine,"before_cursor_execute",capture)
        values=runtime_settings(db)
        assert values["default_temperature"]=="0.42"
        assert values["default_max_tokens"]==SETTING_DEFAULTS["default_max_tokens"]
        assert "preset_asset:huge" not in values
        assert len(queries)==1 and "WHERE" in queries[0][0] and " IN " in queries[0][0]
        assert set(queries[0][1])==set(SETTING_DEFAULTS)
        event.remove(engine,"before_cursor_execute",capture)
    engine.dispose()
