from llm import chat_completion
from sqlalchemy import select, desc
from db import Message, UploadedFile, SessionLocal

async def analyze_project():
    """Analyze chat history and files to suggest project structure."""
    async with SessionLocal() as session:
        # Get recent messages
        msg_res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(50))
        messages = list(reversed(msg_res.scalars().all()))
        
        # Get uploaded files
        file_res = await session.execute(select(UploadedFile))
        files = file_res.scalars().all()
        
        # Build context
        chat_context = "\n".join([f"{m.content}" for m in messages if not m.is_bot])
        file_context = "\n".join([f"File: {f.filename}\nSummary: {f.summary}" for f in files])
        
        prompt = f"""Analyze this project based on chat history and uploaded documents.

Chat History:
{chat_context[:2000]}

Uploaded Documents:
{file_context[:1000]}

Provide a well-organized analysis with clear sections:

📋 PROJECT ANALYSIS

🎯 Goal/Objective:
[Brief description]

🗓️ Key Phases:
• Phase 1: [Name] - [Description]
• Phase 2: [Name] - [Description]
• Phase 3: [Name] - [Description]

✅ Suggested Tasks:
1. [Task with clear action]
2. [Task with clear action]
3. [Task with clear action]

⏱️ Timeline:
[Realistic estimate with breakdown]

Use bullet points, emojis, and clear formatting. Be concise and actionable."""
        
        response = await chat_completion([{"role": "user", "content": prompt}])
        return response.strip()

async def get_project_status():
    """Summarize current project progress from recent messages."""
    async with SessionLocal() as session:
        msg_res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(30))
        messages = list(reversed(msg_res.scalars().all()))
        
        chat_context = "\n".join([f"{m.content}" for m in messages])
        
        prompt = f"""Based on recent chat messages, summarize the current project status:

Recent Messages:
{chat_context[:2000]}

Provide a well-organized status update:

📋 PROJECT STATUS

✅ Completed:
• [Item 1]
• [Item 2]

🔄 In Progress:
• [Item 1]
• [Item 2]

⚠️ Needs Attention:
• [Item 1]
• [Item 2]

🚫 Blockers:
• [Issue 1] or "None"

Use bullet points and emojis. Be brief and specific."""
        
        response = await chat_completion([{"role": "user", "content": prompt}])
        return response.strip()
