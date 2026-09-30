from character_chat.schemas import CharacterSpec
from character_chat.voice import character_voice_gender, normalize_voices, select_voice, vbee_voice_url


def test_vbee_voice_catalog_selects_matching_gender_and_language():
    voices = normalize_voices({"voices": [
        {"voice_id": "male_en", "name": "English man", "gender": "male", "language": "en"},
        {"voice_id": "female_vi", "name": "Vietnamese woman", "gender": "female", "language": "vi"},
        {"voice_id": "male_vi", "name": "Vietnamese man", "gender": "male", "language": "vi"},
    ]})
    assert select_voice(voices, "male", "vi") == "male_vi"
    assert select_voice(voices, "female", "vi") == "female_vi"
    assert select_voice(voices, "unspecified", "vi") == ""
    assert vbee_voice_url("https://api-voice-uat.vbeelabs.ai/v1") == "https://api-voice-uat.vbeelabs.ai/api/v1/voices"


def test_character_gender_prefers_cms_and_known_presets():
    preset = CharacterSpec(name="Mia", preset_type="entertainment_lover")
    assert character_voice_gender(preset) == "female"
    public = CharacterSpec(name="Minh", description="Một chàng trai thích kể chuyện", tts_gender="female")
    assert character_voice_gender(public) == "female"
    public.tts_gender = "unspecified"
    assert character_voice_gender(public) == "male"
    assert character_voice_gender(CharacterSpec(name="Alex")) == "unspecified"
