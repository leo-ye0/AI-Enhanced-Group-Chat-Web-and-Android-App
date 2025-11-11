from llm import chat_completion
import uuid
import json
import re
from datetime import datetime

async def detect_meeting_request(message: str) -> dict:
    """Detect if message is a meeting request and extract details including attendees."""
    indicators = ["schedule", "meeting", "call", "discuss", "review", "meet"]
    if not any(ind in message.lower() for ind in indicators):
        return None
    
    prompt = f"""Extract meeting details from this message. Extract EXACT usernames as they appear.

Message: "{message}"

Return ONLY a JSON object:
{{"is_meeting": true, "title": "extracted topic", "date": "YYYY-MM-DD", "time": "HH:MM", "duration": 60, "attendees": "username1,username2"}}

Rules:
- is_meeting: true if this is a meeting/schedule request
- title: extract the ACTUAL meeting topic/purpose (NOT generic phrases like "schedule a meeting" or "schedule the meeting"). If no specific topic mentioned, use "Team Meeting"
- date: YYYY-MM-DD format (extract from message like "tomorrow", "next Monday", specific dates, null if not mentioned)
- time: HH:MM 24-hour format (extract from message like "2pm" = "14:00", null if not mentioned)
- duration: extract duration in minutes (null if not mentioned)
- attendees: extract EXACT usernames as written in message (e.g., "yutaoye", "leoye0", NOT "Yutao Ye" or "Leo"). NEVER include "bot" as an attendee.

CRITICAL: 
- Use lowercase usernames exactly as typed in the message, NOT real names or formatted names
- NEVER include "bot" in the attendees list
- For title, extract the PURPOSE/TOPIC of the meeting, NOT the action of scheduling
- Examples: "schedule a meeting to discuss project" -> title: "Project Discussion"
- Examples: "let's meet about the presentation" -> title: "Presentation Discussion"

If not a meeting request: {{"is_meeting": false}}

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
        if result.get("is_meeting"):
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
