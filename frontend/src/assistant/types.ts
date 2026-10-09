import type { UiLanguage } from "../i18n";

export type Account = {
  id: string;
  username?: string;
  display_name: string;
  bio?: string;
  avatar_url?: string | null;
  theme: "light" | "dark";
  language: UiLanguage;
};
export type Chat = { is_new?: boolean; id: string; mode: Mode; title: string; created_at: string };
export type WorkspaceRoom = { id: string; name: string; created_at?: string; character_ids?: string[] };
export type WorkspaceCharacter = { id: string; name: string; avatar_url?: string | null };
export type ChatSource = {
  index: number;
  document_id: string;
  filename: string;
  location?: string;
  score?: number;
};
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  sources?: ChatSource[];
  suggestions?: string[];
  interrupted?: boolean;
};
export type UploadedFile = { id: string; filename: string; status: string };
export type AssistantModel = { id: string; name: string; role: string };
export type SavedMemory = { id: string; room_id: string; mode: Mode; content: string; created_at: string };
export type AssistantReminder = { id: string; title: string; due_at: string; status: "active" | "paused" | "done"; last_notified_at?: string | null };
export type Mode =
  | "assistant_general"
  | "assistant_psychology"
  | "assistant_health"
  | "assistant_homework"
  | "assistant_tarot";
export type ModeItem = {
  id: Mode;
  icon: string;
  title: string;
  copy: string;
  slogan: string;
  greeting: string;
};
