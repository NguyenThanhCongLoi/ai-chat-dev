"""Application composition root and backwards-compatible runtime facade.

Implementations live in api/ and services/. Binding order preserves dependency
identities, route ordering and names consumed by workers/tests. New business
logic belongs in the domain modules, not this composition root.
"""

# Domain modules define implementations; registration happens explicitly below.
from .api import admin_accounts as admin_accounts_api
from .api import admin_characters as admin_characters_api
from .api import admin_models as admin_models_api
from .api import admin_overview as admin_overview_api
from .api import admin_settings as admin_settings_api
from .api import assistant_chat as assistant_chat_api
from .api import assistant_memory as assistant_memory_api
from .api import assistant_rooms as assistant_rooms_api
from .api import authentication as authentication_api
from .api import characters as characters_api
from .api import community as community_api
from .api import documentation as documentation_api
from .api import documents as documents_api
from .api import frontend as frontend_api
from .api import localization as localization_api
from .api import roleplay_chat as roleplay_chat_api
from .api import rooms as rooms_api
from .api import tasks as tasks_api
from .api import voice_admin as voice_admin_api
from .api import voice_playback as voice_playback_api
from .api import voice_preferences as voice_preferences_api
from .services import assistant_history as assistant_history_service
from .services import assistant_inference as assistant_inference_service
from .services import audit as audit_service
from .services import authentication as authentication_service
from .services import characters as characters_service
from .services import chat_logs as chat_logs_service
from .services import deletion as deletion_service
from .services import documents as documents_service
from .services import expressions as expressions_service
from .services import gateway_resilience as gateway_resilience_service
from .services import lifecycle as lifecycle_service
from .services import model_registry as model_registry_service
from .services import roleplay_context as roleplay_context_service
from .services import roleplay_inference as roleplay_inference_service
from .services import rooms as rooms_service
from .services import speech as speech_service

from .group_topic import room_topic
from .translation_validation import valid_translation
from .group_routing import plan_room
from .log_archive import (
    capture_log_conversation,
    archive_chat_before_delete,
    character_avatar_metadata_url,
)
from .chat_transport import chat_stream, direct_completion, close_chat_transport
from .gateway import _within_deadline
from .suggestion_stream import (
    merge_suggestion_stream,
    capture_suggestion,
    suggestion_budget,
    post_stream_suggestion_wait,
)
import sys
from .speech_language import (
    roleplay_output_prompt,
    LANGUAGE_INSTRUCTION,
    LanguageStream,
    configured_voice,
    detect_speech_language,
    sentence_segments,
    speech_info,
    spoken_text,
    parse_language_reply,
)
from .incremental_voice import SentenceSpeech, replay_parts
import json, os, re, time, ipaddress, socket, httpx, secrets, concurrent.futures, base64, hashlib, unicodedata, asyncio, logging, io, wave
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Header,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Request,
    status,
)
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    StreamingResponse,
    FileResponse,
    Response,
    HTMLResponse,
    RedirectResponse,
)
from sqlalchemy.orm import Session as DBSession
from .db import (
    AIRequestLog,
    ActionSoundAsset,
    AppSession,
    AppSetting,
    AssistantFile,
    AssistantMemory,
    AssistantMemorySetting,
    AssistantReminder,
    AuditEvent,
    BackgroundMusicAsset,
    Base,
    Character,
    CharacterAsset,
    CharacterExpressionAsset,
    CharacterKnowledge,
    CharacterPublication,
    CharacterRating,
    CharacterReaction,
    CharacterReactionAsset,
    CharacterReactionReference,
    CharacterReflection,
    CharacterState,
    CharacterUsage,
    CharacterVersion,
    CharacterVoiceSample,
    CreatorFollow,
    DailyTask,
    DeclarativeBase,
    Document,
    DocumentChunk,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    Mapped,
    Memory,
    Message,
    MessageAlternative,
    MessageSpeech,
    MessageSpeechPart,
    MessageSpeechRun,
    MessageSuggestion,
    ModelConfig,
    MoodObservation,
    Path,
    ProcessingJob,
    PromptTrace,
    Relationship,
    RelationshipEvent,
    Room,
    RoomDocument,
    RoomMember,
    RoomStoryState,
    SASession,
    Session,
    String,
    StyleExample,
    Text,
    User,
    UserAccount,
    UserAvatar,
    UserProfile,
    UserSession,
    VoiceEvent,
    create_engine,
    database_url,
    datetime,
    engine,
    init_db,
    inspect,
    mapped_column,
    now,
    os,
    sessionmaker,
    text,
    timezone,
)
from .schemas import (
    BaseModel,
    CharacterSpec,
    CharacterVoiceLanguage,
    ConfigDict,
    DailyTaskIn,
    DailyTaskPatch,
    DiscoveryCandidate,
    DocumentUrlIn,
    Field,
    FromDocumentIn,
    GenerateIn,
    Identity,
    Literal,
    MessageIn,
    MirrorIn,
    Personality,
    RoomIn,
    Speech,
    SupportProfile,
    TurnAnalysis,
    annotations,
    date,
    uid,
    uuid4,
)
from .presets import presets, GROUP_PRESETS
from .retrieval import store_memory
from .documents import parse_document, save_chunks, discover_fallback
from .engine import (
    llm,
    compile_character,
    route,
    relationship,
    update_relationship,
    assemble,
    suggestion_prompt,
    parse_suggestions,
    fallback_suggestions,
    finalize_suggestions,
    format_roleplay_reply,
)
from .moderation import ensure_safe_content
from .character_policy import enforce_character_policy
from .background import analyze_turn
from .character_research import research_media_character
from .bundled_expressions import ensure_bundled_expressions
from .avatar_pipeline import (
    build_expression_variants,
    default_expression_variants,
    optimize_card_avatar,
    EXPRESSION_VERSION,
    EMOTIONS,
)
from . import engine as character_engine
from .prompts import MODERATION_SYSTEM_PROMPT, EMOTION_DETECTION_SYSTEM_PROMPT
from .assistant_prompts import ASSISTANT_PROMPTS, ASSISTANT_SUGGESTION_PROMPT
from .assistant_pipeline import retrieve_room_context, task_guardrail
from .voice import (
    vbee_voice_url,
    speech_api_base,
    normalize_voices,
    character_voice_gender,
    select_voice,
    voice_connect_timeout,
)
from cryptography.fernet import Fernet, InvalidToken

