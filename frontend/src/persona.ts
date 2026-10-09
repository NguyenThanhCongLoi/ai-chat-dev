/* Persona minh họa của các trợ lý (theo "Avibi Platform Prototype").
   Dùng chung cho React (ui.tsx) và Admin CMS (admin.ts, không dùng React). */

export type AssistantModeId =
  | "assistant_general"
  | "assistant_psychology"
  | "assistant_health"
  | "assistant_homework"
  | "assistant_tarot";

export type Emotion = "neutral" | "happy" | "sad" | "angry" | "surprised" | "shy";

/** Màu, kiểu tóc và biểu tượng (dùng khi không có tranh minh họa) của từng trợ lý. */
export const MODE_META: Record<AssistantModeId, { icon: string; hue: number; hair: string }> = {
  assistant_general: { icon: "sparkles", hue: 172, hair: "M24 58C22 30 78 30 76 58C72 44 62 38 50 40C38 38 28 44 24 58z" },
  assistant_psychology: { icon: "cloud", hue: 205, hair: "M22 64C16 14 84 14 78 64C78 50 70 42 50 44C32 42 24 50 22 64zM22 64l-2 18 8-8zM78 64l2 18-8-8z" },
  assistant_health: { icon: "heart-rate", hue: 140, hair: "M26 52C28 34 72 30 75 52C66 42 44 46 30 46z" },
  assistant_homework: { icon: "book-alt", hue: 32, hair: "M24 56C24 30 76 30 76 56L70 46 62 52 56 42 48 50 40 42 32 52z" },
  assistant_tarot: { icon: "moon-stars", hue: 275, hair: "M20 74C12 12 88 12 80 74C78 52 70 44 50 45C30 44 22 52 20 74z" },
};

export const metaOf = (mode: string) => MODE_META[mode as AssistantModeId] || MODE_META.assistant_general;

export const EYES: Record<Emotion, string> = {
  neutral: '<circle cx="40" cy="57" r="3.2"/><circle cx="60" cy="57" r="3.2"/>',
  happy: '<path d="M35 58q5-6 10 0M55 58q5-6 10 0" fill="none" stroke-width="3"/>',
  sad: '<circle cx="40" cy="58" r="3"/><circle cx="60" cy="58" r="3"/><path d="M34 49l11-3M66 49l-11-3" fill="none" stroke-width="2.4"/>',
  angry: '<circle cx="40" cy="58" r="3"/><circle cx="60" cy="58" r="3"/><path d="M33 47l12 5M67 47l-12 5" fill="none" stroke-width="2.8"/>',
  surprised: '<circle cx="40" cy="56" r="4.6"/><circle cx="60" cy="56" r="4.6"/>',
  shy: '<path d="M35 57q5 4 10 0M55 57q5 4 10 0" fill="none" stroke-width="2.6"/>',
};
export const MOUTH: Record<Emotion, string> = {
  neutral: '<path d="M44 72h12" stroke-width="2.6"/>',
  happy: '<path d="M40 68q10 11 20 0" stroke-width="2.8"/>',
  sad: '<path d="M42 75q8-7 16 0" stroke-width="2.6"/>',
  angry: '<path d="M42 74q8-5 16 0" stroke-width="2.8"/>',
  surprised: '<ellipse cx="50" cy="72" rx="4.5" ry="5.5" fill="#5a2a2a" stroke="none"/>',
  shy: '<path d="M46 71q4 3 8 0" stroke-width="2.4"/>',
};

/** Tranh minh họa riêng của từng trợ lý chuyên sâu. */
export const ILLUSTRATIONS: Partial<Record<AssistantModeId, string>> = {
  assistant_psychology: '<path d="M40 70c-12 0-20-8-20-18s9-17 19-16c4-12 14-18 26-16 11 2 19 11 20 22 9 1 15 8 15 16 0 7-7 12-15 12z" fill="#fff" opacity=".9"/><path d="M60 64s-12-7-12-15c0-4 3-7 6-7 3 0 5 2 6 4 1-2 3-4 6-4 3 0 6 3 6 7 0 8-12 15-12 15z" fill="hsl(350 70% 62%)"/><circle cx="104" cy="30" r="5" fill="#fff" opacity=".7"/><circle cx="116" cy="44" r="3" fill="#fff" opacity=".6"/>',
  assistant_health: '<rect x="40" y="22" width="48" height="56" rx="10" fill="#fff" opacity=".92"/><path d="M58 50h12M64 44v12" stroke="hsl(140 55% 38%)" stroke-width="6" stroke-linecap="round"/><path d="M14 62h18l6-10 8 18 6-12h16" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" opacity=".85"/><path d="M100 70c0-14 10-22 22-24-2 14-10 24-22 24z" fill="hsl(110 50% 45%)"/><path d="M100 70c6-6 12-14 18-20" stroke="#fff" stroke-width="1.5" opacity=".7"/>',
  assistant_homework: '<path d="M20 34c14-6 28-6 44 2v40c-16-8-30-8-44-2z" fill="#fff" opacity=".95"/><path d="M108 34c-14-6-28-6-44 2v40c16-8 30-8 44-2z" fill="#fff" opacity=".8"/><path d="M28 44h26M28 52h22M28 60h24M74 44h26M74 52h20" stroke="hsl(32 40% 70%)" stroke-width="2.5" stroke-linecap="round"/><path d="M96 14l14 14-30 30-16 3 3-16z" fill="hsl(45 90% 60%)"/><path d="M96 14l14 14" stroke="hsl(15 70% 50%)" stroke-width="5"/>',
  assistant_tarot: '<rect x="30" y="20" width="30" height="48" rx="5" fill="#fff" opacity=".7" transform="rotate(-14 45 44)"/><rect x="50" y="16" width="30" height="48" rx="5" fill="#fff"/><rect x="72" y="20" width="30" height="48" rx="5" fill="#fff" opacity=".7" transform="rotate(14 87 44)"/><path d="M71 34a8 8 0 1 1-6-8 6 6 0 0 0 6 8z" fill="hsl(275 50% 55%)"/><path d="M65 48l1.5 3.5 3.5.5-2.6 2.4.7 3.6-3.1-1.8-3.1 1.8.7-3.6-2.6-2.4 3.5-.5z" fill="hsl(45 90% 55%)"/><circle cx="16" cy="24" r="2" fill="#fff"/><circle cx="114" cy="16" r="2.5" fill="#fff"/><circle cx="118" cy="66" r="1.8" fill="#fff"/>',
};

