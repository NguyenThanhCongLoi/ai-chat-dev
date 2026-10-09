import os
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session as SASession
from .models import *  # Preserve the existing db.py model imports.

def database_url():
    value=os.getenv("DATABASE_URL")
    if value: return value
    directory=Path(os.getenv("DATA_DIR","./data")); directory.mkdir(parents=True,exist_ok=True)
    return f"sqlite:///{(directory/'character_chat.sqlite').absolute().as_posix()}"

engine=create_engine(database_url(),connect_args={"check_same_thread":False})
class AppSession(SASession):pass
Session=sessionmaker(engine,expire_on_commit=False,class_=AppSession)


def init_db():
    Base.metadata.create_all(engine)
    if "assistant_memories" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("assistant_memories")}
        with engine.begin() as connection:
            if "room_id" not in columns:connection.execute(text("ALTER TABLE assistant_memories ADD COLUMN room_id VARCHAR"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_assistant_memories_room_id ON assistant_memories (room_id)"))
    # create_all does not add columns to an existing SQLite database. Keep this
    # tiny migration here so deployed volumes retain their conversations.
    if "messages" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("messages")}
        if "speech_segments" not in columns:
            with engine.begin() as connection:connection.execute(text("ALTER TABLE messages ADD COLUMN speech_segments TEXT DEFAULT '[]'"))
        if "emotion" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE messages ADD COLUMN emotion VARCHAR DEFAULT 'neutral'"))
        if "finish_status" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE messages ADD COLUMN finish_status VARCHAR DEFAULT 'complete'"))
    if "ai_request_logs" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("ai_request_logs")}
        additions={"server_prepare_ms":"INTEGER","gateway_headers_ms":"INTEGER","gateway_first_chunk_ms":"INTEGER","conversation_snapshot":"TEXT DEFAULT ''","archive_source":"VARCHAR DEFAULT 'captured'","client_suggestion_ms":"INTEGER","client_first_chunk_ms":"INTEGER","primary_model_config_id":"VARCHAR DEFAULT ''","primary_model_name":"VARCHAR DEFAULT ''","primary_api_base":"VARCHAR DEFAULT ''","actual_model_config_id":"VARCHAR DEFAULT ''","actual_model_name":"VARCHAR DEFAULT ''","actual_api_base":"VARCHAR DEFAULT ''","gateway_snapshot_source":"VARCHAR DEFAULT ''","fallback_model_2":"VARCHAR DEFAULT ''","fallback_reason":"TEXT DEFAULT ''","actual_model":"VARCHAR DEFAULT ''","thinking_mode":"VARCHAR DEFAULT 'default'","reasoning_effort":"VARCHAR DEFAULT 'default'","output_text":"TEXT DEFAULT ''","continuation_count":"INTEGER DEFAULT 0","finish_status":"VARCHAR DEFAULT ''"}
        with engine.begin() as connection:
            for name,kind in additions.items():
                if name not in columns:connection.execute(text(f"ALTER TABLE ai_request_logs ADD COLUMN {name} {kind}"))
    if "model_configs" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("model_configs")}
        additions={"assistant_name":"VARCHAR DEFAULT ''","assistant_model_id":"VARCHAR DEFAULT ''","assistant_enabled":"INTEGER DEFAULT 1","assistant_thinking_mode":"VARCHAR DEFAULT 'default'","assistant_reasoning_effort":"VARCHAR DEFAULT 'default'"}
        with engine.begin() as connection:
            for name,kind in additions.items():
                if name not in columns:connection.execute(text(f"ALTER TABLE model_configs ADD COLUMN {name} {kind}"))
            connection.execute(text("UPDATE model_configs SET assistant_name=name WHERE assistant_name IS NULL OR assistant_name=''"))
            connection.execute(text("UPDATE model_configs SET assistant_model_id=model_id WHERE assistant_model_id IS NULL OR assistant_model_id=''"))
    if {"ai_request_logs","model_configs"}.issubset(inspect(engine).get_table_names()):
        # Snapshot names for logs that already recorded a CMS config ID. Never
        # overwrite a snapshot after an administrator renames a model.
        with engine.begin() as connection:
            for prefix in ("primary","actual"):
                connection.execute(text(f"""
                    UPDATE ai_request_logs
                    SET {prefix}_model_name = COALESCE((
                        SELECT CASE WHEN ai_request_logs.product = 'assistant'
                            THEN COALESCE(NULLIF(model_configs.assistant_name, ''), model_configs.name)
                            ELSE model_configs.name END
                        FROM model_configs WHERE model_configs.id = ai_request_logs.{prefix}_model_config_id
                    ), '')
                    WHERE COALESCE({prefix}_model_name, '') = ''
                      AND COALESCE({prefix}_model_config_id, '') != ''
                """))
                connection.execute(text(f"""
                    UPDATE ai_request_logs
                    SET {prefix}_api_base = COALESCE((
                        SELECT model_configs.api_base FROM model_configs
                        WHERE model_configs.id = ai_request_logs.{prefix}_model_config_id
                    ), '')
                    WHERE COALESCE({prefix}_api_base, '') = ''
                      AND COALESCE({prefix}_model_config_id, '') != ''
                """))
    if "ai_request_logs" in inspect(engine).get_table_names():
        with engine.begin() as connection:
            connection.execute(text("""
                UPDATE ai_request_logs SET gateway_snapshot_source = 'inferred'
                WHERE COALESCE(gateway_snapshot_source, '') = ''
                  AND (COALESCE(primary_api_base, '') != '' OR COALESCE(actual_api_base, '') != '')
            """))
    if "user_accounts" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("user_accounts")}
        additions={"status":"VARCHAR DEFAULT 'active'","is_admin":"INTEGER DEFAULT 0","suspended_until":"VARCHAR","ban_reason":"TEXT DEFAULT ''"}
        with engine.begin() as connection:
            for name,kind in additions.items():
                if name not in columns:connection.execute(text(f"ALTER TABLE user_accounts ADD COLUMN {name} {kind}"))
