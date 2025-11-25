import os
import asyncio
import time
import uuid
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from db import SessionLocal, init_db, User, Message, UploadedFile, Task, TaskStatus, Meeting, ProjectSettings, Decision, Milestone, ProjectSettings, DecisionLog, DecisionCategory, DecisionType, ActiveConflict, ConflictVote
from auth import get_password_hash, verify_password, create_access_token, get_current_user_token
from websocket_manager import ConnectionManager
from llm import chat_completion
from file_processor import extract_text_from_pdf, extract_text_from_docx, chunk_text
from vector_db import add_documents, search_documents, delete_documents_by_file_id, collection
from conversation_chain import conversation_chain, clear_conversation_history
from chat_compactor import compact_chat_history, should_compact_history
from summarizer import generate_summary
from migrations import run_migrations
from project_manager import analyze_project, get_project_status
from task_extractor import extract_tasks
from meeting_detector import detect_meeting_request, generate_zoom_link
from dialectic_engine import monitor_message_for_conflicts, process_vote_command, SocraticInterventionGenerator
from project_pulse import calculate_project_pulse
from milestone_suggester import suggest_milestones
from milestone_manager import detect_milestone_changes

load_dotenv()

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

app = FastAPI(title="OmniPal Chat")

# Allow same-origin and dev origins by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

# Duplicate prevention: track recent questions
recent_questions = {}

# Context tracking: remember when waiting for meeting info
waiting_for_meeting_info = {}

# --------- Schemas ---------
class AuthPayload(BaseModel):
    username: str
    password: str

class MessagePayload(BaseModel):
    content: str

# --------- Dependencies ---------
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

# --------- Utilities ---------
async def generate_and_update_summary(file_id: int, text: str, filename: str):
    """Generate summary and update database asynchronously."""
    try:
        print(f"Starting summary generation for file {file_id}: {filename}")
        summary = await generate_summary(text, filename)
        print(f"Summary generated for file {file_id}, length: {len(summary)}")
        
        async with SessionLocal() as session:
            file_obj = await session.get(UploadedFile, file_id)
            if file_obj:
                file_obj.summary = summary
                await session.commit()
                print(f"Summary saved to database for file {file_id}")
                await manager.broadcast({"type": "file_summary_updated", "file_id": file_id})
            else:
                print(f"File {file_id} not found in database")
    except Exception as e:
        print(f"Summary generation failed for file {file_id}: {e}")
        try:
            async with SessionLocal() as session:
                file_obj = await session.get(UploadedFile, file_id)
                if file_obj:
                    file_obj.summary = f"Summary generation failed: {str(e)}"
                    await session.commit()
                    await manager.broadcast({"type": "file_summary_updated", "file_id": file_id})
        except:
            pass

async def broadcast_message(session: AsyncSession, msg: Message):
    # Load username
    username = None
    if msg.user_id:
        u = await session.get(User, msg.user_id)
        username = u.username if u else "unknown"
    await manager.broadcast({
        "type": "message",
        "message": {
            "id": msg.id,
            "username": username if not msg.is_bot else "LLM Bot",
            "content": msg.content,
            "is_bot": msg.is_bot,
            "created_at": str(msg.created_at)
        }
    })

async def extract_and_save_tasks(session: AsyncSession, content: str, message_id: int) -> bool:
    """Extract and save tasks from a message. Returns True if tasks were added."""
    print(f"Extracting tasks from: {content}")
    tasks = await extract_tasks(content)
    print(f"Extracted {len(tasks)} tasks: {tasks}")
    if tasks:
        task_names = []
        for task_data in tasks:
            if isinstance(task_data, dict):
                task = Task(
                    content=task_data.get("task"),
                    extracted_from_message_id=message_id,
                    status=TaskStatus.pending,
                    due_date=task_data.get("due_date") if task_data.get("due_date") else None,
                    assigned_to=task_data.get("assigned_to") if task_data.get("assigned_to") else None
                )
                task_names.append(task.content)
                print(f"Created task: {task.content}, due: {task.due_date}, assigned: {task.assigned_to}")
            else:
                task = Task(content=task_data, extracted_from_message_id=message_id, status=TaskStatus.pending)
                task_names.append(task_data)
            session.add(task)
        await session.commit()
        await session.flush()
        print("Tasks committed to database")
        await manager.broadcast({"type": "tasks_updated"})
        print(f"Broadcast tasks_updated event to {len(manager.active_connections)} connections")
        
        # Send confirmation message
        if len(task_names) == 1:
            confirmation = f"✅ Added task: **{task_names[0]}**"
        else:
            confirmation = f"✅ Added {len(task_names)} tasks: " + ", ".join([f"**{t}**" for t in task_names])
        bot_msg = Message(user_id=None, content=confirmation, is_bot=True)
        session.add(bot_msg)
        await session.commit()
        await session.refresh(bot_msg)
        await broadcast_message(session, bot_msg)
        return True
    return False