/** Các kiểu tóc có sẵn khi tạo trợ lý mới. */
export const HAIRS = [
  "M24 58C22 30 78 30 76 58C72 44 62 38 50 40C38 38 28 44 24 58z",
  "M22 64C16 14 84 14 78 64C78 50 70 42 50 44C32 42 24 50 22 64zM22 64l-2 18 8-8zM78 64l2 18-8-8z",
  "M26 52C28 34 72 30 75 52C66 42 44 46 30 46z",
  "M24 56C24 30 76 30 76 56L70 46 62 52 56 42 48 50 40 42 32 52z",
  "M20 74C12 12 88 12 80 74C78 52 70 44 50 45C30 44 22 52 20 74z",
];

/** Gương mặt persona dạng chuỗi SVG theo màu và kiểu tóc, cho nơi render bằng innerHTML. */
export function faceSvg(hue: number, hair: string, size = 34, emotion: Emotion = "happy") {
  const blush = emotion === "shy" ? 0.75 : emotion === "happy" ? 0.4 : 0;
  return `<svg class="personaFace" width="${size}" height="${size}" viewBox="0 0 100 100" aria-hidden="true">`
    + `<rect width="100" height="100" fill="hsl(${hue} 55% 82%)"/>`
    + `<circle cx="82" cy="18" r="22" fill="hsl(${(hue + 40) % 360} 60% 88%)"/>`
    + `<path d="M14 104c4-20 18-28 36-28s32 8 36 28z" fill="hsl(${hue} 50% 46%)"/>`
    + `<ellipse cx="50" cy="60" rx="24" ry="26" style="fill:var(--skin)"/>`
    + `<path d="${hair}" fill="hsl(${hue} 30% 24%)"/>`
    + (blush ? `<ellipse cx="33" cy="66" rx="5.5" ry="3" fill="#E98A8A" opacity="${blush}"/><ellipse cx="67" cy="66" rx="5.5" ry="3" fill="#E98A8A" opacity="${blush}"/>` : "")
    + `<g fill="#2b2420" stroke="#2b2420" stroke-linecap="round">${EYES[emotion]}</g>`
    + `<g fill="none" stroke="#7a3b35" stroke-linecap="round">${MOUTH[emotion]}</g>`
    + `</svg>`;
}

/** Gương mặt persona của một trợ lý có sẵn. */
export function personaFaceSvg(mode: string, size = 34, emotion: Emotion = "happy") {
  const { hue, hair } = metaOf(mode);
  return faceSvg(hue, hair, size, emotion);
}

/** Tranh minh họa thẻ trợ lý dạng chuỗi HTML: tranh vẽ riêng nếu có, nếu không thì nền màu và biểu tượng. */
export function illustrationHtml(mode: string, hue = metaOf(mode).hue, icon = metaOf(mode).icon) {
  const art = ILLUSTRATIONS[mode as AssistantModeId];
  if (!art)
    return `<span class="modeIllustration" style="background:linear-gradient(150deg,hsl(${hue} 58% 62%),hsl(${(hue + 35) % 360} 55% 46%))" aria-hidden="true"><span class="modeIllustrationOrb"></span><span class="modeIllustrationIcon" style="color:hsl(${hue} 50% 38%)"><i class="fi-rr-${icon} vi"></i></span></span>`;
  const id = `illu-${mode}`;
  return `<span class="modeIllustration" aria-hidden="true"><svg viewBox="0 0 128 88" preserveAspectRatio="xMidYMid slice" style="display:block;width:100%;height:100%"><defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="hsl(${hue} 60% 62%)"/><stop offset="1" stop-color="hsl(${(hue + 35) % 360} 55% 48%)"/></linearGradient></defs><rect width="128" height="88" fill="url(#${id})"/><circle cx="118" cy="84" r="34" fill="#fff" opacity=".12"/><circle cx="6" cy="6" r="22" fill="#fff" opacity=".1"/>${art}</svg></span>`;
}
