from llm import chat_completion
import json

async def extract_tasks(message: str) -> list[dict]:
    """Extract actionable tasks with due dates and assignees from a message using AI."""
    # Quick check for task indicators
    indicators = ["need to", "should", "must", "todo", "task", "action:", "by ", "deadline", "assign", "due", "presentation", "report", "document", "slide", "demo", "practice"]
    # Also check for pattern: "X to username" which suggests assignment
    has_to_pattern = " to " in message.lower() and any(c.isalpha() for c in message)
    if not any(ind in message.lower() for ind in indicators) and not has_to_pattern:
        return []
    
    prompt = f"""Extract NEW tasks from this message. Look for:
- Task descriptions (what needs to be done)
- Assignees (who should do it - extract exact usernames)
- Due dates (when it's due in YYYY-MM-DD format)

Message: "{message}"

IMPORTANT:
- If message has pattern "X to username(s)", treat X as the task and username(s) as assignees
- Examples: "presentation slide to leoye0" = task is "presentation slide", assigned to "leoye0"
- Examples: "demo to john and jane" = task is "demo", assigned to "john,jane"
- Extract exact usernames (e.g., "leoye0", "yutaoye") - comma-separated for multiple
- If multiple assignees mentioned with "and", combine them with commas
- Ignore messages that are just status updates without task details

Return ONLY a JSON array like this:
[{{"task": "presentation slide", "due_date": null, "assigned_to": "leoye0,yutaoye"}}]

If no tasks found, return: []

JSON:"""
    
    try:
        response = await chat_completion([{"role": "user", "content": prompt}])
        print(f"LLM raw response: {response}")
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        print(f"Cleaned response: {response}")
        
        tasks = json.loads(response)
        print(f"Parsed tasks: {tasks}")
        if not isinstance(tasks, list):
            return []
        filtered = [t for t in tasks if isinstance(t, dict) and t.get("task") and len(t.get("task", "")) > 10][:3]
        print(f"Filtered tasks: {filtered}")
        return filtered
    except Exception as e:
        print(f"Task extraction error: {e}")
        import traceback
        traceback.print_exc()
        return []