async def detect_and_suggest_meeting(session: AsyncSession, content: str, user_id: int) -> bool:
    """Detect meeting requests and auto-create meeting with extracted details. Returns True if handled."""
    print(f"detect_and_suggest_meeting called with content: {content}")
    
    # Check if we're waiting for meeting info from this user
    if user_id in waiting_for_meeting_info:
        import re
        meeting_data = waiting_for_meeting_info[user_id]
        
        # Try to parse datetime
        datetime_match = re.search(r'(\d{4}-\d{2}-\d{2})[,\s]+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', content, re.IGNORECASE)
        if datetime_match and not meeting_data.get('datetime'):
            date_str = datetime_match.group(1)
            time_str = datetime_match.group(2).strip()
            
            # Convert 12-hour format to 24-hour format
            if 'pm' in time_str.lower() or 'am' in time_str.lower():
                is_pm = 'pm' in time_str.lower()
                time_str = time_str.lower().replace('pm', '').replace('am', '').strip()
                if ':' not in time_str:
                    time_str = f"{time_str}:00"
                hour, minute = time_str.split(':')
                hour = int(hour)
                if is_pm and hour != 12:
                    hour += 12
                elif not is_pm and hour == 12:
                    hour = 0
                time_str = f"{hour:02d}:{minute}"
            elif ':' not in time_str:
                time_str = f"{time_str}:00"
            
            meeting_data['datetime'] = f"{date_str}T{time_str}"
        
        # Try to parse zoom link FIRST and remove it from content
        content_without_url = content
        if not meeting_data.get('zoom_link'):
            zoom_match = re.search(r'https?://[^\s]+', content, re.IGNORECASE)
            if zoom_match:
                meeting_data['zoom_link'] = zoom_match.group(0)
                content_without_url = content.replace(zoom_match.group(0), '').strip()
        
        # Try to parse duration (e.g., "60 minutes", "1 hour", "30min")
        duration_match = re.search(r'(\d+)\s*(?:min|minute|minutes|hour|hours|hrs?)', content_without_url, re.IGNORECASE)
        if duration_match and not meeting_data.get('duration'):
            duration = int(duration_match.group(1))
            if 'hour' in content_without_url.lower() or 'hr' in content_without_url.lower():
                duration *= 60
            meeting_data['duration'] = duration
        
        # Try to parse meeting title
        if not meeting_data.get('title') or meeting_data.get('title') == 'Team Meeting':
            title_match = re.search(r'(?:meeting|call|discuss|review)\s+(?:about|for|on|regarding)?\s+([\w\s]+?)(?:\s+on|\s+at|\s+with|$)', content_without_url, re.IGNORECASE)
            if title_match:
                meeting_data['title'] = title_match.group(1).strip().title()
        
        # Try to parse attendees (usernames without @) from content WITHOUT URL
        if not meeting_data.get('attendees'):
            # Look for usernames (alphanumeric strings), exclude common words
            exclude = {'bot', 'the', 'and', 'with', 'for', 'meeting', 'schedule', 'minutes', 'hour', 'hours', 'min', 'duration'}
            usernames = [u for u in re.findall(r'\b([a-z][a-z0-9_]{2,})\b', content_without_url.lower()) if u not in exclude]
            if usernames:
                meeting_data['attendees'] = ','.join(usernames)
        
        # Check if we have all required info now
        has_title = meeting_data.get('title') and meeting_data.get('title') != 'Team Meeting'
        if has_title and meeting_data.get('datetime') and meeting_data.get('attendees') and meeting_data.get('duration') and meeting_data.get('zoom_link'):
            waiting_for_meeting_info.pop(user_id)
            
            # Create meeting
            meeting = Meeting(
                title=meeting_data.get('title', 'Team Meeting'),
                datetime=meeting_data.get('datetime'),
                duration_minutes=meeting_data.get('duration', 60),
                zoom_link=meeting_data.get('zoom_link'),
                attendees=meeting_data.get('attendees'),
                created_by=user_id
            )
            session.add(meeting)
            await session.commit()
            await session.refresh(meeting)
            
            await manager.broadcast({"type": "meetings_updated"})
            
            attendees_str = f" with {meeting.attendees}" if meeting.attendees else ""
            bot_msg = Message(
                user_id=None,
                content=f"✅ Meeting created: **{meeting.title}** on {meeting.datetime.split('T')[0]} at {meeting.datetime.split('T')[1]}{attendees_str}.",
                is_bot=True
            )
            session.add(bot_msg)
            await session.commit()
            await session.refresh(bot_msg)
            await broadcast_message(session, bot_msg)
            return True
        else:
            # Still missing some info
            missing = []
            if not meeting_data.get('title') or meeting_data.get('title') == 'Team Meeting':
                missing.append('meeting name/title')
            if not meeting_data.get('datetime'):
                missing.append('date/time (YYYY-MM-DD, HH:MM)')
            if not meeting_data.get('attendees'):
                missing.append('attendees (usernames)')
            if not meeting_data.get('duration'):
                missing.append('duration (minutes)')
            if not meeting_data.get('zoom_link'):
                missing.append('Zoom link (https://zoom.us/j/...)')
            
            waiting_for_meeting_info[user_id] = meeting_data
            missing_str = ', '.join(missing)
            bot_msg = Message(
                user_id=None,
                content=f"Missing: {missing_str}",
                is_bot=True
            )
            session.add(bot_msg)
            await session.commit()
            await session.refresh(bot_msg)
            await broadcast_message(session, bot_msg)
            return True
    
    meeting_info = await detect_meeting_request(content)
    print(f"Meeting info detected: {meeting_info}")
    if meeting_info:
        # Check what info is missing
        missing = []
        if not meeting_info.get("title") or meeting_info.get("title") == "Team Meeting":
            missing.append("meeting name/title")
        if not meeting_info.get("datetime"):
            missing.append("date/time (YYYY-MM-DD, HH:MM)")
        if not meeting_info.get("attendees"):
            missing.append("attendees (usernames)")
        if not meeting_info.get("duration"):
            missing.append("duration (minutes)")
        if not meeting_info.get("zoom_link"):
            missing.append("Zoom link (https://zoom.us/j/...)")
        
        if missing:
            # Store meeting info and wait for missing details
            waiting_for_meeting_info[user_id] = meeting_info
            missing_str = ", ".join(missing)
            bot_msg = Message(
                user_id=None,
                content=f"Meeting request detected. Missing: {missing_str}",
                is_bot=True
            )
            session.add(bot_msg)
            await session.commit()
            await session.refresh(bot_msg)
            await broadcast_message(session, bot_msg)
            return True
        
        # Create meeting with all provided info
        print(f"Creating meeting with datetime: {meeting_info.get('datetime')}")
        meeting = Meeting(
            title=meeting_info.get("title", "Team Meeting"),
            datetime=meeting_info.get("datetime"),
            duration_minutes=meeting_info.get("duration", 60),
            zoom_link=meeting_info.get("zoom_link"),
            attendees=meeting_info.get("attendees"),
            created_by=user_id
        )
        session.add(meeting)
        await session.commit()
        await session.refresh(meeting)
        print(f"✅ Meeting created in DB: ID={meeting.id}, title={meeting.title}, datetime={meeting.datetime}, attendees={meeting.attendees}")
        
        # Broadcast update FIRST
        await manager.broadcast({"type": "meetings_updated"})
        print("Broadcast meetings_updated event")
        
        # Send confirmation message
        attendees_str = f" with {meeting.attendees}" if meeting.attendees else ""
        bot_msg = Message(
            user_id=None,
            content=f"✅ Meeting created: **{meeting.title}** on {meeting.datetime.split('T')[0]} at {meeting.datetime.split('T')[1]}{attendees_str}.",
            is_bot=True
        )
        session.add(bot_msg)
        await session.commit()
        await session.refresh(bot_msg)
        await broadcast_message(session, bot_msg)
        return True
    return False

