import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, Text, Float, Integer, ForeignKey, LargeBinary, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session as SASession

def now(): return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__="users"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    created_at: Mapped[str]=mapped_column(String,default=now)

class UserAccount(Base):
    __tablename__="user_accounts"
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),primary_key=True)
    username: Mapped[str]=mapped_column(String,unique=True,index=True)
    display_name: Mapped[str]=mapped_column(String)
    password_hash: Mapped[str]=mapped_column(Text)
    theme: Mapped[str]=mapped_column(String,default="light")
    status: Mapped[str]=mapped_column(String,default="active")
    is_admin: Mapped[int]=mapped_column(Integer,default=0)
    suspended_until: Mapped[str|None]=mapped_column(String,nullable=True)
    ban_reason: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class UserSession(Base):
    __tablename__="user_sessions"
    token_hash: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    created_at: Mapped[str]=mapped_column(String,default=now)
    expires_at: Mapped[str]=mapped_column(String,index=True)

class UserProfile(Base):
    __tablename__="user_profiles"
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),primary_key=True)
    bio: Mapped[str]=mapped_column(Text,default="")
    language: Mapped[str]=mapped_column(String,default="vi")
    reduced_motion: Mapped[int]=mapped_column(Integer,default=0)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class UserAvatar(Base):
    __tablename__="user_avatars"
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),primary_key=True)
    mime_type: Mapped[str]=mapped_column(String)
    content: Mapped[bytes]=mapped_column(LargeBinary)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class Character(Base):
    __tablename__="characters"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    name: Mapped[str]=mapped_column(String)
    spec: Mapped[str]=mapped_column(Text)
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class CharacterVersion(Base):
    __tablename__="character_versions"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    spec: Mapped[str]=mapped_column(Text)
    created_at: Mapped[str]=mapped_column(String,default=now)

class CharacterPublication(Base):
    __tablename__="character_publications"
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),primary_key=True)
    creator_user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    is_public: Mapped[int]=mapped_column(Integer,default=0,index=True)
    character_type: Mapped[str]=mapped_column(String,default="companion",index=True)
    tags: Mapped[str]=mapped_column(Text,default="[]")
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class CharacterAsset(Base):
    __tablename__="character_assets"
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),primary_key=True)
    mime_type: Mapped[str]=mapped_column(String)
    content: Mapped[bytes]=mapped_column(LargeBinary)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class CharacterExpressionAsset(Base):
    __tablename__="character_expression_assets"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    character_id: Mapped[str]=mapped_column(String,index=True)
    emotion: Mapped[str]=mapped_column(String,index=True)
    mime_type: Mapped[str]=mapped_column(String,default="image/png")
    content: Mapped[bytes]=mapped_column(LargeBinary)
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class CharacterRating(Base):
    __tablename__="character_ratings"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    rating: Mapped[int]=mapped_column(Integer)
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class CharacterUsage(Base):
    __tablename__="character_usage"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    created_at: Mapped[str]=mapped_column(String,default=now)

class CharacterReaction(Base):
    __tablename__="character_reactions"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    reaction: Mapped[str]=mapped_column(String)
    created_at: Mapped[str]=mapped_column(String,default=now)

class CreatorFollow(Base):
    __tablename__="creator_follows"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    follower_user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    creator_user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    created_at: Mapped[str]=mapped_column(String,default=now)

class Document(Base):
    __tablename__="documents"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    filename: Mapped[str]=mapped_column(String)
    status: Mapped[str]=mapped_column(String,default="pending")
    error: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[str]=mapped_column(String,default=now)

class DocumentChunk(Base):
    __tablename__="document_chunks"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    document_id: Mapped[str]=mapped_column(ForeignKey("documents.id"),index=True)
    text: Mapped[str]=mapped_column(Text)
    meta: Mapped[str]=mapped_column(Text,default="{}")
    embedding: Mapped[str]=mapped_column(Text,default="[]")

class AssistantFile(Base):
    __tablename__="assistant_files"
    document_id: Mapped[str]=mapped_column(ForeignKey("documents.id"),primary_key=True)
    mime_type: Mapped[str]=mapped_column(String)
    content: Mapped[bytes]=mapped_column(LargeBinary)
    created_at: Mapped[str]=mapped_column(String,default=now)

