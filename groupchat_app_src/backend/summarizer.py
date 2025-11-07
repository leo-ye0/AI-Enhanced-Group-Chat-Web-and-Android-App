from llm import chat_completion

async def generate_summary(text: str, filename: str) -> str:
    """Generate a concise summary of the document text."""
    # Truncate text if too long (keep first 3000 chars for summary)
    truncated_text = text[:3000] if len(text) > 3000 else text
    
    messages = [{
        "role": "user",
        "content": f"Provide a concise summary of this document:\n\n{truncated_text}\n\nSummary:"
    }]
    
    try:
        summary = await chat_completion(messages)
        return summary.strip()
    except Exception as e:
        return f"Summary generation failed: {str(e)}"