async def detect_and_set_ship_date(session: AsyncSession, content: str) -> bool:
    """Detect natural language ship date setting. Returns True if handled."""
    import re
    from datetime import datetime
    
    # Check for ship date patterns
    patterns = [
        r'set.*ship.*date.*to\s+(\d{4}-\d{2}-\d{2})',
        r'ship.*date.*is\s+(\d{4}-\d{2}-\d{2})',
        r'our.*ship.*date.*is\s+(\d{4}-\d{2}-\d{2})',
        r'project.*ship.*date.*is\s+(\d{4}-\d{2}-\d{2})',
        r'we.*ship.*on\s+(\d{4}-\d{2}-\d{2})',
        r'shipping.*on\s+(\d{4}-\d{2}-\d{2})',
        r'launch.*date.*is\s+(\d{4}-\d{2}-\d{2})',
        r'release.*date.*is\s+(\d{4}-\d{2}-\d{2})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            date_str = match.group(1)
            try:
                # Validate date format
                datetime.strptime(date_str, "%Y-%m-%d")
                
                # Get or create project settings
                settings_res = await session.execute(select(ProjectSettings).limit(1))
                settings = settings_res.scalar_one_or_none()
                if not settings:
                    settings = ProjectSettings(ship_date=date_str)
                    session.add(settings)
                else:
                    settings.ship_date = date_str
                await session.commit()
                
                # Send confirmation message
                bot_msg = Message(user_id=None, content=f"🚢 Ship date set to: **{date_str}**", is_bot=True)
                session.add(bot_msg)
                await session.commit()
                await session.refresh(bot_msg)
                await broadcast_message(session, bot_msg)
                
                # Broadcast ship date update to refresh frontend
                await manager.broadcast({"type": "ship_date_updated", "ship_date": date_str})
                return True
            except ValueError:
                continue
    
    return False

async def maybe_answer_with_llm(session: AsyncSession, content: str, message_id: int = None, user_id: int = None):
    # Check for milestone suggestion command, accept all, or requests for more stages
    if content.strip().lower() == "accept all":
        # Get current suggested milestones from recent bot message
        msgs_res = await session.execute(select(Message).where(Message.is_bot == True).order_by(desc(Message.created_at)).limit(5))
        recent_bot_messages = msgs_res.scalars().all()
        
        # Look for milestone suggestions in recent messages
        milestone_data = None
        for msg in recent_bot_messages:
            if "✨ Milestones Updated" in msg.content and "Ship Date:" in msg.content:
                # Parse milestones from the message
                lines = msg.content.split('\n')
                milestones = []
                for line in lines:
                    if line.strip() and line[0].isdigit() and '(' in line and ')' in line:
                        # Extract milestone info: "1. Planning (2025-11-21 to 2025-11-28)"
                        import re
                        match = re.match(r'\d+\. (.+?) \((.+?) to (.+?)\)', line.strip())
                        if match:
                            title, start_date, end_date = match.groups()
                            milestones.append({"title": title, "start_date": start_date, "end_date": end_date})
                
                if milestones:
                    milestone_data = milestones
                    break
        
        if milestone_data:
            # Clear existing milestones
            existing_res = await session.execute(select(Milestone))
            existing_milestones = existing_res.scalars().all()
            for m in existing_milestones:
                await session.delete(m)
            
            # Add new milestones
            for m_data in milestone_data:
                milestone = Milestone(
                    title=m_data["title"],
                    start_date=m_data["start_date"],
                    end_date=m_data["end_date"],
                    created_by=user_id
                )
                session.add(milestone)
            
            await session.commit()
            
            # Broadcast milestone update
            await manager.broadcast({"type": "milestones_updated"})
            
            # Send confirmation
            reply_text = f"✅ **Accepted all {len(milestone_data)} milestones!**\n\nMilestones added to project timeline."
        else:
            reply_text = "❌ No recent milestone suggestions found to accept. Use `/milestones` to generate new suggestions first."
    
    elif (content.strip().lower().startswith("/milestones") or 
        any(phrase in content.lower() for phrase in ["more stages", "more milestones", "add more", "need more phases"])):
        
        # Extract ship date or count if provided
        parts = content.strip().split(maxsplit=1) if content.startswith("/") else []
        extra_param = parts[1] if len(parts) > 1 else None
        ship_date = None
        milestone_count = 5  # default
        
        # Check for number in the message
        import re
        number_match = re.search(r'\b(\d+)\b', content)
        if number_match:
            milestone_count = int(number_match.group(1))
        
        if extra_param:
            # Check if it's a number (milestone count) or date
            if extra_param.isdigit():
                milestone_count = int(extra_param)
            elif '-' in extra_param:  # likely a date
                ship_date = extra_param
        
        # Save ship date if provided
        if ship_date:
            settings_res = await session.execute(select(ProjectSettings).limit(1))
            settings = settings_res.scalar_one_or_none()
            if not settings:
                settings = ProjectSettings(ship_date=ship_date)
                session.add(settings)
            else:
                settings.ship_date = ship_date
            await session.commit()
        
        # Get ship date from DB
        settings_res = await session.execute(select(ProjectSettings).limit(1))
        settings = settings_res.scalar_one_or_none()
        current_ship_date = settings.ship_date if settings else None
        
        # Get chat history
        msgs_res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(50))
        messages = list(reversed(msgs_res.scalars().all()))
        chat_history = "\n".join([f"{m.content}" for m in messages[-20:]])
        
        # Generate suggestions with count (don't save automatically)
        milestones = await suggest_milestones(chat_history, current_ship_date, milestone_count)
        
        # Generate reasoning for chat
        reasoning_prompt = f"""Based on the chat history and ship date {current_ship_date if current_ship_date else 'not specified'}, explain in 2-3 sentences why these milestones were chosen:

{', '.join([f"{m['title']} ({m['start_date']} to {m['end_date']})" for m in milestones])}

Provide a brief, practical explanation focusing on project flow and timeline considerations."""
        
        try:
            reasoning = await chat_completion([{"role": "user", "content": reasoning_prompt}])
        except:
            reasoning = "Milestones structured to provide clear project phases with adequate time for each stage."
        
        # Format response
        reply_text = f"✨ Milestones Updated\n\n"
        if current_ship_date:
            reply_text += f"📅 Ship Date: {current_ship_date}\n\n"
        
        for i, m in enumerate(milestones, 1):
            reply_text += f"{i}. {m['title']} ({m['start_date']} to {m['end_date']})\n"
        
        reply_text += f"\n🧠 Reasoning: {reasoning}\n\nReply **\"accept all\"** to add all milestones to your project."
        
        # Send bot response to chat
        bot_msg = Message(user_id=None, content=reply_text, is_bot=True)
        session.add(bot_msg)
        await session.commit()
        await session.refresh(bot_msg)
        await broadcast_message(session, bot_msg)
        
        # Broadcast milestone suggestions to frontend to trigger UI
        await manager.broadcast({"type": "milestones_suggested", "milestones": milestones, "ship_date": current_ship_date})
        
        return
    elif content.strip().lower().startswith("/project analyze"):
        # Extract timeline info if provided
        timeline_info = None
        if len(content.strip()) > len("/project analyze"):
            timeline_info = content.strip()[len("/project analyze"):].strip()
        reply_text = await analyze_project(timeline_info)
    elif content.strip().lower() == "/project status":
        reply_text = await get_project_status()
    elif content.strip().lower() == "/tasks":
        tasks_res = await session.execute(select(Task).where(Task.status == TaskStatus.pending).order_by(desc(Task.created_at)))
        tasks = tasks_res.scalars().all()
        if tasks:
            reply_text = "📋 Pending Tasks:\n" + "\n".join([f"{i+1}. {t.content}" for i, t in enumerate(tasks)])
        else:
            reply_text = "No pending tasks found."
    elif content.strip().lower().startswith("/vote "):
        # Parse /vote command: /vote Should we use Method A or B?
        vote_question = content.strip()[6:].strip()
        if not vote_question:
            reply_text = "Usage: `/vote [your question]` - Example: `/vote Should we use Method A or B?`"
        else:
            # Create manual vote
            from datetime import datetime, timedelta
            from db import ActiveConflict, ConflictSeverity
            import uuid
            
            conflict_id = f"V{str(uuid.uuid4())[:8].upper()}"
            expires_at = datetime.now() + timedelta(hours=24)
            
            active_conflict = ActiveConflict(
                conflict_id=conflict_id,
                user_statement=vote_question,
                conflicting_evidence="Manual team vote",
                source_file="Team Decision",
                severity=ConflictSeverity.medium,
                reason=vote_question,
                expires_at=expires_at
            )
            
            session.add(active_conflict)
            await session.commit()
            
            reply_text = f"🗳️ **TEAM VOTE STARTED** - {conflict_id}\n\n**Question:** {vote_question}\n\n**Options:**\n**A:** Yes/Approve\n**B:** No/Reject\n**C:** Alternative/Modify\n\nVote with: `@bot decision {conflict_id} A/B/C [your reasoning]`"
            
            # Broadcast new vote
            await manager.broadcast({"type": "new_conflict", "conflict_id": conflict_id})
    elif content.strip().lower() == "/decisions":
        from db import DecisionLog
        decisions_res = await session.execute(select(DecisionLog).order_by(desc(DecisionLog.created_at)).limit(10))
        decisions = decisions_res.scalars().all()
        if decisions:
            reply_text = "📋 Recent Decisions:\n\n" + "\n\n".join([
                f"**{d.decision_text}**\n{d.rationale}\n*{d.created_by} • {d.created_at.strftime('%m/%d %H:%M')}*"
                for d in decisions
            ])
        else:
            reply_text = "No decisions recorded yet."
    elif content.strip().lower() == "/assign":
        tasks_res = await session.execute(select(Task).where(Task.status == TaskStatus.pending, Task.assigned_to == None).order_by(desc(Task.created_at)).limit(1))
        task = tasks_res.scalar_one_or_none()
        if task:
            await manager.broadcast({"type": "open_assign_modal", "task_id": task.id})
        else:
            reply_text = "No unassigned tasks found."
        return
    elif content.strip().lower() == "/schedule":
        await manager.broadcast({"type": "open_meeting_modal"})
        return
    elif content.strip().lower().startswith("/ship date"):
        # Extract date if provided
        date_part = content.strip()[len("/ship date"):].strip()
        if date_part:
            # Set ship date
            try:
                from datetime import datetime
                # Validate date format
                datetime.strptime(date_part, "%Y-%m-%d")
                
                # Get or create project settings
                settings_res = await session.execute(select(ProjectSettings).limit(1))
                settings = settings_res.scalar_one_or_none()
                if not settings:
                    settings = ProjectSettings(ship_date=date_part)
                    session.add(settings)
                else:
                    settings.ship_date = date_part
                await session.commit()
                reply_text = f"🚢 Ship date set to: **{date_part}**"
                
                # Broadcast ship date update to refresh frontend
                await manager.broadcast({"type": "ship_date_updated", "ship_date": date_part})
            except ValueError:
                reply_text = "❌ Invalid date format. Use YYYY-MM-DD (e.g., 2024-12-15)"
        else:
            # Get current ship date
            settings_res = await session.execute(select(ProjectSettings).limit(1))
            settings = settings_res.scalar_one_or_none()
            if settings and settings.ship_date:
                reply_text = f"🚢 Current ship date: **{settings.ship_date}**"
            else:
                reply_text = "🚢 No ship date set. Use `/ship date YYYY-MM-DD` to set it."

    elif any(kw in content.lower() for kw in ["what decisions", "decisions made", "team decisions", "what did we decide"]):
        from db import DecisionLog
        decisions_res = await session.execute(select(DecisionLog).order_by(desc(DecisionLog.created_at)).limit(5))
        decisions = decisions_res.scalars().all()
        if decisions:
            reply_text = "📋 **Recent Team Decisions:**\n\n" + "\n\n".join([
                f"• **{d.decision_text}**\n  {d.rationale}\n  *{d.created_by} • {d.created_at.strftime('%m/%d %H:%M')}*"
                for d in decisions
            ])
        else:
            reply_text = "No team decisions have been recorded yet."
    else:
        # Duplicate prevention
        message_key = content.strip().lower()
        current_time = time.time()
        
        for key, timestamp in list(recent_questions.items()):
            if current_time - timestamp > 10:
                del recent_questions[key]
        
        if message_key in recent_questions and current_time - recent_questions[message_key] < 5:
            return
        
        recent_questions[message_key] = current_time
        
        try:
            reply_text = await conversation_chain.get_response(content)
            
            # Check if response is a vote request
            if reply_text.startswith("__VOTE_REQUEST__"):
                vote_question = reply_text.replace("__VOTE_REQUEST__", "")
                
                # Create manual vote (same logic as /vote command)
                from datetime import datetime, timedelta
                from db import ActiveConflict, ConflictSeverity
                import uuid
                
                conflict_id = f"V{str(uuid.uuid4())[:8].upper()}"
                expires_at = datetime.now() + timedelta(hours=24)
                
                active_conflict = ActiveConflict(
                    conflict_id=conflict_id,
                    user_statement=vote_question,
                    conflicting_evidence="Manual team vote",
                    source_file="Team Decision",
                    severity=ConflictSeverity.medium,
                    reason=vote_question,
                    expires_at=expires_at
                )
                
                session.add(active_conflict)
                await session.commit()
                
                reply_text = f"🗳️ **TEAM VOTE STARTED** - {conflict_id}\n\n**Question:** {vote_question}\n\n**Options:**\n**A:** Yes/Approve\n**B:** No/Reject\n**C:** Alternative/Modify\n\nVote with: `@bot decision {conflict_id} A/B/C [your reasoning]`"
                
                # Broadcast new vote
                await manager.broadcast({"type": "new_conflict", "conflict_id": conflict_id})
            
            # Check if response is a milestone request
            elif reply_text.startswith("__MILESTONE_REQUEST__"):
                # Get ship date from DB
                settings_res = await session.execute(select(ProjectSettings).limit(1))
                settings = settings_res.scalar_one_or_none()
                current_ship_date = settings.ship_date if settings else None
                
                # Get chat history
                msgs_res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(50))
                messages = list(reversed(msgs_res.scalars().all()))
                chat_history = "\n".join([f"{m.content}" for m in messages[-20:]])
                
                # Generate milestone suggestions
                milestones = await suggest_milestones(chat_history, current_ship_date, 5)
                
                # Generate reasoning
                reasoning_prompt = f"""Based on the chat history and ship date {current_ship_date if current_ship_date else 'not specified'}, explain in 2-3 sentences why these milestones were chosen:

{', '.join([f"{m['title']} ({m['start_date']} to {m['end_date']})" for m in milestones])}

Provide a brief, practical explanation focusing on project flow and timeline considerations."""
                
                try:
                    reasoning = await chat_completion([{"role": "user", "content": reasoning_prompt}])
                except:
                    reasoning = "Milestones structured to provide clear project phases with adequate time for each stage."
                
                # Format response
                reply_text = f"✨ **Milestone Suggestions**\n\n"
                if current_ship_date:
                    reply_text += f"📅 Ship Date: {current_ship_date}\n\n"
                
                for i, m in enumerate(milestones, 1):
                    reply_text += f"{i}. {m['title']} ({m['start_date']} to {m['end_date']})\n"
                
                reply_text += f"\n🧠 Reasoning: {reasoning}\n\nReply **\"accept all\"** to add all milestones to your project."
                
                # Broadcast milestone suggestions to frontend
                await manager.broadcast({"type": "milestones_suggested", "milestones": milestones, "ship_date": current_ship_date})
            
            # Check if response is a task request
            elif reply_text.startswith("__TASK_REQUEST__"):
                reply_text = "I can help you create tasks! Just describe what needs to be done and I'll extract tasks automatically. For example: 'We need to review the code by Friday and test the API endpoints.'"
            
            # Check if response is a meeting request
            elif reply_text.startswith("__MEETING_REQUEST__"):
                reply_text = "I can help you schedule a meeting! Please provide: meeting title, date/time (YYYY-MM-DD HH:MM), duration in minutes, attendees, and Zoom link if available."
            
            # Check if response is a status request
            elif reply_text.startswith("__STATUS_REQUEST__"):
                # Get project status
                reply_text = await get_project_status()
                
        except Exception as e:
            reply_text = f"(LLM error) {e}"
    
    bot_msg = Message(user_id=None, content=reply_text, is_bot=True)
    session.add(bot_msg)
    await session.commit()
    await session.refresh(bot_msg)
    await broadcast_message(session, bot_msg)

