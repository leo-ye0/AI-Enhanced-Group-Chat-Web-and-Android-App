from llm import chat_completion

async def extract_tasks(message: str) -> list[str]:
    """Extract actionable tasks from a message using AI."""
    # Quick check for task indicators
    indicators = ["need to", "should", "must", "todo", "task:", "action:", "by ", "deadline"]
    if not any(ind in message.lower() for ind in indicators):
        return []
    
    prompt = f"""Extract actionable tasks from this message. Return ONLY task descriptions, one per line. If no tasks, return empty.

Message: {message}

Tasks:"""
    
    try:
        response = await chat_completion([{"role": "user", "content": prompt}])
        tasks = [line.strip() for line in response.strip().split("\n") if line.strip() and not line.strip().startswith("No tasks")]
        # Filter out non-task responses
        return [t.lstrip("- •*123456789.") for t in tasks if len(t) > 10][:3]  # Max 3 tasks per message
    except:
        return []
