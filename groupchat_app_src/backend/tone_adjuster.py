"""Tone adjustment for messages."""

from llm import chat_completion

TONES = {
    "professional": "formal, business-appropriate, polite",
    "casual": "friendly, relaxed, conversational",
    "concise": "brief, to-the-point, no fluff",
    "detailed": "comprehensive, thorough, explanatory",
    "empathetic": "understanding, supportive, compassionate",
    "direct": "straightforward, clear, no-nonsense"
}

async def adjust_tone(message: str, tone: str) -> str:
    """Adjust message tone using LLM."""
    tone_desc = TONES.get(tone.lower(), tone)
    
    prompt = f"""Rewrite this message in a {tone_desc} tone. Keep the core meaning but adjust the style.

Original: {message}

Rewritten ({tone} tone):"""
    
    try:
        result = await chat_completion([{"role": "user", "content": prompt}], temperature=0.7)
        return result.strip()
    except:
        return message

async def detect_tone_request(message: str) -> dict:
    """Detect if user is requesting tone adjustment."""
    import re
    
    # Pattern: "make it more [tone]" or "rephrase as [tone]" or "tone: [tone]"
    patterns = [
        r'make\s+(?:it\s+)?(?:more\s+)?(\w+)',
        r'rephrase\s+(?:as\s+)?(\w+)',
        r'tone:\s*(\w+)',
        r'adjust\s+tone\s+to\s+(\w+)',
        r'sound\s+more\s+(\w+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            tone = match.group(1)
            if tone in TONES:
                return {"tone": tone, "detected": True}
    
    return {"detected": False}
