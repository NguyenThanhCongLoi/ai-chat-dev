import type { Character } from "./types";
/** Keep canonical system cards selectable even after their owned copy exists. */
export function roomCharacterPool(owned: Character[], presets: Character[]) {
  const system = presets.filter(preset => preset.home_section !== "hidden").map(preset => ({
    character: owned.find(character => character.creation_type === "preset" &&
      character.preset_type === preset.preset_type) || preset,
    source: "system" as const,
  }));
  const systemIds = new Set(system.map(item => item.character.id));
  return [
    ...owned.filter(character => !systemIds.has(character.id)).map(character => ({
      character, source: "owned" as const,
    })),
    ...system,
  ];
}
