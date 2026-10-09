export function isLanguageNeutralUiText(source: string): boolean {
  const value = source.trim();
  return !/\p{L}/u.test(value) ||
    value === "x" ||
    /^https?:\/\/\S+$/i.test(value) ||
    /^(?:PNG|JPEG|JPG|WEBP|GIF|SVG|AVIF|HEIC)(?:\s*[,·|/]\s*(?:PNG|JPEG|JPG|WEBP|GIF|SVG|AVIF|HEIC))*$/i.test(value);
}
const technical = /^(?:Avibi(?: Platform)?|Vbee|AI|API|TTS|JSON|URL|PDF|OK|Email|Avatar|Model|Tags|Tarot|Chat|Enter|Shift|PNG|JPG|JPEG|MB|GB|GPT.*)$/i;
const placeholders = (value: string) => [...value.matchAll(/\{(?:name|count)\}/g)].map((m) => m[0]).sort().join("|");
export function validUiTranslation(source: string, value: unknown, language: string, english = ""): value is string {
  if (typeof value !== "string" || !value.trim() || placeholders(source) !== placeholders(value)) return false;
  // Symbols, counts and punctuation have no language (×, …, 12, etc.).
  if (isLanguageNeutralUiText(source)) return value.trim() === source.trim();
  if (technical.test(source)) return true;
  if (value.trim() === source.trim()) {
    // English UI labels already written in English can remain unchanged.
    if (language === "en" && (!english || english === source) &&
        !/[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/iu.test(source)) return true;
    return false;
  }
  if (language !== "en" && english && value.trim() === english.trim()) return false;
  const scripts: Record<string, RegExp> = {
    zh: /[\u3400-\u9fff]/, ja: /[\u3040-\u30ff\u3400-\u9fff]/,
    ko: /[\uac00-\ud7af]/, my: /[\u1000-\u109f\uaa60-\uaa7f]/, km: /[\u1780-\u17ff]/,
  };
  return !scripts[language] || scripts[language].test(value);
}