class CharacterKnowledge(Base):
    __tablename__="character_knowledge"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    document_id: Mapped[str]=mapped_column(ForeignKey("documents.id"),index=True)
    cutoff_page: Mapped[int|None]=mapped_column(Integer,nullable=True)
    cutoff_chapter: Mapped[int|None]=mapped_column(Integer,nullable=True)

class Room(Base):
    __tablename__="rooms"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    name: Mapped[str]=mapped_column(String)
    created_at: Mapped[str]=mapped_column(String,default=now)

class RoomStoryState(Base):
    __tablename__="room_story_states"
    room_id: Mapped[str]=mapped_column(ForeignKey("rooms.id"),primary_key=True)
    events: Mapped[str]=mapped_column(Text,default="[]")
    updated_at: Mapped[str]=mapped_column(String,default=now)

class RoomMember(Base):
    __tablename__="room_members"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    room_id: Mapped[str]=mapped_column(ForeignKey("rooms.id"),index=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)

class RoomDocument(Base):
    __tablename__="room_documents"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    room_id: Mapped[str]=mapped_column(ForeignKey("rooms.id"),index=True)
    document_id: Mapped[str]=mapped_column(ForeignKey("documents.id"),index=True)

class Message(Base):
    __tablename__="messages"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    room_id: Mapped[str]=mapped_column(ForeignKey("rooms.id"),index=True)
    sender_type: Mapped[str]=mapped_column(String)
    character_id: Mapped[str|None]=mapped_column(String,nullable=True)
    text: Mapped[str]=mapped_column(Text)
    sources: Mapped[str]=mapped_column(Text,default="[]")
    emotion: Mapped[str]=mapped_column(String,default="neutral")
    finish_status: Mapped[str]=mapped_column(String,default="complete")
    created_at: Mapped[str]=mapped_column(String,default=now)

class MessageAlternative(Base):
    __tablename__="message_alternatives"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    message_id: Mapped[str]=mapped_column(ForeignKey("messages.id"),index=True)
    text: Mapped[str]=mapped_column(Text)
    created_at: Mapped[str]=mapped_column(String,default=now)

class MessageSuggestion(Base):
    __tablename__="message_suggestions"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    message_id: Mapped[str]=mapped_column(ForeignKey("messages.id"),index=True)
    text: Mapped[str]=mapped_column(String)
    position: Mapped[int]=mapped_column(Integer,default=0)

class Memory(Base):
    __tablename__="memories"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    character_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    room_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    type: Mapped[str]=mapped_column(String,default="fact")
    content: Mapped[str]=mapped_column(Text)
    importance: Mapped[float]=mapped_column(Float,default=.5)
    confidence: Mapped[float]=mapped_column(Float,default=.7)
    visibility: Mapped[str]=mapped_column(String)
    pinned: Mapped[int]=mapped_column(Integer,default=0)
    embedding: Mapped[str]=mapped_column(Text,default="[]")
    source_message_id: Mapped[str|None]=mapped_column(String,nullable=True)
    created_at: Mapped[str]=mapped_column(String,default=now)
    last_accessed_at: Mapped[str]=mapped_column(String,default=now)

class Relationship(Base):
    __tablename__="relationships"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    other_character_id: Mapped[str|None]=mapped_column(String,nullable=True)
    familiarity: Mapped[float]=mapped_column(Float,default=0)
    trust: Mapped[float]=mapped_column(Float,default=0)
    affinity: Mapped[float]=mapped_column(Float,default=0)
    tension: Mapped[float]=mapped_column(Float,default=0)
    respect: Mapped[float]=mapped_column(Float,default=0)

class CharacterState(Base):
    __tablename__="character_states"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    emotion: Mapped[str]=mapped_column(String,default="neutral")
    energy: Mapped[float]=mapped_column(Float,default=.6)
    mood: Mapped[float]=mapped_column(Float,default=.5)
    intensity: Mapped[float]=mapped_column(Float,default=.2)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class RelationshipEvent(Base):
    __tablename__="relationship_events"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    room_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    source_message_id: Mapped[str|None]=mapped_column(String,nullable=True)
    event_type: Mapped[str]=mapped_column(String,default="interaction")
    valence: Mapped[float]=mapped_column(Float,default=0)
    confidence: Mapped[float]=mapped_column(Float,default=.5)
    deltas: Mapped[str]=mapped_column(Text,default="{}")
    created_at: Mapped[str]=mapped_column(String,default=now)