# --------- Routes ---------
@app.on_event("startup")
async def on_startup():
    await init_db()
    await run_migrations()

@app.post("/api/signup")
async def signup(payload: AuthPayload, session: AsyncSession = Depends(get_db)):
    # check unique username
    existing = await session.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")
    u = User(username=payload.username, password_hash=get_password_hash(payload.password))
    session.add(u)
    await session.commit()
    token = create_access_token({"sub": u.username})
    return {"ok": True, "token": token}

async def generate_login_summary(username: str, session: AsyncSession) -> str:
    """Generate personalized summary for user on login."""
    # Get recent messages
    msgs_res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(20))
    messages = list(reversed(msgs_res.scalars().all()))
    
    # Get user's pending tasks
    tasks_res = await session.execute(
        select(Task).where(
            Task.status == TaskStatus.pending,
            Task.assigned_to.like(f"%{username}%")
        ).order_by(Task.due_date)
    )
    user_tasks = tasks_res.scalars().all()
    
    # Get upcoming meetings
    from datetime import datetime
    meetings_res = await session.execute(
        select(Meeting).where(Meeting.datetime >= datetime.now().isoformat()).order_by(Meeting.datetime).limit(3)
    )
    meetings = meetings_res.scalars().all()
    
    # If no tasks, meetings, or recent messages, return simple welcome
    if not user_tasks and not meetings and not messages:
        return f"Welcome back, {username}!"
    
    # Build context
    context = f"User {username} just logged in. Provide a brief welcome summary.\n\n"
    
    if messages:
        context += "Recent chat (last 20 messages):\n"
        for m in messages[-10:]:
            if m.is_bot:
                context += f"Bot: {m.content[:100]}...\n"
            else:
                user_res = await session.get(User, m.user_id)
                uname = user_res.username if user_res else "unknown"
                context += f"{uname}: {m.content[:100]}...\n"
    
    if user_tasks:
        context += f"\n{username}'s pending tasks:\n"
        for t in user_tasks:
            context += f"- {t.content} (due: {t.due_date or 'no date'})\n"
    
    if meetings:
        context += "\nUpcoming meetings:\n"
        for m in meetings:
            context += f"- {m.title} at {m.datetime}\n"
    
    prompt = f"{context}\n\nProvide ONLY a brief, friendly welcome message (1-2 sentences) summarizing ONLY the actual items listed above. If there are no tasks or meetings for {username}, just mention the recent chat activity. Do not make up or hallucinate any notifications. Do not include any prefix like 'Here's a message' or 'Welcome message:'. Start directly with the greeting."
    
    try:
        summary = await chat_completion([{"role": "user", "content": prompt}])
        return summary
    except:
        return f"Welcome back, {username}!"

