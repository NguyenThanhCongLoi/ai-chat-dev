"""Validate runtime translations before they enter the shared cache."""
import re

SCRIPTS = {
    "km": re.compile(r"[\u1780-\u17ff]"),
    "zh": re.compile(r"[\u3400-\u9fff]"),
    "ja": re.compile(r"[\u3040-\u30ff\u3400-\u9fff]"),
    "ko": re.compile(r"[\uac00-\ud7af]"),
    "my": re.compile(r"[\u1000-\u109f\uaa60-\uaa7f]"),
}
TECHNICAL = re.compile(r"^(?:Avibi(?: Platform)?|Vbee|AI|API|TTS|JSON|URL|PDF|OK|Email|Avatar|Model|Tags|Tarot|Chat|Enter|Shift|PNG|JPG|JPEG|MB|GB|GPT.*)$", re.I)
FORMATS = re.compile(r"^(?:PNG|JPEG|JPG|WEBP|GIF|SVG|AVIF|HEIC)(?:\s*[,·|/]\s*(?:PNG|JPEG|JPG|WEBP|GIF|SVG|AVIF|HEIC))*$", re.I)
VIETNAMESE = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.I)


def valid_translation(source, value, language):
    if not isinstance(value, str) or not value.strip():
        return False
    source, value = source.strip(), value.strip()
    placeholders = lambda text: sorted(re.findall(r"\{(?:name|count)\}", text))
    if placeholders(source) != placeholders(value):
        return False
    if (not any(char.isalpha() for char in source) or source == "x"
            or re.fullmatch(r"https?://\S+", source, re.I) or FORMATS.fullmatch(source)):
        return value == source
    if TECHNICAL.fullmatch(source):
        return True
    script = SCRIPTS.get(language)
    if value == source:
        # Already in the target writing system, or already English.
        return bool(script.search(source)) if script else language == "en" and not VIETNAMESE.search(source)
    return not script or bool(script.search(value))
