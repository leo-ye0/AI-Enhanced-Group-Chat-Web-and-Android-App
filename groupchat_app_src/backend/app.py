import os
import asyncio
import time
import uuid
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from db import SessionLocal, init_db, User, Message, UploadedFile, Task, TaskStatus, Meeting
from auth import get_password_hash, verify_password, create_access_token, get_current_user_token
from websocket_manager import ConnectionManager
from llm import chat_completion
from file_processor import extract_text_from_pdf, extract_text_from_docx, chunk_text
from vector_db import add_documents, search_documents, delete_documents_by_file_id
from conversation_chain import conversation_chain, clear_conversation_history
from summarizer import generate_summary
from migrations import run_migrations
from project_manager import analyze_project, get_project_status
from task_extractor import extract_tasks
from meeting_detector import detect_meeting_request, generate_zoom_link

load_dotenv()

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))

app = FastAPI(title="StudyPal Chat")

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
        summary = await generate_summary(text, filename)
        async with SessionLocal() as session:
            file_obj = await session.get(UploadedFile, file_id)
            if file_obj:
                file_obj.summary = summary
                await session.commit()
    except Exception as e:
        print(f"Summary generation failed for file {file_id}: {e}")

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

async def extract_and_save_tasks(session: AsyncSession, content: str, message_id: int):
    """Extract and save tasks from a message."""
    tasks = await extract_tasks(content)
    if tasks:
        for task_content in tasks:
            task = Task(content=task_content, extracted_from_message_id=message_id, status=TaskStatus.pending)
            session.add(task)
        await session.commit()
        await manager.broadcast({"type": "tasks_updated"})

async def detect_and_suggest_meeting(session: AsyncSession, content: str, user_id: int):
    """Detect meeting requests and broadcast suggestion."""
    meeting_info = await detect_meeting_request(content)
    if meeting_info:
        await manager.broadcast({
            "type": "meeting_suggestion",
            "data": {
                "title": meeting_info.get("title", "Team Meeting"),
                "suggested_times": meeting_info.get("suggested_times", ""),
                "duration": meeting_info.get("duration", 30)
            }
        })

async def maybe_answer_with_llm(session: AsyncSession, content: str, message_id: int = None):
    # Check for project commands
    if content.strip().lower() == "/project analyze":
        reply_text = await analyze_project()
    elif content.strip().lower() == "/project status":
        reply_text = await get_project_status()
    elif content.strip().lower() == "/tasks":
        tasks_res = await session.execute(select(Task).where(Task.status == TaskStatus.pending).order_by(desc(Task.created_at)))
        tasks = tasks_res.scalars().all()
        if tasks:
            reply_text = "📋 Pending Tasks:\n" + "\n".join([f"{i+1}. {t.content}" for i, t in enumerate(tasks)])
        else:
            reply_text = "No pending tasks found."
    elif content.strip().lower() == "/schedule":
        await manager.broadcast({"type": "open_meeting_modal"})
        return
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

@app.post("/api/login")
async def login(payload: AuthPayload, session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(User).where(User.username == payload.username))
    u = res.scalar_one_or_none()
    if not u or not verify_password(payload.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": u.username})
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
    m = Message(user_id=u.id, content=payload.content, is_bot=False)
    session.add(m)
    await session.commit()
    await session.refresh(m)
    await broadcast_message(session, m)
    
    # Check if bot should respond (commands or @bot mentions)
    should_respond = (
        payload.content.startswith("/") or 
        "@bot" in payload.content.lower()
    )
    
    if should_respond:
        # Add user message to conversation history (skip commands)
        if not payload.content.startswith("/"):
            conversation_chain.add_to_history("user", payload.content)
        
        # fire-and-forget LLM answer
        asyncio.create_task(maybe_answer_with_llm(session, payload.content, m.id))
    
    # Always extract tasks and detect meetings from non-command messages
    if not payload.content.startswith("/"):
        asyncio.create_task(extract_and_save_tasks(session, payload.content, m.id))
        asyncio.create_task(detect_and_suggest_meeting(session, payload.content, u.id))
    
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
    return {"tasks": [{"id": t.id, "content": t.content, "status": t.status.value, "created_at": str(t.created_at)} for t in tasks]}

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

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await session.delete(task)
    await session.commit()
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
        result.append({"id": m.id, "title": m.title, "datetime": m.datetime, "duration_minutes": m.duration_minutes, "zoom_link": m.zoom_link, "transcript_filename": transcript_filename, "created_at": str(m.created_at)})
    return {"meetings": result}

@app.delete("/api/meetings/{meeting_id}")
async def delete_meeting(meeting_id: int, username: str = Depends(get_current_user_token), session: AsyncSession = Depends(get_db)):
    meeting = await session.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await session.delete(meeting)
    await session.commit()
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