# Shared runtime preserves dependency overrides and the existing worker facade.
_runtime = sys.modules[__name__]

SETTING_DEFAULTS = {
    "assistant_system_instruction": "",
    "llm_model": os.getenv("LLM_MODEL", "openai/gpt-4.1-mini"),
    "fallback_model": os.getenv("LLM_FALLBACK_MODEL", ""),
    "moderation_model": os.getenv("MODERATION_MODEL", ""),
    "llm_api_base": os.getenv("LLM_API_BASE", "https://gateway.avibi.ai/v1"),
    "response_instruction": "",
    "suggestion_instruction": "",
    "compiler_instruction": "",
    "default_temperature": "0.75",
    "short_temperature": "0.65",
    "default_max_tokens": "350",
    "short_max_tokens": "180",
}
MODEL_CIRCUIT = {}
MODEL_CIRCUIT_LOCK = __import__("threading").Lock()


gateway_resilience_service.bind_model_circuit_remaining(_runtime)


assistant_history_service.bind_bounded_assistant_history(_runtime)
SUPPORTED_LANGUAGES = {
    "vi": "Vietnamese",
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "pt": "Portuguese",
    "ru": "Russian",
    "th": "Thai",
    "id": "Indonesian",
    "my": "Burmese (Myanmar)",
    "km": "Khmer (Cambodia)",
}


model_registry_service.bind_runtime_settings(_runtime)


lifecycle_service.bind_lifespan(_runtime)