class MoodObservation(Base):
    __tablename__="mood_observations"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    room_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    source_message_id: Mapped[str|None]=mapped_column(String,nullable=True)
    emotion: Mapped[str]=mapped_column(String,default="neutral")
    valence: Mapped[float]=mapped_column(Float,default=0)
    arousal: Mapped[float]=mapped_column(Float,default=.3)
    confidence: Mapped[float]=mapped_column(Float,default=.5)
    directed_at_character: Mapped[int]=mapped_column(Integer,default=0)
    created_at: Mapped[str]=mapped_column(String,default=now)

class CharacterReflection(Base):
    __tablename__="character_reflections"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    room_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    content: Mapped[str]=mapped_column(Text)
    importance: Mapped[float]=mapped_column(Float,default=.5)
    confidence: Mapped[float]=mapped_column(Float,default=.5)
    created_at: Mapped[str]=mapped_column(String,default=now)

class PromptTrace(Base):
    __tablename__="prompt_traces"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    room_id: Mapped[str]=mapped_column(String,index=True)
    query: Mapped[str]=mapped_column(Text)
    layers: Mapped[str]=mapped_column(Text,default="[]")
    memory_ids: Mapped[str]=mapped_column(Text,default="[]")
    document_ids: Mapped[str]=mapped_column(Text,default="[]")
    state: Mapped[str]=mapped_column(Text,default="{}")
    created_at: Mapped[str]=mapped_column(String,default=now)

class AIRequestLog(Base):
    __tablename__="ai_request_logs"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    room_id: Mapped[str]=mapped_column(ForeignKey("rooms.id"),index=True)
    user_message_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    response_message_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    product: Mapped[str]=mapped_column(String,index=True)
    task: Mapped[str]=mapped_column(String,default="response")
    primary_model: Mapped[str]=mapped_column(String,default="")
    fallback_model: Mapped[str]=mapped_column(String,default="")
    fallback_model_2: Mapped[str]=mapped_column(String,default="")
    fallback_used: Mapped[int]=mapped_column(Integer,default=0)
    fallback_reason: Mapped[str]=mapped_column(Text,default="")
    actual_model: Mapped[str]=mapped_column(String,default="")
    thinking_mode: Mapped[str]=mapped_column(String,default="default")
    reasoning_effort: Mapped[str]=mapped_column(String,default="default")
    output_text: Mapped[str]=mapped_column(Text,default="")
    continuation_count: Mapped[int]=mapped_column(Integer,default=0)
    finish_status: Mapped[str]=mapped_column(String,default="")
    latency_ms: Mapped[int]=mapped_column(Integer,default=0)
    error: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[str]=mapped_column(String,default=now)

class AuditEvent(Base):
    """Operational user activity. Never stores passwords, tokens, or request bodies."""
    __tablename__="audit_events"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    username: Mapped[str]=mapped_column(String,default="",index=True)
    session_hash: Mapped[str]=mapped_column(String,default="",index=True)
    category: Mapped[str]=mapped_column(String,index=True)
    action: Mapped[str]=mapped_column(String,index=True)
    method: Mapped[str]=mapped_column(String,default="")
    path: Mapped[str]=mapped_column(String,index=True)
    status: Mapped[str]=mapped_column(String,index=True)
    status_code: Mapped[int]=mapped_column(Integer,default=200,index=True)
    latency_ms: Mapped[int]=mapped_column(Integer,default=0)
    ip_address: Mapped[str]=mapped_column(String,default="")
    user_agent: Mapped[str]=mapped_column(Text,default="")
    error: Mapped[str]=mapped_column(Text,default="")
    details: Mapped[str]=mapped_column(Text,default="{}")
    created_at: Mapped[str]=mapped_column(String,default=now,index=True)

