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


def is_vbee_voice_base(api_base: str) -> bool:
    host = (urlsplit(api_base).hostname or "").lower()
    return host == "api-voice-uat.vbeelabs.ai" or host.endswith(".vbeelabs.ai")


def vbee_voice_url(api_base: str) -> str:
    return api_base.rstrip("/").removesuffix("/v1") + "/api/v1/voices"


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


def select_voice(voices: list[dict[str, str]], gender: str, preferred_language: str = "vi") -> str:
    choices = [voice for voice in voices if voice["gender"] == gender]
    if not choices:
        return ""
    language = (preferred_language or "vi").lower()
    choices.sort(key=lambda voice: (not voice["language"].lower().startswith(language), voice["id"]))
    return choices[0]["id"]