app = FastAPI(
    title="Character Chat API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
docs_security = HTTPBasic()


documentation_api.bind_docs_auth(_runtime)

DOC_SECTIONS = {
    "assistant": {
        "title": "Avibi AI Assistant API",
        "tags": {"AI Assistant", "Identity & localization", "System"},
    },
    "role-play": {
        "title": "Avibi AI Role Play API",
        "tags": {
            "Role Play",
            "Characters",
            "Documents & knowledge",
            "Memory & state",
            "Identity & localization",
            "System",
        },
    },
    "admin": {
        "title": "Avibi CMS API",
        "tags": {
            "CMS — access",
            "CMS — content",
            "CMS — AI configuration",
            "CMS — observability",
            "System",
        },
    },
    "all": {"title": "Avibi Platform — All APIs", "tags": None},
}


documentation_api.bind_section_docs(_runtime)


audit_service.bind__audit_category(_runtime)


authentication_service.bind_db_session(_runtime)


authentication_api.bind_register_account(_runtime)


localization_api.bind_translate_interface_content(_runtime)


authentication_api.bind_update_account(_runtime)

ASSISTANT_ROOM_PREFIX = "assistant:"
ASSISTANT_ROOM_TITLES = {
    "assistant_general": "AI Assistant",
    "assistant_psychology": "Tư vấn tâm lý",
    "assistant_health": "Tư vấn sức khỏe",
    "assistant_homework": "Hỗ trợ bài tập",
    "assistant_tarot": "Tarot và chiêm nghiệm",
    "assistant_tuvi": "Tử vi và Bát Tự",
}


assistant_memory_api.bind_assistant_room(_runtime)

ASSISTANT_MEMORY_MODES = set(ASSISTANT_PROMPTS)


assistant_memory_api.bind_assistant_memory_enabled(_runtime)


assistant_rooms_api.bind_assistant_profiles_config(_runtime)


assistant_inference_service.bind_run_assistant_model_chain(_runtime)


assistant_chat_api.bind_send_assistant_message(_runtime)


characters_service.bind_owned(_runtime)


characters_api.bind_health(_runtime)


expressions_service.bind_generate_character_expressions(_runtime)


characters_api.bind_mirror_character(_runtime)

EXPRESSION_ALIASES = {
    "joy": "happy",
    "excited": "happy",
    "warm": "happy",
    "playful": "happy",
    "softening": "happy",
    "melancholy": "sad",
    "hurt": "sad",
    "sulking": "sad",
    "concerned": "sad",
    "upset": "angry",
    "annoyed": "angry",
    "slightly_annoyed": "angry",
    "tense": "angry",
    "shock": "surprised",
    "curious": "surprised",
    "embarrassed": "shy",
    "affectionate": "shy",
    "gentle": "shy",
    "apologetic": "shy",
}


expressions_service.bind_normalized_expression(_runtime)


community_api.bind_character_expression(_runtime)


deletion_service.bind_purge_message_dependents(_runtime)


characters_api.bind_delete_character(_runtime)


deletion_service.bind_purge_character_record(_runtime)


rooms_service.bind_preferred_language(_runtime)


rooms_api.bind_public_rooms(_runtime)


roleplay_context_service.bind_extract_memory(_runtime)


chat_logs_service.bind_save_ai_request_log(_runtime)


roleplay_inference_service.bind_stream_roleplay_answer(_runtime)


roleplay_chat_api.bind_send_message(_runtime)


documents_service.bind_process_document(_runtime)


documents_api.bind_upload_document(_runtime)


tasks_api.bind_memory_out(_runtime)


roleplay_chat_api.bind_regenerate_message(_runtime)

_vbee_voice_cache = {}


speech_service.bind__stream_with_connect_retry(_runtime)


voice_admin_api.bind_admin_voice_sample(_runtime)


speech_service.bind_message_speech_segments(_runtime)


voice_preferences_api.bind_voice_preferences(_runtime)


speech_service.bind_multilingual_speech_events(_runtime)


voice_playback_api.bind_roleplay_message_speech_stream(_runtime)


speech_service.bind__roleplay_speech_stream(_runtime)


voice_playback_api.bind_roleplay_message_speech(_runtime)

from .background_music import build_background_music_router

app.include_router(build_background_music_router(current_user, db_session, docs_auth))

from .action_sounds import build_action_sound_router

app.include_router(build_action_sound_router(current_user, db_session, docs_auth))
from .reaction_sounds import build_reaction_router, reaction_voice_for

_reaction_router, queue_reaction_generation = build_reaction_router(
    current_user,
    db_session,
    docs_auth,
    Session,
    cms_voice_sample_spec,
    effective_presets,
)
app.include_router(_reaction_router)


from .api.character_social import bind as bind_character_social
bind_character_social(_runtime)

from .memory_routes import build_memory_router

_memory_router, (
    save_manual_roleplay_memory,
    add_character_memory,
    room_memories,
    add_room_memory,
    patch_memory,
    delete_memory,
    get_relationship,
    prompt_traces,
) = build_memory_router(
    db_session,
    current_user,
    owned,
    memory_out,
    relationship,
    ensure_safe_content,
    uid,
)
app.include_router(_memory_router)


admin_overview_api.bind_admin_overview(_runtime)


admin_accounts_api.bind_admin_account_out(_runtime)


admin_settings_api.bind_get_admin_settings(_runtime)


admin_characters_api.bind_admin_characters(_runtime)


admin_models_api.bind_admin_models(_runtime)

ADMIN_TABLES = {
    "users": User,
    "user_accounts": UserAccount,
    "user_sessions": UserSession,
    "user_profiles": UserProfile,
    "user_avatars": UserAvatar,
    "characters": Character,
    "character_versions": CharacterVersion,
    "character_publications": CharacterPublication,
    "character_assets": CharacterAsset,
    "character_ratings": CharacterRating,
    "character_reactions": CharacterReaction,
    "character_usage": CharacterUsage,
    "creator_follows": CreatorFollow,
    "rooms": Room,
    "room_members": RoomMember,
    "messages": Message,
    "message_alternatives": MessageAlternative,
    "message_suggestions": MessageSuggestion,
    "documents": Document,
    "document_chunks": DocumentChunk,
    "room_documents": RoomDocument,
    "character_knowledge": CharacterKnowledge,
    "memories": Memory,
    "relationships": Relationship,
    "character_states": CharacterState,
    "relationship_events": RelationshipEvent,
    "mood_observations": MoodObservation,
    "character_reflections": CharacterReflection,
    "prompt_traces": PromptTrace,
    "daily_tasks": DailyTask,
    "style_examples": StyleExample,
    "processing_jobs": ProcessingJob,
    "app_settings": AppSetting,
    "model_configs": ModelConfig,
    "character_expression_assets": CharacterExpressionAsset,
    "ai_request_logs": AIRequestLog,
    "audit_events": AuditEvent,
    "voice_events": VoiceEvent,
}

from .admin_observability import build_admin_observability_router

_admin_router, (
    admin_database_tables,
    admin_conversations,
    admin_action_logs,
    admin_voice_logs,
    admin_chat_logs,
    admin_conversation,
    admin_database_rows,
) = build_admin_observability_router(
    docs_auth,
    db_session,
    ADMIN_TABLES,
    ASSISTANT_ROOM_PREFIX,
    suggestion_values,
    spec,
)
app.include_router(_admin_router)


from .api.roleplay_continuity import bind_roleplay_continuity
bind_roleplay_continuity(_runtime)

from .publication_review import bind_publication_review
bind_publication_review(_runtime)

from .api.roleplay_lorebook import bind_roleplay_lorebook
bind_roleplay_lorebook(_runtime)

from .api.worlds import bind_worlds
bind_worlds(_runtime)

frontend_api.bind_admin_app(_runtime)

# Keep the public URLs stable while presenting the OpenAPI surface as distinct
# product domains. This is the first step toward moving each group into its own
# APIRouter module without forcing a coordinated frontend migration.
API_TAGS = [
    {"name": "System", "description": "Health checks and deployment metadata."},
    {
        "name": "Identity & localization",
        "description": "Accounts, sessions, profiles, avatars and interface localization.",
    },
    {
        "name": "AI Assistant",
        "description": "Assistant model catalog, chats, files, streaming answers and suggestions.",
    },
    {
        "name": "Role Play",
        "description": "Role Play rooms, messages, streaming and regeneration.",
    },
    {
        "name": "Characters",
        "description": "Private characters, public catalog, social actions and expression assets.",
    },
    {
        "name": "Documents & knowledge",
        "description": "Uploads, parsing, room knowledge and document-derived characters.",
    },
    {
        "name": "Memory & state",
        "description": "Memories, relationships, character state and daily tasks.",
    },
    {
        "name": "CMS — access",
        "description": "Maintenance mode and account administration.",
    },
    {
        "name": "CMS — content",
        "description": "System characters, home sections and expression management.",
    },
    {
        "name": "CMS — AI configuration",
        "description": "Models, credentials, prompts and task assignment.",
    },
    {
        "name": "CMS — observability",
        "description": "Overview, database explorer, conversations and chat logs.",
    },
]
app.openapi_tags = API_TAGS


documentation_api.bind_api_tag(_runtime)

for api_route in app.routes:
    if getattr(api_route, "include_in_schema", False):
        api_route.tags = [api_tag(api_route.path)]

from fastapi.staticfiles import StaticFiles

if os.path.isdir(os.getenv("CHARACTER_IMAGE_DIR", "image")):
    app.mount(
        "/character-images",
        StaticFiles(directory=os.getenv("CHARACTER_IMAGE_DIR", "image")),
        name="character-images",
    )
if os.path.isdir(os.getenv("FRONTEND_DIST", "frontend/dist")):
    app.mount(
        "/",
        StaticFiles(directory=os.getenv("FRONTEND_DIST", "frontend/dist"), html=True),
        name="frontend",
    )
