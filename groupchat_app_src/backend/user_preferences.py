"""User preferences for LLM tone."""

# Store user tone preferences in memory (could be moved to database)
user_tone_preferences = {}

def set_user_tone(username: str, tone: str):
    """Set tone preference for user."""
    user_tone_preferences[username] = tone

def get_user_tone(username: str) -> str:
    """Get tone preference for user."""
    return user_tone_preferences.get(username, "none")
