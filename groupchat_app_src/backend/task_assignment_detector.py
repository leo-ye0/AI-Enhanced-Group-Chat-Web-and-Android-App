from llm import chat_completion
import json

async def detect_task_assignment(message: str) -> dict:
    """Detect if user wants to assign a task using natural language."""
    prompt = f"""Respond with ONLY JSON. No other text.

Message: "{message}"

Question: Is this a request for someone to do work or complete a task?

Answer TRUE if the message:
- Asks if anyone can do something ("Can anyone...", "Can someone...")
- Asks who can do something ("Who can...")
- Suggests someone should do something ("Someone should...", "We need to...")
- Requests work to be done ("Please...", "Could someone...")
- Asks for volunteers ("Anyone want to...")

Answer FALSE if:
- It's a question about information ("What is...", "How does...")
- It's a status check ("Is anyone working on...")
- It's just a statement without requesting action

JSON format:
{{"is_assignment": true/false, "task": "the work to do", "assignee": null}}

Examples:
"Can anyone work on paper finding?" = {{"is_assignment": true, "task": "work on paper finding", "assignee": null}}
"Who can review the code?" = {{"is_assignment": true, "task": "review the code", "assignee": null}}
"What is the deadline?" = {{"is_assignment": false, "task": "", "assignee": null}}

Your response (JSON only):
"""
    
    try:
        response = await chat_completion([{"role": "user", "content": prompt}])
        print(f"Task assignment LLM response: {response}")
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            result = json.loads(response[json_start:json_end])
            print(f"Parsed task assignment result: {result}")
            if result.get("is_assignment"):
                return result
        return None
    except Exception as e:
        print(f"Task assignment detection error: {e}")
        return None
