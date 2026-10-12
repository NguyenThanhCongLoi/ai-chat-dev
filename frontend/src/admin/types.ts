export type Overview = {
  stats: Record<string, number>;
  characters: {
    id: string;
    name: string;
    role: string;
    type: string;
    category: string;
    updated_at: string;
    usage_count?: number;
    avatar_url?: string | null;
  }[];
  rooms: {
    id: string;
    name: string;
    members: number;
    messages: number;
    updated_at: string;
  }[];
  documents: { id: string; filename: string; status: string; error?: string }[];
  ai_activity: {
    id: string;
    layers: number;
    memories: number;
    documents: number;
    created_at: string;
    character_id?: string;
    room?: string;
  }[];
};
export type Settings = {
  assistant_system_instruction: string;
  llm_model: string;
  fallback_model: string;
  moderation_model: string;
  llm_api_base: string;
  response_instruction: string;
  suggestion_instruction: string;
  compiler_instruction: string;
  default_temperature: string;
  short_temperature: string;
  default_max_tokens: string;
  short_max_tokens: string;
  _base_prompts: { response: string; suggestion: string; compiler: string };
};
export type CredentialState = {
  avibi: {
    configured: boolean;
    source: "cms" | "modal_secret" | "missing";
    hint: string;
  };
  bases?: { id: string; api_base: string; hint: string }[];
};
export type AccessAccount = {
  user_id: string;
  username: string;
  display_name: string;
  status: "active" | "suspended" | "banned";
  is_admin: boolean;
  suspended_until: string | null;
  ban_reason: string;
  created_at: string;
  updated_at: string;
};
export type AccessControl = {
  maintenance_mode: boolean;
  registration_enabled: boolean;
  accounts: AccessAccount[];
};
export type DbRows = {
  table: string;
  total: number;
  limit: number;
  offset: number;
  columns: string[];
  rows: Record<string, unknown>[];
};
export type AdminCharacter = {
  id: string;
  user_id: string | null;
  source: "preset" | "user";
  home_section?: "auto" | "featured" | "popular" | "top_rated" | "hidden";
  spec: {
    preset_type?: string;
    avatar_url?: string | null;
    creation_type: string;
    name: string;
    description: string;
    system_prompt: string;
    scenario: string;
    initial_greeting: string;
    tts_voice_id?: string;
    tts_voice_mode?: "shared" | "separate";
    tts_voice_source?: "auto" | "clone" | "catalog";
    tts_voice_source_vi?: "auto" | "clone" | "catalog";
    tts_voice_source_en?: "auto" | "clone" | "catalog";
    tts_languages?: Record<string, { enabled: boolean; voice_id: string }>;
    tts_voice_vi?: string;
    tts_voice_en?: string;
    tts_volume?: number;
    tts_gender?: "male" | "female" | "unspecified";
    tts_emotion_enabled?: boolean;
    identity: { role: string };
    goals: string[];
    behavior_rules: string[];
  };
};
export type CharacterCatalog = {
  preset_catalog: AdminCharacter[];
  user_characters: AdminCharacter[];
};
export type DbTable = { name: string; rows: number; columns: string[] };
export type ModelConfig = {
  id: string;
  name: string;
  provider: string;
  model_id: string;
  api_base: string;
  logo: string;
  enabled: boolean;
  assistant_name: string;
  assistant_model_id: string;
  assistant_enabled: boolean;
  assistant_thinking_mode: string;
  assistant_reasoning_effort: string;
  role: "available" | "primary" | "fallback";
  has_api_key: boolean;
  api_key_hint: string;
  purposes: string[];
  response_instruction: string;
  suggestion_instruction: string;
  compiler_instruction: string;
  moderation_instruction: string;
  emotion_instruction: string;
  assistant_general_instruction: string;
  assistant_psychology_instruction: string;
  assistant_health_instruction: string;
  assistant_homework_instruction: string;
  assistant_tarot_instruction: string;
  assistant_general_fallback_instruction: string;
  assistant_psychology_fallback_instruction: string;
  assistant_health_fallback_instruction: string;
  assistant_homework_fallback_instruction: string;
  assistant_tarot_fallback_instruction: string;
  temperature: string;
  short_temperature: string;
  max_tokens: string;
  short_max_tokens: string;
  gateway_read_timeout_seconds: string;
  tts_default_voice: string;
  thinking_mode: string;
  reasoning_effort: string;
};
export type ExpressionPreview = {
  character_id: string;
  status:
    | "queued"
    | "processing"
    | "ready"
    | "failed"
    | "no-image-model"
    | "missing";
  quality: string;
  error?: string;
  images: Record<string, string>;
};
export type ModelUpdate = ModelConfig & {
  expression_generation?: {
    characters: number;
    unique_sources: number;
    images: number;
  };
};

// View/editor contracts shared by the CMS entrypoint and domain controllers.
export type CmsHomeSection = {
  id: string;
  name: string;
  rule?: string;
  tags?: string[];
  hidden?: boolean;
};

export type Connection = {
  base: string;
  gateway: boolean;
  hint: string;
  source: string;
  ok: boolean;
  baseKeyId?: string;
  models: ModelConfig[];
};

export type AssistantStats = {
  requests: number;
  fallback_rate: number;
  latency: number;
  error_rate: number;
  days: number[];
};

export type AssistantProfile = {
  title: string;
  slogan: string;
  description: string;
  greeting: string;
  starters: string[];
  visible: boolean;
  user_pick: boolean;
  icon?: string;
  hue?: number;
  hair?: number;
  custom?: boolean;
  stats?: AssistantStats;
};

export type AssistantProfiles = {
  order: string[];
  items: Record<string, AssistantProfile>;
};

export type AssistantDraft = {
  main: string;
  f1: string;
  f2: string;
  prompt: string;
  fp1: string;
  fp2: string;
  title: string;
  slogan: string;
  description: string;
  greeting: string;
  starters: string;
  visible: boolean;
  user_pick: boolean;
};

export type GlobalDraft = {
  prompt: string;
  enabled: Record<string, boolean>;
};

export type AssistantTab = "info" | "model" | "prompt" | "stats";

export type NewAssistantForm = {
  title: string;
  slogan: string;
  description: string;
  greeting: string;
  icon: string;
  hue: number;
  hair: number;
  main: string;
  f1: string;
  prompt: string;
  visible: boolean;
};

export type LogRow = Record<string, unknown>;