@app.post("/api/login")
async def login(payload: AuthPayload, session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(User).where(User.username == payload.username))
    u = res.scalar_one_or_none()
    if not u or not verify_password(payload.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": u.username})
    
    # Generate login summary asynchronously
    async def send_summary():
        await asyncio.sleep(1)  # Wait for WebSocket connection
        async with SessionLocal() as new_session:
            summary = await generate_login_summary(payload.username, new_session)
            # Remove any prefix like "Here's a brief welcome message for username:"
            import re
            summary = re.sub(r'^.*?welcome message.*?:\s*["\']?', '', summary, flags=re.IGNORECASE).strip('"\'')
            bot_msg = Message(user_id=None, content=f"👋 {summary}", is_bot=True)
            new_session.add(bot_msg)
            await new_session.commit()
            await new_session.refresh(bot_msg)
            await broadcast_message(new_session, bot_msg)
    
    asyncio.create_task(send_summary())
    return {"ok": True, "token": token}

@app.get("/api/messages")
async def get_messages(limit: int = 50, session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(limit))
    items = list(reversed(res.scalars().all()))
    out = []
    for m in items:
        username = None
        if not m.is_bot and m.user_id:
            u = await session.get(User, m.user_id)
            username = u.username if u else "unknown"
        out.append({
            "id": m.id,
            "username": "LLM Bot" if m.is_bot else (username or "unknown"),
            "content": m.content,
            "is_bot": m.is_bot,
            "created_at": str(m.created_at)
        })
    return {"messages": out}

@app.post("/api/messages")
async def post_message(payload: MessagePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Check if chat history needs compacting
    if await should_compact_history():
        compact_result = await compact_chat_history()
        if compact_result:
            await manager.broadcast({"type": "history_compacted", "message": compact_result})
    
    m = Message(user_id=u.id, content=payload.content, is_bot=False)
    session.add(m)
    await session.commit()
    await session.refresh(m)
    await broadcast_message(session, m)
    
    # DIALECTIC ENGINE: Check for decision responses FIRST
    if "@bot decision" in payload.content.lower():
        decision_response = await process_vote_command(payload.content, u.id, session)
        if decision_response:
            bot_msg = Message(user_id=None, content=decision_response, is_bot=True)
            session.add(bot_msg)
            await session.commit()
            await session.refresh(bot_msg)
            await broadcast_message(session, bot_msg)
            # Broadcast voting update to decision bar
            await manager.broadcast({"type": "voting_updated"})
            return {"ok": True, "id": m.id}
    
    # DIALECTIC ENGINE: Silent monitoring for conflicts
    conflict_data = await monitor_message_for_conflicts(payload.content, m.id, session)
    if conflict_data:
        bot_msg = Message(user_id=None, content=conflict_data['intervention_message'], is_bot=True)
        session.add(bot_msg)
        await session.commit()
        await session.refresh(bot_msg)
        await broadcast_message(session, bot_msg)
        # Broadcast new conflict to decision bar
        await manager.broadcast({"type": "new_conflict", "conflict_id": conflict_data['conflict_id']})
        return {"ok": True, "id": m.id}
    
    # Check if bot should respond (commands, @bot mentions, or decision questions)
    decision_keywords = ["what decisions", "decisions made", "team decisions", "what did we decide"]
    should_respond = (
        payload.content.startswith("/") or 
        "@bot" in payload.content.lower() or
        any(kw in payload.content.lower() for kw in decision_keywords)
    )
    
    # Always detect meetings, milestones, and ship date from non-command messages FIRST
    meeting_handled = False
    milestone_handled = False
    ship_date_handled = False
    if not payload.content.startswith("/"):
        meeting_handled = await detect_and_suggest_meeting(session, payload.content, u.id)
        milestone_response = await detect_milestone_changes(payload.content, u.id)
        if milestone_response:
            milestone_handled = True
            bot_msg = Message(user_id=None, content=milestone_response, is_bot=True)
            session.add(bot_msg)
            await session.commit()
            await session.refresh(bot_msg)
            await broadcast_message(session, bot_msg)
        # Only detect ship date if NOT mentioning @bot (to avoid interfering with bot requests)
        if "@bot" not in payload.content.lower():
            ship_date_handled = await detect_and_set_ship_date(session, payload.content)
    
    if should_respond and not meeting_handled and not milestone_handled and not ship_date_handled:
        # Add user message to conversation history (skip commands)
        if not payload.content.startswith("/"):
            conversation_chain.add_to_history("user", payload.content)
        
        # fire-and-forget LLM answer with fresh session
        async def llm_task():
            async with SessionLocal() as new_session:
                await maybe_answer_with_llm(new_session, payload.content, m.id, u.id)
        asyncio.create_task(llm_task())
    
    return {"ok": True, "id": m.id}

@app.delete("/api/messages")
async def clear_messages(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    from sqlalchemy import delete
    await session.execute(delete(Message))
    await session.commit()
    clear_conversation_history()  # Clear AI conversation memory
    await manager.broadcast({"type": "clear"})
    return {"ok": True}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    # Validate file type
    if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported")
    
    # Get user
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Read file content
    content = await file.read()
    
    # Extract text based on file type
    if file.filename.lower().endswith('.pdf'):
        text = extract_text_from_pdf(content)
    elif file.filename.lower().endswith('.docx'):
        text = extract_text_from_docx(content)
    else:  # .txt file
        text = content.decode('utf-8')
    
    # Chunk the text
    chunks = chunk_text(text)
    
    # Generate IDs and metadata
    file_id = str(uuid.uuid4())
    ids = [f"{file_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"filename": file.filename, "username": username, "chunk_id": i} for i in range(len(chunks))]
    
    # Store in vector database
    add_documents(chunks, metadatas, ids)
    
    # Store file metadata and base64 encoded data in database
    import base64
    uploaded_file = UploadedFile(
        filename=file.filename,
        file_id=file_id,
        user_id=u.id,
        content=text,
        file_data=base64.b64encode(content).decode('utf-8'),
        summary="Generating summary..."
    )
    session.add(uploaded_file)
    await session.commit()
    await session.refresh(uploaded_file)
    
    # Generate summary asynchronously
    asyncio.create_task(generate_and_update_summary(uploaded_file.id, text, file.filename))
    
    return {"ok": True, "filename": file.filename, "chunks": len(chunks)}

@app.get("/api/files")
async def get_files(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    # Verify user is authenticated
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Get ALL files from ALL users (group chat)
    files_res = await session.execute(
        select(UploadedFile).order_by(desc(UploadedFile.created_at))
    )
    files = files_res.scalars().all()
    
    files_with_users = []
    for f in files:
        user_obj = await session.get(User, f.user_id)
        uploader_username = user_obj.username if user_obj else "unknown"
        files_with_users.append({
            "id": f.id,
            "filename": f.filename,
            "file_id": f.file_id,
            "summary": f.summary or "No summary available",
            "username": uploader_username,
            "created_at": str(f.created_at)
        })
    
    return {"files": files_with_users}

@app.delete("/api/files/delete/{file_id}")
async def delete_file(file_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Get file to delete (allow any user to delete any file in group chat)
    file_res = await session.execute(
        select(UploadedFile).where(UploadedFile.id == file_id)
    )
    file_obj = file_res.scalar_one_or_none()
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete from vector database
    delete_documents_by_file_id(file_obj.file_id)
    
    # Delete from database
    await session.delete(file_obj)
    await session.commit()
    
    return {"ok": True}

@app.get("/api/debug/vector-db")
async def debug_vector_db():
    """Debug endpoint to check vector database contents"""
    try:
        from vector_db import collection
        results = collection.get()
        docs_with_rag = []
        for i, doc in enumerate(results.get('documents', [])):
            if any(term in doc.lower() for term in ['rag', 'retrieval', 'augmented', 'generation']):
                docs_with_rag.append({"index": i, "preview": doc[:200]})
        return {
            "total_documents": len(results.get('documents', [])),
            "rag_documents": docs_with_rag[:5],
            "sample_search": search_documents("RAG", n_results=3)
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/files/{file_id}/download")
async def download_file(file_id: int, token: str, session: AsyncSession = Depends(get_db)):
    from auth import decode_access_token
    from fastapi.responses import Response
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    file_res = await session.execute(
        select(UploadedFile).where(UploadedFile.id == file_id, UploadedFile.user_id == u.id)
    )
    file_obj = file_res.scalar_one_or_none()
    if not file_obj or not file_obj.file_data:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Decode base64 data
    import base64
    file_content = base64.b64decode(file_obj.file_data)
    
    # Determine content type
    content_type = "application/octet-stream"
    if file_obj.filename.lower().endswith('.pdf'):
        content_type = "application/pdf"
    elif file_obj.filename.lower().endswith('.txt'):
        content_type = "text/plain"
    elif file_obj.filename.lower().endswith('.docx'):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    return Response(
        content=file_content,
        media_type=content_type,
        headers={"Content-Disposition": f"inline; filename={file_obj.filename}"}
    )

@app.get("/api/tasks")
async def get_tasks(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    tasks_res = await session.execute(select(Task).order_by(desc(Task.created_at)))
    tasks = tasks_res.scalars().all()
    result = []
    for t in tasks:
        result.append({"id": t.id, "content": t.content, "status": t.status.value, "assigned_to": t.assigned_to, "due_date": t.due_date, "created_at": str(t.created_at)})
    return {"tasks": result}

class DueDatePayload(BaseModel):
    due_date: str

@app.patch("/api/tasks/{task_id}/due-date")
async def set_due_date(task_id: int, payload: DueDatePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.due_date = payload.due_date
    await session.commit()
    await manager.broadcast({"type": "tasks_updated"})
    return {"ok": True}

@app.get("/api/users")
async def get_users(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    users_res = await session.execute(select(User))
    users = users_res.scalars().all()
    return {"users": [{"username": u.username} for u in users]}

@app.patch("/api/tasks/{task_id}/complete")
async def complete_task(task_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = TaskStatus.completed
    await session.commit()
    return {"ok": True}

@app.post("/api/tasks")
async def create_task(payload: MessagePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    task = Task(content=payload.content, status=TaskStatus.pending)
    session.add(task)
    await session.commit()
    await manager.broadcast({"type": "tasks_updated"})
    return {"ok": True}

class AssignPayload(BaseModel):
    usernames: str

@app.patch("/api/tasks/{task_id}/assign")
async def assign_task(task_id: int, payload: AssignPayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.assigned_to = payload.usernames
    await session.commit()
    await manager.broadcast({"type": "tasks_updated"})
    return {"ok": True}

@app.patch("/api/tasks/{task_id}/content")
async def update_task_content(task_id: int, payload: MessagePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.content = payload.content
    await session.commit()
    await manager.broadcast({"type": "tasks_updated"})
    return {"ok": True}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await session.delete(task)
    await session.commit()
    await manager.broadcast({"type": "tasks_updated"})
    return {"ok": True}

class MeetingPayload(BaseModel):
    title: str
    datetime: str
    duration_minutes: int
    zoom_link: Optional[str] = None

@app.post("/api/meetings")
async def create_meeting(payload: MeetingPayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    zoom_link = payload.zoom_link if payload.zoom_link else "No Zoom link provided"
    meeting = Meeting(
        title=payload.title,
        datetime=payload.datetime,
        duration_minutes=payload.duration_minutes,
        zoom_link=zoom_link,
        created_by=u.id
    )
    session.add(meeting)
    await session.commit()
    await session.refresh(meeting)
    await manager.broadcast({"type": "meetings_updated"})
    return {"ok": True, "zoom_link": zoom_link, "id": meeting.id}

@app.post("/api/meetings/{meeting_id}/transcript")
async def upload_transcript(meeting_id: int, file: UploadFile = File(...), username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    if not file.filename.lower().endswith(('.txt', '.vtt', '.srt')):
        raise HTTPException(status_code=400, detail="Only TXT, VTT, and SRT transcript files supported")
    
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    content = await file.read()
    text = content.decode('utf-8')
    chunks = chunk_text(text)
    file_id = str(uuid.uuid4())
    ids = [f"{file_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"filename": file.filename, "username": username, "chunk_id": i, "meeting_id": meeting_id} for i in range(len(chunks))]
    add_documents(chunks, metadatas, ids)
    
    import base64
    uploaded_file = UploadedFile(
        filename=file.filename,
        file_id=file_id,
        user_id=u.id,
        content=text,
        file_data=base64.b64encode(content).decode('utf-8'),
        summary="Transcript uploaded"
    )
    session.add(uploaded_file)
    await session.commit()
    await session.refresh(uploaded_file)
    
    meeting.transcript_file_id = uploaded_file.id
    await session.commit()
    await manager.broadcast({"type": "meetings_updated"})
    return {"ok": True}

@app.get("/api/meetings")
async def get_meetings(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    meetings_res = await session.execute(select(Meeting).order_by(desc(Meeting.created_at)))
    meetings = meetings_res.scalars().all()
    result = []
    for m in meetings:
        transcript_filename = None
        if m.transcript_file_id:
            tf = await session.get(UploadedFile, m.transcript_file_id)
            transcript_filename = tf.filename if tf else None
        result.append({"id": m.id, "title": m.title, "datetime": m.datetime, "duration_minutes": m.duration_minutes, "zoom_link": m.zoom_link, "transcript_filename": transcript_filename, "attendees": m.attendees, "created_at": str(m.created_at)})
    return {"meetings": result}

@app.patch("/api/meetings/{meeting_id}/attendees")
async def set_attendees(meeting_id: int, payload: AssignPayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting.attendees = payload.usernames
    await session.commit()
    await manager.broadcast({"type": "meetings_updated"})
    return {"ok": True}

class DurationPayload(BaseModel):
    duration_minutes: int

@app.patch("/api/meetings/{meeting_id}/duration")
async def set_duration(meeting_id: int, payload: DurationPayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting.duration_minutes = payload.duration_minutes
    await session.commit()
    await manager.broadcast({"type": "meetings_updated"})
    return {"ok": True}

class MeetingTitlePayload(BaseModel):
    title: str

@app.patch("/api/meetings/{meeting_id}/title")
async def update_meeting_title(meeting_id: int, payload: MeetingTitlePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting.title = payload.title
    await session.commit()
    await manager.broadcast({"type": "meetings_updated"})
    return {"ok": True}

class MeetingDatetimePayload(BaseModel):
    datetime: str

@app.patch("/api/meetings/{meeting_id}/datetime")
async def update_meeting_datetime(meeting_id: int, payload: MeetingDatetimePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting.datetime = payload.datetime
    await session.commit()
    await manager.broadcast({"type": "meetings_updated"})
    return {"ok": True}

class ZoomLinkPayload(BaseModel):
    zoom_link: str

@app.patch("/api/meetings/{meeting_id}/zoom-link")
async def update_zoom_link(meeting_id: int, payload: ZoomLinkPayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting.zoom_link = payload.zoom_link
    await session.commit()
    await manager.broadcast({"type": "meetings_updated"})
    return {"ok": True}

@app.delete("/api/meetings/{meeting_id}")
async def delete_meeting(meeting_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await session.delete(meeting)
    await session.commit()
    await manager.broadcast({"type": "meetings_updated"})
    return {"ok": True}

# --------- Milestones Routes ---------
@app.post("/api/milestones/suggest")
async def suggest_project_milestones(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """LLM suggests milestones based on chat history and ship date."""
    # Get ship date
    settings_res = await session.execute(select(ProjectSettings).limit(1))
    settings = settings_res.scalar_one_or_none()
    ship_date = settings.ship_date if settings else None
    
    # Get recent messages for context
    msgs_res = await session.execute(select(Message).order_by(desc(Message.created_at)).limit(50))
    messages = list(reversed(msgs_res.scalars().all()))
    
    chat_history = "\n".join([f"{m.content}" for m in messages[-20:]])
    milestones = await suggest_milestones(chat_history, ship_date, 5)
    
    return {"milestones": milestones, "ship_date": ship_date}

class MilestonePayload(BaseModel):
    title: str
    start_date: str
    end_date: str

@app.post("/api/milestones/bulk")
async def bulk_accept_milestones(milestones: List[MilestonePayload], username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Accept multiple milestones at once."""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Clear existing milestones
    existing_res = await session.execute(select(Milestone))
    for m in existing_res.scalars().all():
        await session.delete(m)
    
    # Add new milestones
    for m_data in milestones:
        milestone = Milestone(
            title=m_data.title,
            start_date=m_data.start_date,
            end_date=m_data.end_date,
            created_by=u.id
        )
        session.add(milestone)
    
    await session.commit()
    await manager.broadcast({"type": "milestones_updated"})
    return {"ok": True, "count": len(milestones)}

@app.post("/api/milestones")
async def create_milestone(payload: MilestonePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Create a new milestone."""
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    milestone = Milestone(
        title=payload.title,
        start_date=payload.start_date,
        end_date=payload.end_date,
        created_by=u.id
    )
    session.add(milestone)
    await session.commit()
    await session.refresh(milestone)
    return {"ok": True, "id": milestone.id}

@app.get("/api/milestones")
async def get_milestones(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Get all milestones."""
    milestones_res = await session.execute(select(Milestone).order_by(Milestone.start_date))
    milestones = milestones_res.scalars().all()
    return {"milestones": [{"id": m.id, "title": m.title, "start_date": m.start_date, "end_date": m.end_date} for m in milestones]}

@app.delete("/api/milestones/{milestone_id}")
async def delete_milestone(milestone_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Delete a milestone."""
    milestone = await session.get(Milestone, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    await session.delete(milestone)
    await session.commit()
    return {"ok": True}

@app.patch("/api/milestones/{milestone_id}")
async def update_milestone(milestone_id: int, payload: MilestonePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Update an existing milestone."""
    milestone = await session.get(Milestone, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    milestone.title = payload.title
    milestone.start_date = payload.start_date
    milestone.end_date = payload.end_date
    await session.commit()
    return {"ok": True}

# --------- Project Pulse Route ---------
class ProjectPulsePayload(BaseModel):
    current_date: str
    milestones: List[Dict]
    tasks: List[Dict]

@app.post("/api/project-pulse")
async def get_project_pulse(payload: ProjectPulsePayload, username: str = Depends(get_current_user_token)):
    """Calculate project pulse status."""
    result = calculate_project_pulse(payload.current_date, payload.milestones, payload.tasks)
    return result

class ShipDatePayload(BaseModel):
    ship_date: str

@app.post("/api/project/ship-date")
async def set_ship_date(payload: ShipDatePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Set project ship date."""
    settings_res = await session.execute(select(ProjectSettings).limit(1))
    settings = settings_res.scalar_one_or_none()
    if not settings:
        settings = ProjectSettings(ship_date=payload.ship_date)
        session.add(settings)
    else:
        settings.ship_date = payload.ship_date
    await session.commit()
    return {"ok": True, "ship_date": payload.ship_date}

@app.get("/api/project/ship-date")
async def get_ship_date(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Get project ship date."""
    settings_res = await session.execute(select(ProjectSettings).limit(1))
    settings = settings_res.scalar_one_or_none()
    return {"ship_date": settings.ship_date if settings else None}

# --------- Dialectic Engine Routes ---------
@app.get("/api/decisions")
async def get_decisions(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Get all logged decisions."""
    decisions_res = await session.execute(select(Decision).order_by(desc(Decision.created_at)))
    decisions = decisions_res.scalars().all()
    result = []
    for d in decisions:
        user_obj = await session.get(User, d.decided_by)
        result.append({
            "id": d.id,
            "conflict_id": d.conflict_id,
            "selected_option": d.selected_option.value,
            "reasoning": d.reasoning,
            "decided_by": user_obj.username if user_obj else "unknown",
            "created_at": str(d.created_at)
        })
    return {"decisions": result}

@app.get("/api/decisions/{conflict_id}")
async def get_decision_by_conflict(conflict_id: str, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Get decision for specific conflict."""
    decision_res = await session.execute(select(Decision).where(Decision.conflict_id == conflict_id))
    decision = decision_res.scalar_one_or_none()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    user_obj = await session.get(User, decision.decided_by)
    return {
        "id": decision.id,
        "conflict_id": decision.conflict_id,
        "selected_option": decision.selected_option.value,
        "reasoning": decision.reasoning,
        "decided_by": user_obj.username if user_obj else "unknown",
        "created_at": str(decision.created_at)
    }

# --------- Voting System Routes ---------
@app.get("/api/decision-log")
async def get_decision_log(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Get project audit trail - all logged decisions."""
    from db import DecisionLog
    decisions_res = await session.execute(select(DecisionLog).order_by(desc(DecisionLog.created_at)))
    decisions = decisions_res.scalars().all()
    result = []
    for d in decisions:
        result.append({
            "id": d.id,
            "decision_text": d.decision_text,
            "rationale": d.rationale,
            "category": d.category.value,
            "decision_type": d.decision_type.value,
            "created_by": d.created_by,
            "chat_reference_id": d.chat_reference_id,
            "created_at": str(d.created_at)
        })
    return {"decisions": result}

@app.get("/api/active-conflicts")
async def get_active_conflicts(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Get currently active conflicts requiring votes."""
    from datetime import datetime
    conflicts_res = await session.execute(
        select(ActiveConflict).where(
            ActiveConflict.is_resolved == False,
            ActiveConflict.expires_at > datetime.now()
        ).order_by(desc(ActiveConflict.created_at))
    )
    conflicts = conflicts_res.scalars().all()
    
    result = []
    for c in conflicts:
        # Get vote counts
        votes_res = await session.execute(
            select(ConflictVote).where(ConflictVote.conflict_id == c.conflict_id)
        )
        votes = votes_res.scalars().all()
        
        vote_counts = {'A': 0, 'B': 0, 'C': 0}
        user_votes = {}
        for vote in votes:
            vote_counts[vote.selected_option.value] += 1
            user_obj = await session.get(User, vote.user_id)
            user_votes[user_obj.username if user_obj else "unknown"] = vote.selected_option.value
        
        remaining_time = c.expires_at - datetime.now()
        hours_left = max(0, int(remaining_time.total_seconds() / 3600))
        
        result.append({
            "conflict_id": c.conflict_id,
            "user_statement": c.user_statement,
            "source_file": c.source_file,
            "severity": c.severity.value,
            "reason": c.reason,
            "vote_counts": vote_counts,
            "user_votes": user_votes,
            "hours_remaining": hours_left,
            "created_at": str(c.created_at)
        })
    
    return {"conflicts": result}

class VotePayload(BaseModel):
    conflict_id: str
    option: str
    reasoning: str

@app.post("/api/vote")
async def submit_vote(payload: VotePayload, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Submit vote via decision bar."""
    from db import ConflictVote, ActiveConflict, DecisionOption
    from sqlalchemy import select
    
    res = await session.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid user")
    
    # Check if conflict exists and is active
    conflict_res = await session.execute(
        select(ActiveConflict).where(
            ActiveConflict.conflict_id == payload.conflict_id,
            ActiveConflict.is_resolved == False
        )
    )
    conflict = conflict_res.scalar_one_or_none()
    
    if not conflict:
        raise HTTPException(status_code=400, detail=f"Conflict {payload.conflict_id} not found or already resolved.")
    
    # Check if user already voted
    existing_vote_res = await session.execute(
        select(ConflictVote).where(
            ConflictVote.conflict_id == payload.conflict_id,
            ConflictVote.user_id == u.id
        )
    )
    existing_vote = existing_vote_res.scalar_one_or_none()
    
    if existing_vote:
        # Update existing vote
        existing_vote.selected_option = DecisionOption(payload.option)
        existing_vote.reasoning = payload.reasoning
    else:
        # Create new vote
        vote = ConflictVote(
            conflict_id=payload.conflict_id,
            user_id=u.id,
            selected_option=DecisionOption(payload.option),
            reasoning=payload.reasoning
        )
        session.add(vote)
    
    await session.commit()
    
    # Broadcast voting update
    await manager.broadcast({"type": "voting_updated"})
    return {"ok": True}

@app.post("/api/conflicts/{conflict_id}/end")
async def end_conflict_voting(conflict_id: str, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """End voting for a conflict and resolve it."""
    from db import ActiveConflict, ConflictVote, DecisionLog, DecisionCategory, DecisionType
    from sqlalchemy import select
    
    # Get conflict
    conflict_res = await session.execute(
        select(ActiveConflict).where(ActiveConflict.conflict_id == conflict_id)
    )
    conflict = conflict_res.scalar_one_or_none()
    
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Get votes
    votes_res = await session.execute(
        select(ConflictVote).where(ConflictVote.conflict_id == conflict_id)
    )
    votes = votes_res.scalars().all()
    
    # Count votes
    vote_counts = {'A': 0, 'B': 0, 'C': 0}
    for vote in votes:
        vote_counts[vote.selected_option.value] += 1
    
    # Determine winner
    winner = max(vote_counts, key=vote_counts.get)
    
    # Mark conflict as resolved
    conflict.is_resolved = True
    
    # Log decision
    decision_log = DecisionLog(
        decision_text=f"Team voted on conflict {conflict_id}",
        rationale=f"Option {winner} won with {vote_counts[winner]} votes (A:{vote_counts['A']} B:{vote_counts['B']} C:{vote_counts['C']})",
        category=DecisionCategory.methodology,
        decision_type=DecisionType.consensus,
        created_by="Team_Vote"
    )
    session.add(decision_log)
    
    await session.commit()
    
    # Broadcast update
    await manager.broadcast({"type": "voting_updated"})
    await manager.broadcast({"type": "decisions_updated"})
    
    return {"ok": True, "winner": winner, "votes": vote_counts}

@app.delete("/api/decision-log/clear")
async def clear_decision_log(username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    """Clear all decision log entries."""
    from db import DecisionLog
    from sqlalchemy import delete
    await session.execute(delete(DecisionLog))
    await session.commit()
    await manager.broadcast({"type": "decisions_updated"})
    return {"ok": True}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Optional auth via query param token
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from client over WS; ignore/echo if any
            data = await websocket.receive_text()
            await websocket.send_json({"type": "ack", "echo": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Serve frontend - mount last to avoid conflicts with API routes
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")
