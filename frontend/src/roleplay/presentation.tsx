/** Stateless text rendering and character editor defaults. No audio or request side effects. */
import type { ReactNode } from "react";
import type { Character } from "./types";
import { formatStarText } from "../ui";

export function renderRoleplayText(
  text: string,
  isCharacter: boolean,
): ReactNode {
  if (!isCharacter) return text;
  const normalized = text
    .replace(/\\r\\n|\\n|\\r/g, "\n")
    .split("\n")
    .filter((line) => line.trim() !== "*")
    .join("\n")
    .trim()
    .replace(/(^|\n)([ \t]*)\*([^*\n]{1,240})\*(?=[ \t]|\n|$)/g, "$1$2**$3**");
  return formatStarText(normalized, "roleplay");
}

export const characterSpecPayload = (character: Character) => {
  const presentationFields = new Set([
    "usage_count",
    "trending_score",
    "reactions",
    "rating",
    "rating_count",
    "home_section",
    "creator",
    "is_public",
    "character_type",
    "tags",
  ]);
  return Object.fromEntries(
    Object.entries(character).filter(([key]) => !presentationFields.has(key)),
  );
};

export const roleLabels = {
  companion: "Đồng hành",
  study: "Học tập",
  work: "Công việc",
  health: "Sức khỏe",
  lifestyle: "Lối sống",
} as const;

export const suggestedTags = [
  "Anime",
  "Boss",
  "Mafia",
  "Romance",
  "Action",
  "Adventure",
  "Comedy",
  "Comics",
  "Drama",
  "Fantasy",
  "Horror",
  "Sports",
  "Supernatural",
  "Slice of Life",
  "Academy",
  "Actor",
  "Adaptive",
  "AI",
  "Alien",
  "Amnesia",
  "Ancient",
  "Android",
  "Angel",
  "Angst",
  "Animal",
  "Anthro",
  "Anxious",
  "Mystery",
  "Friendship",
  "Work",
  "Study",
];
