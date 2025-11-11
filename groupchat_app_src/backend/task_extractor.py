from llm import chat_completion
import json

async def extract_tasks(message: str) -> list[dict]:
    """Extract actionable tasks with due dates and assignees from a message using AI."""
    # Quick check for task indicators
    indicators = ["need to", "should", "must", "todo", "task", "action:", "by ", "deadline", "assign", "due", "presentation", "report", "document"]
    if not any(ind in message.lower() for ind in indicators):
        return []
    
    prompt = f"""Extract tasks from this message. Look for:
- Task descriptions (what needs to be done)
- Assignees (who should do it)
- Due dates (when it's due)

Message: "{message}"

Return ONLY a JSON array like this:
[{{"task": "Complete Milestone2", "due_date": "2025-12-01", "assigned_to": "yutaoye"}}]

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
