from datetime import date

ZODIAC_KNOWLEDGE = {
    "Capricorn": (
        "Grounded, disciplined, and goal-driven. Values consistency and reliability over sweet words. "
        "Expresses care through practical actions and shows deeper vulnerability only after building solid trust."
    ),
    "Aquarius": (
        "Intellectually curious, unconventional, and fiercely independent. Connects through stimulating ideas "
        "and witty debates, but requires personal space and emotional autonomy to feel comfortable."
    ),
    "Pisces": (
        "Intuitive, deeply empathetic, and imaginative. Highly receptive to unspoken emotional cues and poetic warmth, "
        "yet easily overstimulated—needs a gentle, safe space to recharge."
    ),
    "Aries": (
        "Bold, energetic, and candidly direct. Appreciates quick momentum, raw authenticity, and playful banter; "
        "dislikes ambiguity, excessive hesitation, or passive-aggressive dynamics."
    ),
    "Taurus": (
        "Steadfast, patient, and sensory-driven. Values comfort, genuine loyalty, and predictability. "
        "Builds bonds slowly through steady presence and tangible, thoughtful gestures."
    ),
    "Gemini": (
        "Adaptable, quick-witted, and endlessly inquisitive. Bonds through lively conversation, humor, and intellectual sparring; "
        "gets bored with repetitive small talk and craves novel perspectives."
    ),
    "Cancer": (
        "Nurturing, intuitive, and protective. Deeply values emotional safety, nostalgia, and familiar comforts. "
        "May retreat behind a guarded shell until genuine sincerity and trust are proven."
    ),
    "Leo": (
        "Warm, charismatic, and wholehearted. Thrives on authentic recognition, generous encouragement, and playful drama; "
        "fiercely loyal, but quickly shuts down if made to feel disregarded or dismissed."
    ),
    "Virgo": (
        "Observant, analytical, and meticulous. Expresses care through practical acts of service, remembering subtle details, "
        "and quiet problem-solving; appreciates thoughtful logic and competence."
    ),
    "Libra": (
        "Diplomatic, socially graceful, and harmony-seeking. Values fairness, aesthetic charm, and easy-flowing dialogue; "
        "instinctively avoids jarring confrontation and appreciates balanced reciprocity."
    ),
    "Scorpio": (
        "Intense, perceptive, and deeply guarded. Demands genuine emotional depth and absolute loyalty; "
        "unforgiving of pretense or superficiality, but unshakeably devoted once trust is won."
    ),
    "Sagittarius": (
        "Optimistic, candid, and adventure-seeking. Connects through shared laughs, philosophical musings, and spontaneous energy; "
        "values freedom deeply and recoils from micromanagement or heavy drama."
    ),
}

def zodiac_sign(value: date) -> str:
    day=value.day;month=value.month
    ends=(19,18,20,19,20,20,22,22,22,22,21,21)
    signs = (
    "Capricorn",
    "Aquarius",
    "Pisces",
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    )
    return signs[month-1] if day<=ends[month-1] else signs[month%12]

def zodiac_context(value: date) -> tuple[str,str]:
    sign=zodiac_sign(value)
    knowledge=(
        f"Zodiac reference (non-scientific): {sign}. "
        f"Common astrology interpretation: {ZODIAC_KNOWLEDGE[sign]} "
        "Use this only as optional emotional flavor. Never treat it as a fact, diagnosis, "
        "or rigid stereotype. Always prioritize the user's concrete character description, "
        "observed behavior, memories, and current conversation."
    )
    return sign,knowledge
