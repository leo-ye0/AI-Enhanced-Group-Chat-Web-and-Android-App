from llm import chat_completion
from sqlalchemy import select
from db import Task, TaskStatus
import json

async def detect_task_action(session, message: str) -> dict:
    """Detect if user wants to complete or delete a task."""
    # Skip task assignment commands
    if message.strip().lower().startswith(("accept ", "decline ", "claim ")):
        return None
    
    # Get pending tasks
    tasks_res = await session.execute(select(Task).where(Task.status == TaskStatus.pending))
    tasks = tasks_res.scalars().all()
    
    if not tasks:
        return None
    
    task_list = "\n".join([f"{t.id}. {t.content}" for t in tasks])
    
    prompt = f"""Analyze if the user wants to complete or delete a task using natural language.

User message: "{message}"

Available tasks:
{task_list}

Return ONLY a JSON object:
{{"action": "complete|delete|none", "task_id": number}}

Rules:
- action: "complete" if user indicates task is done/finished/completed/cleared
  Examples: "done with X", "finished X", "X is complete", "cleared X", "X done"
- action: "delete" if user wants to remove/delete/cancel task
  Examples: "delete X", "remove X", "cancel X", "get rid of X"
- action: "none" if not a task action request
- task_id: match the task by finding keywords from the task content in the user message
- Be flexible with partial matches (e.g., "login" matches "Build login page")
"""
    
    try:
        response = await chat_completion([{"role": "user", "content": prompt}])
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            result = json.loads(response[json_start:json_end])
            if result.get("action") != "none":
                return result
        return None
    except:
        return None
