from __future__ import annotations
from typing import Literal
from datetime import date
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

def uid() -> str:
    return str(uuid4())

class Identity(BaseModel):
    role: str = "companion"
    age_description: str | None = None
    backstory: str = ""
    current_context: str = ""

class Personality(BaseModel):
    warmth: float = Field(.6, ge=0, le=1)
    humor: float = Field(.5, ge=0, le=1)
    assertiveness: float = Field(.5, ge=0, le=1)
    curiosity: float = Field(.5, ge=0, le=1)
    empathy: float = Field(.6, ge=0, le=1)
    optimism: float = Field(.5, ge=0, le=1)
    skepticism: float = Field(.3, ge=0, le=1)
    spontaneity: float = Field(.5, ge=0, le=1)
    confidence: float = Field(.5, ge=0, le=1)
    possessiveness: float = Field(.1, ge=0, le=1)
    energy: float = Field(.6, ge=0, le=1)

class Speech(BaseModel):
    verbosity: Literal["short", "medium", "long"] = "medium"
    formality: Literal["casual", "semi_formal", "formal"] = "casual"
    emoji_usage: Literal["never", "rare", "sometimes", "often"] = "rare"
    humor_style: str = "gentle"
    vocabulary_style: str = "natural"
    preferred_language: str = "vi"
    code_switching: bool = False
    example_phrases: list[str] = Field(default_factory=list)

class SupportProfile(BaseModel):
    primary_role: Literal["study","work","health","lifestyle","companion"] = "companion"
    strengths: list[Literal["study","work","health","lifestyle","companion"]] = Field(default_factory=lambda:["companion"])
    introduction: str = "Đồng hành, lắng nghe và hỗ trợ bạn trong cuộc sống hằng ngày."
    method: str = "Listen first, then offer one small useful next step when appropriate."
    proactive_style: str = "gentle"

class CharacterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=uid)
    name: str = Field(min_length=1)
    display_name: str = ""
    description: str = ""
    avatar_url: str | None = None
    tts_voice_id: str = Field(default="", max_length=160, description="Voice identifier for browser demo or a future TTS model")
    tts_emotion_enabled: bool = True
    preset_type: str | None = None
    category: Literal["utility","entertainment"] = "utility"
    system_prompt: str = Field(default="", description="Character-specific roleplay instructions, voice, worldview, and interaction style")
    initial_greeting: str = Field(default="", description="The character's first natural message when a new room starts")
    scenario: str = Field(default="", description="Current fictional situation and relationship context")
    sample_dialogues: list[str] = Field(default_factory=list, description="Short examples that anchor the character voice")
    identity: Identity = Field(default_factory=Identity)
    personality: Personality = Field(default_factory=Personality)
    speech: Speech = Field(default_factory=Speech)
    support: SupportProfile = Field(default_factory=SupportProfile)
    motivations: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    likes: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    behavior_rules: list[str] = Field(default_factory=list)
    persona_knowledge: list[str] = Field(default_factory=list, description="Background knowledge used to understand and portray this character")
    knowledge_document_ids: list[str] = Field(default_factory=list)
    memory_policy: str = "remember meaningful details with user control"
    creation_type: Literal["preset", "custom", "mirror", "document"] = "custom"
    knowledge_cutoff_page: int | None = None
    knowledge_cutoff_chapter: int | None = None
    simulation_label: bool = False

class MessageIn(BaseModel):
    message: str = Field(min_length=1)
    speaker_mode: str = "auto"

class RoomIn(BaseModel):
    name: str = ""
    character_ids: list[str] = Field(min_length=1, max_length=6)

class GenerateIn(BaseModel):
    description: str = Field(min_length=3,max_length=72000)
    name: str = ""
    role: str = Field("companion",max_length=120)
    scenario: str = Field("",max_length=3000)
    initial_greeting: str = Field("",max_length=1000)
    dialogue_examples: list[str] = Field(default_factory=list,max_length=8)
    existing_media_character: bool = False
    media_character_name: str = Field("",max_length=160)
    media_title: str = Field("",max_length=200)

class MirrorIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    description: str = Field(min_length=3, max_length=72000)
    introduction: str = Field(default="", max_length=2000)

class FromDocumentIn(BaseModel):
    document_id: str
    candidate_name: str
    knowledge_cutoff_page: int | None = None
    knowledge_cutoff_chapter: int | None = None

class DocumentUrlIn(BaseModel):
    url: str = Field(min_length=8, max_length=2000)

class DailyTaskIn(BaseModel):
    title: str = Field(min_length=1,max_length=200)
    domain: Literal["study","work","health","lifestyle"] = "lifestyle"
    priority: int = Field(2,ge=1,le=3)
    notes: str = Field("",max_length=1000)
    due_at: str | None = None

class DailyTaskPatch(BaseModel):
    title: str | None = Field(None,min_length=1,max_length=200)
    domain: Literal["study","work","health","lifestyle"] | None = None
    status: Literal["open","done","cancelled"] | None = None
    priority: int | None = Field(None,ge=1,le=3)
    notes: str | None = Field(None,max_length=1000)
    due_at: str | None = None

class DiscoveryCandidate(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    importance: float = Field(.5, ge=0, le=1)
    confidence: float = Field(.5, ge=0, le=1)
    source_evidence: list[str] = Field(default_factory=list)
    dialogue_count: int = 0
    relationships: list[str] = Field(default_factory=list)
    important_events: list[str] = Field(default_factory=list)

class TurnAnalysis(BaseModel):
    user_emotion: str = "neutral"
    valence: float = Field(0,ge=-1,le=1)
    arousal: float = Field(.3,ge=0,le=1)
    confidence: float = Field(.5,ge=0,le=1)
    directed_at_character: bool = False
    relationship_event: Literal["none","sharing","appreciation","repair","dismissal","conflict","boundary"] = "none"
    event_valence: float = Field(0,ge=-1,le=1)
    significance: float = Field(.3,ge=0,le=1)
    reflection: str = Field("",max_length=500)
    memory_worthy: bool = False
    memory_summary: str = Field("",max_length=400)
