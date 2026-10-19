from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Integer, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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
    reply_to_message_id: Mapped[str|None]=mapped_column(String,nullable=True,index=True)
    character_id: Mapped[str|None]=mapped_column(String,nullable=True)
    text: Mapped[str]=mapped_column(Text)
    speech_segments: Mapped[str]=mapped_column(Text,default="[]")
    sources: Mapped[str]=mapped_column(Text,default="[]")
    emotion: Mapped[str]=mapped_column(String,default="neutral")
    finish_status: Mapped[str]=mapped_column(String,default="complete")
    created_at: Mapped[str]=mapped_column(String,default=now)

class MessageSpeech(Base):
    __tablename__="message_speech"
    message_id: Mapped[str]=mapped_column(ForeignKey("messages.id"),primary_key=True)
    signature: Mapped[str]=mapped_column(String)
    mime_type: Mapped[str]=mapped_column(String,default="audio/mpeg")
    content: Mapped[bytes]=mapped_column(LargeBinary)
    created_at: Mapped[str]=mapped_column(String,default=now)

class MessageSpeechRun(Base):
    __tablename__="message_speech_runs"
    message_id: Mapped[str]=mapped_column(ForeignKey("messages.id"),primary_key=True)
    signature: Mapped[str]=mapped_column(String)
    status: Mapped[str]=mapped_column(String,default="generating")
    error: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[str]=mapped_column(String,default=now)

class MessageSpeechPart(Base):
    __tablename__="message_speech_parts"
    message_id: Mapped[str]=mapped_column(ForeignKey("messages.id"),primary_key=True)
    position: Mapped[int]=mapped_column(Integer,primary_key=True)
    sample_rate: Mapped[int]=mapped_column(Integer)
    content: Mapped[bytes]=mapped_column(LargeBinary)

class VoiceEvent(Base):
    __tablename__="voice_events"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    message_id: Mapped[str]=mapped_column(String,index=True)
    character_id: Mapped[str]=mapped_column(String,index=True)
    user_id: Mapped[str]=mapped_column(String,index=True)
    event_type: Mapped[str]=mapped_column(String,index=True)
    status: Mapped[str]=mapped_column(String,index=True)
    model_id: Mapped[str]=mapped_column(String,default="")
    voice_id: Mapped[str]=mapped_column(String,default="")
    latency_ms: Mapped[int]=mapped_column(Integer,default=0)
    audio_bytes: Mapped[int]=mapped_column(Integer,default=0)
    automatic: Mapped[int]=mapped_column(Integer,default=0)
    error: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[str]=mapped_column(String,default=now,index=True)

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
    primary_model_config_id: Mapped[str]=mapped_column(String,default="")
    primary_model_name: Mapped[str]=mapped_column(String,default="")
    primary_api_base: Mapped[str]=mapped_column(String,default="")
    fallback_model: Mapped[str]=mapped_column(String,default="")
    fallback_model_2: Mapped[str]=mapped_column(String,default="")
    fallback_used: Mapped[int]=mapped_column(Integer,default=0)
    fallback_reason: Mapped[str]=mapped_column(Text,default="")
    actual_model: Mapped[str]=mapped_column(String,default="")
    actual_model_config_id: Mapped[str]=mapped_column(String,default="")
    actual_model_name: Mapped[str]=mapped_column(String,default="")
    actual_api_base: Mapped[str]=mapped_column(String,default="")
    gateway_snapshot_source: Mapped[str]=mapped_column(String,default="")
    thinking_mode: Mapped[str]=mapped_column(String,default="default")
    reasoning_effort: Mapped[str]=mapped_column(String,default="default")
    conversation_snapshot: Mapped[str]=mapped_column(Text,default="")
    archive_source: Mapped[str]=mapped_column(String,default="captured")
    output_text: Mapped[str]=mapped_column(Text,default="")
    continuation_count: Mapped[int]=mapped_column(Integer,default=0)
    finish_status: Mapped[str]=mapped_column(String,default="")
    client_suggestion_ms: Mapped[int|None]=mapped_column(Integer,nullable=True)
    client_first_chunk_ms: Mapped[int|None]=mapped_column(Integer,nullable=True)
    server_prepare_ms: Mapped[int|None]=mapped_column(Integer,nullable=True)
    gateway_headers_ms: Mapped[int|None]=mapped_column(Integer,nullable=True)
    gateway_first_chunk_ms: Mapped[int|None]=mapped_column(Integer,nullable=True)
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


