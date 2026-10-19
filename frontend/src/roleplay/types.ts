export type Character = {
  id: string;
  name: string;
  display_name: string;
  description: string;
  initial_greeting?: string;
  tts_volume?: number;
  tts_voice_id?: string;
  tts_voice_mode?: "shared" | "separate";
  tts_languages?: Record<string, { enabled: boolean; voice_id: string }>;
  tts_voice_vi?: string;
  tts_voice_en?: string;
  tts_gender?: string;
  creation_type: string;
  simulation_label: boolean;
  preset_type?: string;
  category?: "utility" | "entertainment";
  avatar_url?: string;
  source_character_id?: string | null;
  publication_status?: string;
  is_public?: boolean;
  character_type?: string;
  tags?: string[];
  creator?: { id: string; name: string; followers?: number };
  rating?: number;
  rating_count?: number;
  usage_count?: number;
  trending_score?: number;
  home_section?: "auto" | "featured" | "popular" | "top_rated" | "hidden";
  reactions?: Record<string, number>;
  identity?: { role?: string };
  support?: {
    primary_role: "study" | "work" | "health" | "lifestyle" | "companion";
    strengths: ("study" | "work" | "health" | "lifestyle" | "companion")[];
    introduction: string;
  };
};

export type Message = {
  id: string;
  sender_type: string;
  character_id: string | null;
  text: string;
  interrupted?: boolean;
  speech_ready?: boolean;
  speech_supported?: boolean;
  speech_languages?: string[];
  speech_error?: string;
  sources?: { document_id: string }[];
  suggestions?: string[];
  emotion?:
    | "neutral"
    | "happy"
    | "sad"
    | "angry"
    | "surprised"
    | "shy"
    | "thinking";
  attachment?: {
    document_id: string;
    filename: string;
    status: string;
    error?: string;
  };
};

export type Account = {
  id: string;
  username: string;
  display_name: string;
  theme: "light" | "dark";
  bio: string;
  language: import("../i18n").UiLanguage;
  reduced_motion: boolean;
  avatar_url?: string | null;
};

// Page contracts; these are presentation types, not API/schema changes.
export type Room = {
  topic?: string;
  id: string;
  name: string;
  character_ids: string[];
  created_at?: string;
  created?: boolean;
  is_public?: boolean;
};

export type StoryCandidate = {
  name: string;
  description: string;
  source_evidence: string[];
  importance: number;
};

export type HomeSection = {
  id: string;
  name: string;
  rule: "popular" | "trending" | "top_rated" | "favorites" | "tags";
  tags: string[];
};