class DailyTask(Base):
    __tablename__="daily_tasks"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    title: Mapped[str]=mapped_column(String)
    domain: Mapped[str]=mapped_column(String,default="lifestyle")
    status: Mapped[str]=mapped_column(String,default="open")
    priority: Mapped[int]=mapped_column(Integer,default=2)
    notes: Mapped[str]=mapped_column(Text,default="")
    due_at: Mapped[str|None]=mapped_column(String,nullable=True)
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class AssistantMemorySetting(Base):
    __tablename__="assistant_memory_settings"
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),primary_key=True)
    enabled: Mapped[int]=mapped_column(Integer,default=0)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class AssistantMemory(Base):
    __tablename__="assistant_memories"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    mode: Mapped[str]=mapped_column(String,default="assistant_general",index=True)
    room_id: Mapped[str|None]=mapped_column(String,index=True,nullable=True)
    content: Mapped[str]=mapped_column(Text)
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class AssistantReminder(Base):
    __tablename__="assistant_reminders"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    title: Mapped[str]=mapped_column(String)
    due_at: Mapped[str]=mapped_column(String,index=True)
    status: Mapped[str]=mapped_column(String,default="active",index=True)
    last_notified_at: Mapped[str|None]=mapped_column(String,nullable=True)
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class StyleExample(Base):
    __tablename__="style_examples"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    text: Mapped[str]=mapped_column(Text)
    embedding: Mapped[str]=mapped_column(Text,default="[]")

class AppSetting(Base):
    __tablename__="app_settings"
    key: Mapped[str]=mapped_column(String,primary_key=True)
    value: Mapped[str]=mapped_column(Text,default="")
    updated_at: Mapped[str]=mapped_column(String,default=now)

class ModelConfig(Base):
    __tablename__="model_configs"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    name: Mapped[str]=mapped_column(String)
    provider: Mapped[str]=mapped_column(String)
    model_id: Mapped[str]=mapped_column(String,index=True)
    api_base: Mapped[str]=mapped_column(String)
    api_key_encrypted: Mapped[str]=mapped_column(Text,default="")
    api_key_hint: Mapped[str]=mapped_column(String,default="")
    logo: Mapped[str]=mapped_column(String,default="AI")
    enabled: Mapped[int]=mapped_column(Integer,default=1)
    assistant_name: Mapped[str]=mapped_column(String,default="")
    assistant_model_id: Mapped[str]=mapped_column(String,default="")
    assistant_enabled: Mapped[int]=mapped_column(Integer,default=1)
    assistant_thinking_mode: Mapped[str]=mapped_column(String,default="default")
    assistant_reasoning_effort: Mapped[str]=mapped_column(String,default="default")
    role: Mapped[str]=mapped_column(String,default="available")
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class ProcessingJob(Base):
    __tablename__="processing_jobs"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(String,index=True)
    job_type: Mapped[str]=mapped_column(String)
    status: Mapped[str]=mapped_column(String,default="pending")
    resource_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    content_preview: Mapped[str]=mapped_column(Text,default="")
    error: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

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
        if "emotion" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE messages ADD COLUMN emotion VARCHAR DEFAULT 'neutral'"))
        if "finish_status" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE messages ADD COLUMN finish_status VARCHAR DEFAULT 'complete'"))
    if "ai_request_logs" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("ai_request_logs")}
        additions={"fallback_model_2":"VARCHAR DEFAULT ''","fallback_reason":"TEXT DEFAULT ''","actual_model":"VARCHAR DEFAULT ''","thinking_mode":"VARCHAR DEFAULT 'default'","reasoning_effort":"VARCHAR DEFAULT 'default'","output_text":"TEXT DEFAULT ''","continuation_count":"INTEGER DEFAULT 0","finish_status":"VARCHAR DEFAULT ''"}
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
    if "user_accounts" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("user_accounts")}
        additions={"status":"VARCHAR DEFAULT 'active'","is_admin":"INTEGER DEFAULT 0","suspended_until":"VARCHAR","ban_reason":"TEXT DEFAULT ''"}
        with engine.begin() as connection:
            for name,kind in additions.items():
                if name not in columns:connection.execute(text(f"ALTER TABLE user_accounts ADD COLUMN {name} {kind}"))
