from llm import chat_completion
from sqlalchemy import select, desc
from db import Message, UploadedFile, SessionLocal

async def analyze_project(timeline_info: str = None):
    """Analyze chat history and files to suggest project structure."""
    from conversation_chain import conversation_chain
    
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
        
        if timeline_info:
            # User provided timeline - use conversation chain to remember previous analysis
            prompt = f"""The user provided timeline info: {timeline_info}

Based on the previous project analysis and this timeline, create a detailed timeline with:
• Specific phases with start/end dates
• Key milestones and deadlines
• Task assignments if team size is mentioned
• Realistic estimates based on the timeframe

Format:

⏱️ TIMELINE ({timeline_info})

Week 1-2: [Phase name]
• [Milestone/task]
• [Milestone/task]

Week 3-4: [Phase name]
• [Milestone/task]
• [Milestone/task]

[Continue for full timeline]

Be specific and realistic."""
            response = await conversation_chain.get_response(prompt)
        else:
            # Initial analysis - store in conversation chain
            prompt = f"""Analyze this project based on chat history and uploaded documents.

Chat History:
{chat_context[:2000]}

Uploaded Documents:
{file_context[:1000]}

Provide a well-organized analysis:

📋 PROJECT ANALYSIS

🎯 Goal/Objective:
[Brief description based on chat/files]

🗓️ Key Phases:
• Phase 1: [Name] - [Description]
• Phase 2: [Name] - [Description]
• Phase 3: [Name] - [Description]

✅ Suggested Tasks:
1. [Task with clear action]
2. [Task with clear action]
3. [Task with clear action]

⏱️ Timeline:
To provide a realistic timeline, please reply with:
• How much time do you have? (e.g., "2 weeks", "1 month", "3 months")
• How many team members? (e.g., "3 people", "solo")

Example: "@bot /project analyze 2 weeks, 3 people"

Use bullet points and emojis. Be concise and actionable."""
            
            response = await chat_completion([{"role": "user", "content": prompt}])
            # Add to conversation history for follow-up
            conversation_chain.add_to_history("user", "/project analyze")
            conversation_chain.add_to_history("assistant", response)
        
        return response.strip()

async def get_project_status():
    """Summarize current project progress from actual tasks and recent chat."""
    from db import Task, TaskStatus, Meeting, User
    from datetime import datetime
    
    async with SessionLocal() as session:
        # Get tasks from database
        task_res = await session.execute(select(Task).order_by(desc(Task.created_at)))
        tasks = task_res.scalars().all()
        
        # Get meetings
        meeting_res = await session.execute(select(Meeting).order_by(Meeting.datetime))
        meetings = meeting_res.scalars().all()
        
        # Get recent messages for context
        msg_res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(20))
        messages = list(reversed(msg_res.scalars().all()))
        
        # Categorize tasks
        completed = [t for t in tasks if t.status == TaskStatus.completed]
        pending = [t for t in tasks if t.status == TaskStatus.pending]
        
        # Build context for LLM
        task_context = "ACTUAL TASKS FROM DATABASE:\n"
        task_context += "Completed Tasks:\n"
        for t in completed:
            task_context += f"- {t.content} (assigned: {t.assigned_to or 'none'})\n"
        task_context += "\nPending Tasks:\n"
        for t in pending:
            task_context += f"- {t.content} (assigned: {t.assigned_to or 'none'}, due: {t.due_date or 'none'})\n"
        
        meeting_context = "\nACTUAL MEETINGS FROM DATABASE:\n"
        for m in meetings:
            meeting_context += f"- {m.title} at {m.datetime} (attendees: {m.attendees or 'none'})\n"
        
        chat_context = "\nRECENT CHAT MESSAGES:\n"
        for m in messages[-10:]:
            if not m.is_bot:
                user = await session.get(User, m.user_id)
                username = user.username if user else "unknown"
                chat_context += f"{username}: {m.content[:100]}\n"
        
        prompt = f"""{task_context}{meeting_context}{chat_context}

CRITICAL INSTRUCTIONS:
- Use ONLY the information listed above
- Do NOT make up or hallucinate any tasks, meetings, or phases
- If there are no completed tasks, say "None"
- Summarize recent chat activity briefly if relevant

Provide a status report:

📋 PROJECT STATUS

✅ Completed:
[List ONLY completed tasks from database above, or "None"]

🔄 Pending Tasks:
[List ONLY pending tasks from database above, or "None"]

📅 Upcoming Meetings:
[List ONLY meetings from database above, or "None"]

💬 Recent Activity:
[Brief 1-sentence summary of recent chat, or "None"]

🚫 Blockers:
[Mention only if explicitly stated in chat, otherwise "None"]
"""
        
        response = await chat_completion([{"role": "user", "content": prompt}])
        return response.strip()
