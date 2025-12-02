from llm import chat_completion
from sqlalchemy import select, desc
from db import Message, UploadedFile, SessionLocal

async def analyze_project(timeline_info: str = None):
    """Analyze chat history and files to suggest project structure."""
    from conversation_chain import conversation_chain
    from db import Milestone, ProjectSettings
    
    async with SessionLocal() as session:
        # Get recent messages
        msg_res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(50))
        messages = list(reversed(msg_res.scalars().all()))
        
        # Get uploaded files
        file_res = await session.execute(select(UploadedFile))
        files = file_res.scalars().all()
        
        # Get milestones
        milestones_res = await session.execute(select(Milestone).order_by(Milestone.start_date))
        milestones = milestones_res.scalars().all()
        
        # Get ship date
        settings_res = await session.execute(select(ProjectSettings).limit(1))
        settings = settings_res.scalar_one_or_none()
        ship_date = settings.ship_date if settings else None
        
        # Build context
        chat_context = "\n".join([f"{m.content}" for m in messages if not m.is_bot])
        file_context = "\n".join([f"File: {f.filename}\nSummary: {f.summary}" for f in files])
        milestone_context = "\n".join([f"- {m.title}: {m.start_date} to {m.end_date}" for m in milestones])
        ship_context = f"Ship Date: {ship_date}" if ship_date else "No ship date set"
        
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
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            prompt = f"""Analyze this project based on chat history, uploaded documents, and current milestones.

Today's date: {current_date}

Chat History:
{chat_context[:2000]}

Uploaded Documents:
{file_context[:1000]}

Current Milestones:
{milestone_context}

{ship_context}

Provide a well-organized analysis:

📋 PROJECT ANALYSIS

🎯 Goal/Objective:
[Brief description based on chat/files]

🗓️ Current Milestones:
{milestone_context if milestone_context else "No milestones set - use /milestones to generate"}

📅 Ship Date: {ship_date if ship_date else "Not set"}

✅ Suggested Next Steps:
1. [Task with clear action]
2. [Task with clear action]
3. [Task with clear action]

⏱️ Timeline Analysis:
{"Based on ship date " + ship_date + " and starting from " + current_date + ", " if ship_date else "Starting from " + current_date + ", "}provide realistic timeline recommendations using actual future dates.

Use bullet points and emojis. Be concise and actionable."""
            
            response = await chat_completion([{"role": "user", "content": prompt}])
            # Add to conversation history for follow-up
            conversation_chain.add_to_history("user", "/project analyze")
            conversation_chain.add_to_history("assistant", response)
        
        return response.strip()

async def get_project_status():
    """Summarize current project progress from actual tasks and recent chat."""
    from db import Task, TaskStatus, Meeting, User, ProjectSettings
    from datetime import datetime
    
    async with SessionLocal() as session:
        # Get tasks from database
        task_res = await session.execute(select(Task).order_by(desc(Task.created_at)))
        tasks = task_res.scalars().all()
        
        # Get upcoming meetings only
        current_time = datetime.now().isoformat()
        meeting_res = await session.execute(
            select(Meeting).where(Meeting.datetime >= current_time).order_by(Meeting.datetime)
        )
        meetings = meeting_res.scalars().all()
        
        # Get recent messages for context
        msg_res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(20))
        messages = list(reversed(msg_res.scalars().all()))
        
        # Get project settings (ship date)
        settings_res = await session.execute(select(ProjectSettings).limit(1))
        settings = settings_res.scalar_one_or_none()
        
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
        
        meeting_context = "\nUPCOMING MEETINGS FROM DATABASE:\n"
        if meetings:
            for m in meetings:
                meeting_context += f"- {m.title} at {m.datetime} (attendees: {m.attendees or 'none'})\n"
        else:
            meeting_context += "No upcoming meetings\n"
        
        ship_date_context = "\nPROJECT SHIP DATE:\n"
        if settings and settings.ship_date:
            ship_date_context += f"Ship date: {settings.ship_date}\n"
        else:
            ship_date_context += "No ship date set\n"
        
        chat_context = "\nRECENT CHAT MESSAGES:\n"
        for m in messages[-10:]:
            if not m.is_bot:
                user = await session.get(User, m.user_id)
                username = user.username if user else "unknown"
                chat_context += f"{username}: {m.content[:100]}\n"
        
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""{task_context}{meeting_context}{ship_date_context}{chat_context}

CRITICAL INSTRUCTIONS:
- Today's date is {current_date}
- Use ONLY the information listed above
- Do NOT make up or hallucinate any tasks, meetings, or phases
- If there are no completed tasks, say "None"
- Summarize recent chat activity briefly if relevant
- When providing timeline analysis, use realistic dates starting from {current_date}

Provide a status report:

📋 PROJECT STATUS

✅ Completed:
[List ONLY completed tasks from database above, or "None"]

🔄 Pending Tasks:
[List ONLY pending tasks from database above, or "None"]

📅 Upcoming Meetings:
[List ONLY meetings from database above, or "None"]

🚢 Ship Date:
[Show ship date from database above, or "Not set"]

💬 Recent Activity:
[Brief 1-sentence summary of recent chat, or "None"]

🚫 Blockers:
[Mention only if explicitly stated in chat, otherwise "None"]
"""
        
        response = await chat_completion([{"role": "user", "content": prompt}])
        return response.strip()
