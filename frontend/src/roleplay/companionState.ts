import type {Character, Message} from "./types";
export function hasElfCompanion(character:Character) {
  return character.preset_type === "elf" ||
    /^(?:selene moonbrook|elf)$/i.test(character.name.trim()) ||
    /\/elf\.(?:png|webp|jpg)(?:\?|$)/i.test(character.avatar_url || "");
}
export function companionTalking(characterId:string,
  speakingMessageId:string|null, messages:Message[]) {
  return !!speakingMessageId &&
    messages.some(message=>message.id===speakingMessageId && message.character_id===characterId);
}