class BackgroundMusicAsset(Base):
    __tablename__="background_music_assets"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    title: Mapped[str]=mapped_column(String)
    mime_type: Mapped[str]=mapped_column(String)
    content: Mapped[bytes]=mapped_column(LargeBinary)
    created_at: Mapped[str]=mapped_column(String,default=now)

class CharacterVoiceSample(Base):
    __tablename__ = "character_voice_samples"
    character_id: Mapped[str] = mapped_column(String, primary_key=True)
    target: Mapped[str] = mapped_column(String, primary_key=True)
    voice_id: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sample_language: Mapped[str] = mapped_column(String)
    ref_text: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[str] = mapped_column(String, default=now)

class CharacterReactionAsset(Base):
    __tablename__ = "character_reaction_assets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    character_id: Mapped[str] = mapped_column(String, index=True)
    target: Mapped[str] = mapped_column(String)
    emotion: Mapped[str] = mapped_column(String)
    variant: Mapped[int] = mapped_column(Integer, default=0)
    voice_version: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String, default="audio/wav")
    content: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[str] = mapped_column(String, default=now)

class CharacterReactionReference(Base):
    __tablename__ = "character_reaction_references"
    character_id: Mapped[str] = mapped_column(String, primary_key=True)
    target: Mapped[str] = mapped_column(String, primary_key=True)
    voice_id: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[str] = mapped_column(String, default=now)

class ActionSoundAsset(Base):
    __tablename__ = "action_sound_assets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    content: Mapped[bytes] = mapped_column(LargeBinary)

# Ordinary Roleplay social graph; separate from user-character Relationship.
class CharacterSocialState(Base):
    __tablename__="character_social_state"
    __table_args__=(UniqueConstraint("user_id","scope","character_a_id","character_b_id"),)
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    scope: Mapped[str]=mapped_column(String,default="roleplay",index=True)
    character_a_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    character_b_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    active: Mapped[int]=mapped_column(Integer,default=1)
    interaction_count: Mapped[int]=mapped_column(Integer,default=0)
    affinity: Mapped[float]=mapped_column(Float,default=0)
    trust: Mapped[float]=mapped_column(Float,default=0)
    respect: Mapped[float]=mapped_column(Float,default=0)
    jealousy: Mapped[float]=mapped_column(Float,default=0)
    rivalry: Mapped[float]=mapped_column(Float,default=0)
    fear: Mapped[float]=mapped_column(Float,default=0)
    romantic_interest: Mapped[float]=mapped_column(Float,default=0)
    first_met_at: Mapped[str|None]=mapped_column(String,nullable=True)
    last_interaction_at: Mapped[str|None]=mapped_column(String,nullable=True)
    created_at: Mapped[str]=mapped_column(String,default=now)
    updated_at: Mapped[str]=mapped_column(String,default=now)

class CharacterSocialKnowledge(Base):
    __tablename__="character_social_knowledge"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    scope: Mapped[str]=mapped_column(String,default="roleplay",index=True)
    character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    subject_character_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    fact_key: Mapped[str]=mapped_column(String)
    fact_value: Mapped[str]=mapped_column(Text)
    knowledge_type: Mapped[str]=mapped_column(String,default="TOLD")
    source: Mapped[str]=mapped_column(String)
    confidence: Mapped[float]=mapped_column(Float,default=1)
    visibility: Mapped[str]=mapped_column(String,default="PRIVATE")
    learned_at: Mapped[str]=mapped_column(String,default=now)

class CharacterSocialCanon(Base):
    __tablename__="character_social_canon"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    scope: Mapped[str]=mapped_column(String,default="roleplay")
    character_a_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    character_b_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    text: Mapped[str]=mapped_column(Text)
    revision: Mapped[int]=mapped_column(Integer,default=1)
    created_at: Mapped[str]=mapped_column(String,default=now)

class CharacterSharedInteraction(Base):
    __tablename__="character_shared_interaction"
    id: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),index=True)
    scope: Mapped[str]=mapped_column(String,default="roleplay",index=True)
    character_a_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    character_b_id: Mapped[str]=mapped_column(ForeignKey("characters.id"),index=True)
    conversation_id: Mapped[str]=mapped_column(String,index=True)
    source_message_id: Mapped[str]=mapped_column(String,index=True)
    interaction_type: Mapped[str]=mapped_column(String,default="GROUP_CHAT")
    summary: Mapped[str]=mapped_column(Text)
    source_ids: Mapped[str]=mapped_column(Text)
    source_fingerprint: Mapped[str]=mapped_column(String)
    deltas: Mapped[str]=mapped_column(Text,default="{}")
    created_at: Mapped[str]=mapped_column(String,default=now)
