"""Vbee voice catalog parsing and character-to-voice selection."""

import re
from urllib.parse import urlsplit


PRESET_GENDERS = {
    "ideal_boyfriend": "male",
    "classmate": "female",
    "cold_ceo": "male",
    "entertainment_ceo": "male",
    "entertainment_lover": "female",
    "entertainment_best_friend": "male",
}


def voice_connect_timeout(default: float, request_timeout: float) -> float:
    """Use the shared gateway setting while retaining Voice's existing defaults."""
    from .timeouts import gateway_connect_timeout
    return gateway_connect_timeout(default, request_timeout)


def vbee_voice_url(api_base: str) -> str:
    return api_base.rstrip("/").removesuffix("/v1") + "/api/v1/voices"


def speech_api_base(api_base: str) -> str:
    """Accept a service origin as well as an OpenAI-compatible /v1 base."""
    base = api_base.rstrip("/")
    return base + "/v1" if not urlsplit(base).path else base


def normalize_voices(payload) -> list[dict[str, str]]:
    """Accept the catalog's list or envelope without exposing unrelated fields."""
    if isinstance(payload, dict):
        payload = next((payload[key] for key in ("voices", "data", "items", "results") if isinstance(payload.get(key), list)), [])
    if not isinstance(payload, list):
        return []
    voices = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        voice_id = str(row.get("voice_id") or row.get("id") or row.get("voice_code") or row.get("code") or "").strip()
        if not voice_id:
            continue
        gender = str(row.get("gender") or "").strip().lower()
        if gender in ("nam", "man", "m"):
            gender = "male"
        elif gender in ("nữ", "nu", "woman", "f"):
            gender = "female"
        if gender not in ("male", "female"):
            gender = "unspecified"
        voices.append({
            "id": voice_id,
            "name": str(row.get("name") or row.get("display_name") or voice_id),
            "gender": gender,
            "language": str(row.get("language") or ""),
            "style": str(row.get("style") or ""),
        })
    return voices


def character_voice_gender(character) -> str:
    """Use explicit CMS metadata first; infer only clear existing descriptions."""
    if character.tts_gender in ("male", "female"):
        return character.tts_gender
    if character.preset_type in PRESET_GENDERS:
        return PRESET_GENDERS[character.preset_type]
    description = " ".join((character.description, character.identity.backstory, character.system_prompt)).lower()
    female = bool(re.search(r"\b(cô gái|phụ nữ|nữ sinh|người mẹ|female|woman|girl|she/her|she is)\b", description))
    male = bool(re.search(r"\b(chàng trai|đàn ông|nam sinh|người cha|male|man|boy|he/him|he is)\b", description))
    if female != male:
        return "female" if female else "male"
    return "unspecified"


def select_voice(voices: list[dict[str, str]], gender: str, preferred_language: str = "vi", strict_language: bool = False) -> str:
    language=(preferred_language or "vi").split("-",1)[0].lower()
    aliases={"vi":("vi","vietnamese","vietnam","tiếng việt"),"en":("en","english")}
    def matches(voice):
        value=voice.get("language","").lower()
        return any(value.startswith(alias) for alias in aliases.get(language,(language,)))
    localized=[voice for voice in voices if matches(voice)]
    choices=localized if strict_language else localized or voices
    if not choices:return ""
    # Unknown gender still gets a real catalog voice. Prefer language before
    # gender, and preserve gender when the matching catalog offers it.
    choices=sorted(choices,key=lambda voice:(gender in ("male","female") and voice["gender"]!=gender,voice["id"]))
    return choices[0]["id"]
