from llm import chat_completion

async def generate_summary(text: str, filename: str) -> str:
    """Generate a concise summary of the document text."""
    # Truncate text if too long (keep first 3000 chars for summary)
    truncated_text = text[:3000] if len(text) > 3000 else text
    
    messages = [{
        "role": "user",
        "content": f"Provide a concise summary of this document. Do not include any preamble like 'Here is a summary' or 'Here is a concise summary'. Just provide the summary directly:\n\n{truncated_text}\n\nSummary:"
    }]
    
    try:
        summary = await chat_completion(messages)
        # Remove common prefixes if LLM still includes them
        summary = summary.strip()
        prefixes = [
            "Here is a concise summary of the document:",
            "Here is a summary of the document:",
            "Here is a concise summary:",
            "Here is a summary:",
            "Here's a concise summary of the document:",
            "Here's a summary of the document:",
            "Here's a concise summary:",
            "Here's a summary:"
        ]
        for prefix in prefixes:
            if summary.startswith(prefix):
                summary = summary[len(prefix):].strip()
                break
        return summary
    except Exception as e:
        return f"Summary generation failed: {str(e)}"