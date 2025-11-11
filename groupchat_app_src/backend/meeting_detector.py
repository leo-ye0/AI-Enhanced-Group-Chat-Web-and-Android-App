from llm import chat_completion
import uuid

async def detect_meeting_request(message: str) -> dict:
    """Detect if message is a meeting request and extract details."""
    indicators = ["schedule", "meeting", "call", "discuss", "review"]
    if not any(ind in message.lower() for ind in indicators):
        return None
    
    prompt = f"""Analyze if this is a meeting request. If yes, extract details.

Message: {message}

Respond in this format ONLY:
IS_MEETING: yes/no
TITLE: [meeting title]
SUGGESTED_TIMES: [suggest 3 time slots in format "MM/DD HH:MM AM/PM"]
DURATION: [duration in minutes, default 30]

If not a meeting request, respond with "IS_MEETING: no"."""
    
    try:
        response = await chat_completion([{"role": "user", "content": prompt}])
        if "IS_MEETING: yes" in response:
            lines = response.strip().split("\n")
            result = {}
            for line in lines:
                if "TITLE:" in line:
                    result["title"] = line.split("TITLE:")[1].strip()
                elif "SUGGESTED_TIMES:" in line:
                    result["suggested_times"] = line.split("SUGGESTED_TIMES:")[1].strip()
                elif "DURATION:" in line:
                    try:
                        result["duration"] = int(line.split("DURATION:")[1].strip().split()[0])
                    except:
                        result["duration"] = 30
            return result if "title" in result else None
        return None
    except:
        return None

def generate_zoom_link() -> str:
    """Generate a mock Zoom link (in production, use Zoom API)."""
    meeting_id = ''.join([str(uuid.uuid4().int)[:9]])
    return f"https://zoom.us/j/{meeting_id}"
