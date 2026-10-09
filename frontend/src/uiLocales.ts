import { validUiTranslation, isLanguageNeutralUiText } from "./uiTranslationValidation";
export { validUiTranslation } from "./uiTranslationValidation";
import type { UiLanguage } from "./i18n";

// All supported UI packs ship in the app bundle. A language switch must
// not depend on fetching a lazy asset that can disappear after deployment.
const bundledTranslations = import.meta.glob<Record<string, string>>("./locales/{en,zh,ja,ko,my,km}.json", {
  eager: true,
  import: "default",
});
export async function loadUiTranslations(language: UiLanguage): Promise<Record<string, string>> {
  if (language === "vi") return {};
  return bundledTranslations["./locales/" + language + ".json"] || {};
}

const catalogs = import.meta.glob<Array<{ source: string; en: string }>>("./locales/catalog.json", { eager: true, import: "default" });
const catalog = catalogs["./locales/catalog.json"];
export class UiTranslationLoadError extends Error {
  constructor(public readonly code: string, public readonly stage = "ui", public readonly language = "") {
    super(code);
  }
}
export function uiLanguageErrorMessage(error: unknown, language: string): string {
  const code = error instanceof UiTranslationLoadError ? error.code : "load_failed";
  const stage = error instanceof UiTranslationLoadError && error.stage === "introductions"
    ? "Character introductions" : "Interface";
  const reasons: Record<string, string> = {
    session_expired: "Your session has expired. Please sign in again",
    access_denied: "Translation access denied",
    credentials: "The translation API key is invalid",
    model_not_assigned: "Assign a translation model in CMS",
    timeout: "The translation request timed out",
    output_limit: "The translation output limit was reached",
    gateway_error: "The translation gateway failed",
    invalid_translation: "The translation is incomplete or in the wrong language",
    load_failed: "Could not load language data",
    network_error: "Could not reach the translation server. Check your connection",
  };
  return stage + " [" + language + "]: " + (reasons[code] || code) + ". Please retry or switch to Vietnamese (vi).";
}
export async function translateUiBatch(language: string, texts: string[], kind?: "character"): Promise<string[]> {
  if (texts.some((value) => value.length > 1200))
    throw new Error("Translation text exceeds the API limit");
  const token = localStorage.getItem("auth_token");
  let response: Response;
  try {
    response = await fetch((import.meta.env.VITE_API_URL || "") + "/v1/i18n/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: JSON.stringify({ language, texts, kind }),
    signal: AbortSignal.timeout(45000),
  });
  } catch (error) {
    throw new UiTranslationLoadError(
      error instanceof Error && /timeout|abort/i.test(error.name + " " + error.message)
        ? "timeout" : "network_error",
    );
  }
  if (!response.ok) throw new UiTranslationLoadError(response.status === 401 ? "session_expired" : response.status === 403 ? "access_denied" : "HTTP " + response.status);

  const result = await response.json() as { translations?: unknown[]; failures?: Array<{ code: string }> };
  if (result.failures?.length) {
    const allowed = ["credentials", "model_not_assigned", "timeout", "output_limit", "gateway_error", "invalid_translation"];
    const code = result.failures[0].code;
    throw new UiTranslationLoadError(allowed.includes(code) ? code : "gateway_error");
  }
  if (!Array.isArray(result.translations) || result.translations.length !== texts.length ||
      result.translations.some((value) => typeof value !== "string" || !value.trim()))
    throw new UiTranslationLoadError("invalid_translation");
  return result.translations as string[];
}
export async function loadCompleteUiTranslations(language: UiLanguage): Promise<Record<string, string>> {
  if (language === "vi") return {};
  const key = "ui_complete_v1:" + language;
  let cached: Record<string, string> = {};
  try { cached = JSON.parse(localStorage.getItem(key) || "{}"); } catch {}
  const values = { ...cached, ...await loadUiTranslations(language) };
  for (const item of catalog) if (isLanguageNeutralUiText(item.source)) values[item.source] = item.source;
  const missing = catalog.filter((item) => !validUiTranslation(item.source, values[item.source], language, item.en));
  for (let offset = 0; offset < missing.length; offset += 120) {
    const batch = missing.slice(offset, offset + 120);
    const result = await translateUiBatch(language, batch.map((item) => item.source));
    batch.forEach((item, index) => {
      const translated = result[index];
      if (!validUiTranslation(item.source, translated, language, item.en))
        throw new UiTranslationLoadError("invalid_translation", "ui", language);
      values[item.source] = translated;
    });
  }
  if (catalog.some((item) => !validUiTranslation(item.source, values[item.source], language, item.en)))
    throw new UiTranslationLoadError("invalid_translation", "ui", language);
  try { localStorage.setItem(key, JSON.stringify(values)); } catch {}
  return values;
}
export async function loadCharacterIntroductions(language: string, texts: string[], userId = "guest"): Promise<Record<string, string>> {
  const key = "character_intro_v3:" + userId + ":" + language;
  let values: Record<string, string> = {};
  try { values = JSON.parse(localStorage.getItem(key) || "{}"); } catch {}
  const persist = () => { try { localStorage.setItem(key, JSON.stringify(values)); } catch {} };
  const targetScripts: Record<string, RegExp> = {
    zh: /[\u3400-\u9fff]/, ja: /[\u3040-\u30ff\u3400-\u9fff]/,
    ko: /[\uac00-\ud7af]/, my: /[\u1000-\u109f\uaa60-\uaa7f]/, km: /[\u1780-\u17ff]/,
  };
  const valid = (source: string, value: unknown): value is string =>
    (language === "vi" ? typeof value === "string" && Boolean(value.trim()) && !/[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af\u1000-\u109f\u1780-\u17ff]/.test(value)
      : validUiTranslation(source, value, language)) ||
    (typeof value === "string" && value === source && Boolean(targetScripts[language]?.test(source)));
  const missing = [...new Set(texts.filter(Boolean))].filter((source) => !valid(source, values[source]));
  // Translate complete descriptions without the API truncating them at 1200.
  // Keep pieces small enough to fit the gateway output budget.
  const pieces = (source: string): string[] => {
    const result: string[] = [];
    let rest = source;
    while (rest.length > 900) {
      const candidate = rest.slice(0, 900);
      const boundary = Math.max(candidate.lastIndexOf("\n"), candidate.lastIndexOf(". "), candidate.lastIndexOf(" "));
      const cut = boundary >= 450 ? boundary + 1 : 900;
      result.push(rest.slice(0, cut));
      rest = rest.slice(cut);
    }
    if (rest) result.push(rest);
    return result;
  };
  try {
    const work = [...new Set(missing.flatMap(pieces))].filter((piece) => !valid(piece, values[piece]));
    for (let offset = 0; offset < work.length;) {
      const batch: string[] = [];
      let characters = 0;
      while (offset < work.length && batch.length < 6 &&
             (!batch.length || characters + work[offset].length <= 1800)) {
        const piece = work[offset++];
        batch.push(piece);
        characters += piece.length;
      }
      const translated = await translateUiBatch(language, batch, "character");
      batch.forEach((source, index) => {
        if (valid(source, translated[index])) values[source] = translated[index];
      });
      persist(); // A failed later batch does not discard earlier translations.
      if (batch.some((source, index) => !valid(source, translated[index])))
        throw new UiTranslationLoadError("invalid_translation");
    }
    for (const source of missing) {
      const parts = pieces(source);
      if (parts.some((part) => !valid(part, values[part]))) throw new UiTranslationLoadError("invalid_translation");
      values[source] = parts.map((part) => values[part]).join("\n");
    }
    persist();
    return values;
  } catch (error) {
    const code = error instanceof UiTranslationLoadError ? error.code
      : error instanceof Error && /timeout|abort/i.test(error.name + " " + error.message) ? "timeout" : "gateway_error";
    throw new UiTranslationLoadError(code, "introductions", language);
  }
}
export function afterUiLanguagePaint(): Promise<void> {
  return new Promise((resolve) => {
    // Hidden workspace frames can suspend animation frames indefinitely.
    const timer = window.setTimeout(resolve, 250);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      window.clearTimeout(timer);
      resolve();
    }));
  });
}
export type UiLanguageGate = {
  language: string; busy: boolean; error?: string; retry?: () => void; cancel?: () => void;
};
let ownGate: UiLanguageGate = { language: "vi", busy: false };
let gate = ownGate;
const childGates = new Map<MessageEventSource, { language: string; busy: boolean; error?: string }>();
const listeners = new Set<() => void>();
function publishGate() {
  const frames = Array.from(document.querySelectorAll("iframe")).map((frame) => frame.contentWindow);
  const children = [...childGates].filter(([source, value]) =>
    frames.includes(source as Window) && value.language === ownGate.language).map(([, value]) => value);
  const childError = children.find((value) => value.error)?.error;
  gate = {
    ...ownGate,
    busy: ownGate.busy || children.some((value) => value.busy),
    error: ownGate.error || childError,
    retry: () => {
      ownGate.retry?.();
      for (const frame of frames) frame?.postMessage({ type: "avibi-ui-language-retry" }, window.location.origin);
    },
  };
  const root = document.getElementById("root");
  if (root) {
    root.inert = gate.busy || Boolean(gate.error);
    root.setAttribute("aria-busy", String(gate.busy));
  }
  for (const listener of listeners) listener();
}
export function setUiLanguageGate(value: UiLanguageGate) {
  ownGate = value;
  publishGate();
  if (window.parent !== window) window.parent.postMessage({
    type: "avibi-ui-language-gate", language: value.language, busy: value.busy, error: value.error,
  }, window.location.origin);
}
window.addEventListener("message", (event) => {
  if (event.origin !== window.location.origin || !event.data || typeof event.data !== "object") return;
  if (event.data.type === "avibi-ui-language-retry" && event.source === window.parent && window.parent !== window) {
    ownGate.retry?.();
    return;
  }
  if (event.data.type !== "avibi-ui-language-gate" || !event.source ||
      !Array.from(document.querySelectorAll("iframe")).some((frame) => frame.contentWindow === event.source)) return;
  if (typeof event.data.language !== "string" || typeof event.data.busy !== "boolean") return;
  childGates.set(event.source, {
    language: event.data.language, busy: event.data.busy,
    error: typeof event.data.error === "string" ? event.data.error : undefined,
  });
  publishGate();
});
export const uiLanguageLoadingSnapshot = () => gate;
export function subscribeUiLanguageLoading(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
