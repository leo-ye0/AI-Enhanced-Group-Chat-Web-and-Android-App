from llm import chat_completion
import uuid
import json
import re
from datetime import datetime

async def detect_meeting_request(message: str) -> dict:
    """Detect if message is a meeting request and extract details including attendees."""
    # Extract Zoom link first using regex
    import re
    zoom_link = None
    zoom_match = re.search(r'https?://[^\s]+', message, re.IGNORECASE)
    if zoom_match:
        zoom_link = zoom_match.group(0)
    
    prompt = f"""Analyze if this is a CLEAR meeting scheduling request (not just mentioning meetings).

Message: "{message}"

Return ONLY a JSON object:
{{"is_meeting": true/false, "title": "extracted topic", "date": "YYYY-MM-DD", "time": "HH:MM", "duration": 60, "attendees": "username1,username2"}}

Rules:
- is_meeting: true ONLY if user is actively trying to SCHEDULE/ARRANGE a meeting (not just mentioning meetings)
- Examples of TRUE meeting requests: "let's schedule a meeting", "can we meet tomorrow", "schedule a call for 2pm", "Schedule team sync for Dec 15"
- Examples of FALSE (not meeting requests): "meeting request detected", "in the meeting", "after the meeting", "meeting notes"
- title: extract the ACTUAL meeting topic/purpose from the message (e.g., "team sync", "project review"). If no specific topic, use "Team Meeting"
- date: Convert to YYYY-MM-DD format. Current year is {datetime.now().year}. Examples: "Dec 15" → "2025-12-15", "tomorrow" → calculate date
- time: Convert to HH:MM 24-hour format. Examples: "2pm" → "14:00", "9:30am" → "09:30"
- duration: extract duration in minutes (e.g., "60 minutes" → 60)
- attendees: extract EXACT usernames as written (e.g., "alice bob" → "alice,bob"), NEVER include "bot" or "@bot"

If not a meeting scheduling request: {{"is_meeting": false}}

JSON:"""
    
    try:
        response = await chat_completion([{"role": "user", "content": prompt}])
        print(f"Raw LLM response: '{response}'")
        response = response.strip()
        if not response:
            print("Empty response from LLM")
            return None
        
        # Extract JSON from markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        # Extract only the JSON object (from { to })
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            response = response[start:end]
        
        response = response.strip()
        print(f"Cleaned JSON: '{response}'")
        result = json.loads(response)
        print(f"Meeting detection result: {result}")
        if result.get("is_meeting") and result.get("is_meeting") is not False:
            # Only set datetime if date is provided
            datetime_str = None
            if result.get("date") and result.get("date") != "null":
                time_str = result.get("time") or "14:00"
                datetime_str = f"{result['date']}T{time_str}"
            
            # Filter out 'bot' from attendees
            attendees = result.get("attendees")
            if attendees:
                exclude = {'bot', '@bot'}
                attendees_list = [a.strip() for a in attendees.split(',') if a.strip() not in exclude]
                attendees = ','.join(attendees_list) if attendees_list else None
            
            meeting_data = {
                "title": result.get("title", "Team Meeting"),
                "datetime": datetime_str,
                "duration": result.get("duration"),
                "attendees": attendees,
                "zoom_link": zoom_link,
                "suggested_times": result.get("suggested_times", "")
            }
            print(f"Returning meeting data: {meeting_data}")
            return meeting_data
        return None
    except Exception as e:
        print(f"Meeting detection error: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_zoom_link() -> str:
    """Generate a mock Zoom link (in production, use Zoom API)."""
    meeting_id = ''.join([str(uuid.uuid4().int)[:9]])
    return f"https://zoom.us/j/{meeting_id}"
