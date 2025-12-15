# AI-Enhanced Group Chat with RAG System

A real-time group chat application with AI assistant, file upload capabilities, and Retrieval Augmented Generation (RAG) system for context-aware responses.

## Features

### 💬 **Communication**
- **Real-time Group Chat**: WebSocket-based messaging with multiple users
- **Multi-Group Support**: Create and join multiple project groups with isolated workspaces
- **Direct Messaging**: Private 1-on-1 conversations between team members
- **AI Assistant**: LLM bot with natural language understanding and context-aware responses

### 🤖 **AI-Powered Intelligence**
- **RAG System**: Upload PDF/DOCX/TXT files with automatic text extraction and semantic search
- **Dialectic Engine**: Monitors conversations, detects conflicts with uploaded documents, forces evidence-based decisions
- **Smart Task Assignment**: AI matches tasks to team members based on roles (Backend Dev, QA, DevOps, etc.)
- **Auto-Summarization**: AI-generated summaries for uploaded documents
- **Intent Detection**: Automatically recognizes commands for tasks, meetings, votes, and milestones

### 📊 **Project Management**
- **Milestone Planning**: AI-generated project phases with dates, descriptions, and risk levels
- **Task Management**: Create, assign, track tasks with due dates and milestone linking
- **Progress Tracking**: Auto-calculated milestone completion based on linked tasks
- **Role-Based Workflow**: Tasks assigned based on team member roles with accept/decline flow
- **Meeting Scheduler**: Create meetings with Zoom links, attendees, and transcript uploads

### 🗳️ **Decision Making**
- **Team Voting**: Democratic decision-making with A/B/C options and reasoning
- **Conflict Detection**: RAG-powered detection of contradictions with uploaded documents
- **Decision Logging**: Permanent audit trail for all team decisions
- **Socratic Method**: Forces teams to justify decisions with evidence

### 📈 **Dashboard & Analytics**
- **Workspace Overview**: See all groups, tasks, meetings, and conflicts in one view
- **Project Pulse**: Real-time progress tracking with risk indicators
- **Team Roles**: Visual display of team members and their responsibilities
- **Active Conflicts**: Track ongoing votes and decision deadlines

### 🎨 **User Experience**
- **Responsive UI**: Works on desktop and mobile devices
- **Real-time Updates**: WebSocket-powered instant notifications
- **File Management**: Preview, download, and delete uploaded files
- **Customizable Profiles**: Set roles, upload avatars, manage preferences

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- MySQL (database)
- ChromaDB (vector database for RAG)
- SentenceTransformers (embeddings)
- WebSocket (real-time communication)

**Frontend:**
- Vanilla HTML/CSS/JavaScript
- Responsive design

## Setup Instructions

### Prerequisites

- Python 3.8+
- MySQL server
- LLM API endpoint (OpenAI-compatible)

### 1. Clone Repository

```bash
git clone <repository-url>
cd AI-Enhanced-Group-Chat-Web-and-Android-App
```

### 2. Backend Setup

```bash
cd groupchat_app_src/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Create MySQL database
mysql -u root -p
CREATE DATABASE groupchat;
CREATE USER 'chatuser'@'localhost' IDENTIFIED BY 'chatpass';
GRANT ALL PRIVILEGES ON groupchat.* TO 'chatuser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. Environment Configuration

Create `.env` file in the backend directory:

```env
# Database
DATABASE_URL=mysql+asyncmy://chatuser:chatpass@localhost:3306/groupchat

# LLM API (OpenAI-compatible endpoint)
LLM_API_BASE=http://localhost:8001/v1
LLM_MODEL=llama-3-8b-instruct
LLM_API_KEY=your-api-key-here

# Server
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 5. Run Application

```bash
# Start backend server
cd groupchat_app_src/backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Access Application

Open your browser and navigate to:
```
http://localhost:8000
```

## Usage

### **Getting Started**
1. **Sign Up/Login**: Create an account or log in
2. **Create/Join Groups**: Create new project groups or browse and join existing ones
3. **Set Your Role**: Use `/role [your role]` to set your expertise (e.g., "Backend Dev, Python")

### **Communication**
4. **Chat**: Send messages in group chat or direct messages
5. **Ask AI**: Use `@bot` or type questions with "?" for AI responses
6. **Upload Files**: Add PDF/DOCX/TXT documents to Group Brain for RAG search

### **Project Management**
7. **Generate Milestones**: Type `/milestones` to AI-generate project phases
8. **Create Tasks**: Use `/tasks` or click "Add Task" in sidebar
9. **Smart Assignment**: AI auto-assigns tasks based on team roles
10. **Accept/Decline**: Team members confirm or decline task assignments
11. **Track Progress**: View milestone completion in Project Pulse sidebar

### **Meetings & Collaboration**
12. **Schedule Meetings**: Use `/schedule` or click "Add Meeting"
13. **Upload Transcripts**: Add meeting transcripts for AI analysis
14. **Team Voting**: Use `/vote [question]` to start democratic decisions

### **Commands**
- `/role [your role]` - Set your role(s)
- `/milestones` - Generate project milestones
- `/tasks` - Generate tasks from milestones
- `/schedule` - AI suggests meeting times
- `/vote [question]` - Start team vote
- `/project analyze` - Get project status report
- `/decisions` - View decision history
- `@bot decision [ID] A/B/C [reasoning]` - Vote on conflicts

## API Endpoints

### **Authentication**
- `POST /api/signup` - User registration
- `POST /api/login` - User authentication

### **Messaging**
- `GET /api/messages` - Retrieve chat messages (group or DM)
- `POST /api/messages` - Send new message
- `DELETE /api/messages` - Clear chat history
- `WebSocket /ws` - Real-time messaging

### **Groups**
- `GET /api/groups` - List user's groups
- `GET /api/groups/all` - Browse all available groups
- `POST /api/groups` - Create new group
- `POST /api/groups/{id}/join` - Join a group
- `GET /api/groups/{id}/members` - Get group members

### **Tasks**
- `GET /api/tasks` - List tasks (filterable by group)
- `POST /api/tasks` - Create new task
- `PATCH /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `POST /api/tasks/{id}/complete` - Mark task complete
- `POST /api/tasks/{id}/accept` - Accept task assignment
- `POST /api/tasks/{id}/decline` - Decline task assignment
- `PATCH /api/tasks/{id}/assign` - Assign task to users

### **Milestones**
- `GET /api/milestones` - List milestones
- `POST /api/milestones` - Create milestone
- `POST /api/milestones/suggest` - AI-generate milestones
- `POST /api/milestones/bulk` - Create multiple milestones
- `PATCH /api/milestones/{id}` - Update milestone
- `DELETE /api/milestones/{id}` - Delete milestone

### **Meetings**
- `GET /api/meetings` - List meetings
- `POST /api/meetings` - Create meeting
- `PATCH /api/meetings/{id}/title` - Update meeting title
- `PATCH /api/meetings/{id}/datetime` - Update meeting time
- `PATCH /api/meetings/{id}/attendees` - Update attendees
- `POST /api/meetings/{id}/transcript` - Upload transcript
- `DELETE /api/meetings/{id}` - Delete meeting

### **Files & RAG**
- `POST /api/upload` - Upload file (PDF/DOCX/TXT)
- `GET /api/files` - List uploaded files
- `GET /api/files/{id}/download` - Download file
- `DELETE /api/files/delete/{id}` - Delete file

### **Dialectic Engine**
- `GET /api/active-conflicts` - List active votes
- `POST /api/vote` - Submit vote on conflict
- `POST /api/conflicts/{id}/end` - End voting period
- `GET /api/decision-log` - List all logged decisions
- `GET /api/decisions/{conflict_id}` - Get specific decision

### **Dashboard**
- `GET /api/dashboard` - Get workspace overview
- `GET /api/users` - List all users
- `POST /api/project-pulse` - Get project status
- `POST /api/project/ship-date` - Set/update ship date

## Architecture

### RAG Pipeline
1. **File Upload** → Text extraction (PDF/DOCX/TXT)
2. **Text Chunking** → Split into 500-word chunks with 50-word overlap
3. **Embeddings** → Generate vectors using SentenceTransformers
4. **Vector Storage** → Store in ChromaDB with metadata
5. **Query Processing** → Search relevant chunks for user questions
6. **Context Injection** → Combine search results with chat history
7. **LLM Response** → Generate context-aware answers

### Database Schema

**MySQL (Structured Data):**
- `users` - User accounts with roles
- `groups` - Project groups
- `group_members` - Group membership
- `messages` - Chat messages (group and DM)
- `tasks` - Task management with assignments
- `milestones` - Project phases with dates
- `meetings` - Scheduled meetings with attendees
- `uploaded_files` - File metadata and content
- `decisions` - Decision audit trail
- `active_conflicts` - Ongoing votes
- `conflict_votes` - Individual vote records
- `project_settings` - Ship dates and settings

**ChromaDB (Vector Database):**
- Document embeddings (384-dimensional vectors)
- Metadata: filename, chunk_id, upload_date
- Semantic search for RAG queries

## Development

### File Structure
```
groupchat_app_src/
├── backend/
│   ├── app.py              # Main FastAPI application
│   ├── db.py               # Database models
│   ├── auth.py             # Authentication
│   ├── llm.py              # LLM integration
│   ├── vector_db.py        # ChromaDB integration
│   ├── file_processor.py   # File text extraction
│   ├── summarizer.py       # Auto-summarization
│   ├── conversation_chain.py # Chat memory
│   ├── migrations.py       # Database migrations
│   └── requirements.txt    # Python dependencies
└── frontend/
    ├── index.html          # Main HTML
    ├── app.js              # JavaScript logic
    └── styles.css          # Styling
```

## Key Features Deep Dive

### 🤖 **Dialectic Engine**
Active AI research partner that monitors conversations and enforces evidence-based decisions:

1. **Silent Monitoring**: Processes every message without responding unless conflict detected
2. **RAG-Powered Detection**: Searches uploaded documents for contradictions (70%+ confidence threshold)
3. **Socratic Method**: Forces team to choose between 3 options with reasoning
4. **Democratic Voting**: 2-hour voting period with A/B/C options
5. **Audit Trail**: Permanent decision log in database

**Example Workflow:**
```
User: "We should use Streamlit for the dashboard"

Bot: 🚨 CONFLICT DETECTED
Evidence from [requirements.pdf]: "Use React framework"
Conflict ID: C4A7B2E1 | Confidence: 95%

Option A: Keep Streamlit & document mitigation
Option B: Revise to React per requirements
Option C: Challenge the requirements document

Vote: @bot decision C4A7B2E1 A/B/C [reasoning]

Alice: @bot decision B React is in requirements
Bob: @bot decision B Agree with requirements

Bot: ✅ Decision Recorded: Team chose Option B (2 votes)
```

### 📋 **Smart Task Assignment**
AI-powered role-based task assignment with human approval:

1. **Role Matching**: LLM analyzes task requirements and matches to team member roles
2. **Milestone Linking**: Tasks automatically linked to parent milestones
3. **Accept/Decline Flow**: Assignees must confirm before task becomes active
4. **Progress Tracking**: Milestone completion auto-calculated from task status

**Example:**
```
Milestone: "Backend Development" (assigned_roles: "Backend Dev, DevOps")

AI Generates:
- "Create REST API" → alice (Backend Dev) ✓
- "Setup CI/CD" → carol (DevOps) ✓
- "Write API tests" → alice (Backend) + dave (QA) ✓

Alice receives notification → [Accept] → Task status: pending → active
Milestone progress: 0/3 → 1/3 (33%) → 2/3 (67%) → 3/3 (100%)
```

### 🎯 **RAG Pipeline**
Retrieval Augmented Generation for context-aware AI responses:

1. **File Upload**: PDF/DOCX/TXT → Text extraction
2. **Chunking**: 500-word chunks with 50-word overlap
3. **Embedding**: SentenceTransformers (384-dim vectors)
4. **Vector Storage**: ChromaDB with metadata
5. **Semantic Search**: Query → Top 5 relevant chunks
6. **Context Injection**: Chunks + chat history → LLM
7. **AI Response**: Evidence-based answer with citations

**Example:**
```
User: "What's the project deadline?"
→ RAG searches uploaded docs
→ Finds: "Ship date: December 31, 2024" in requirements.pdf
→ AI: "According to requirements.pdf, the deadline is Dec 31, 2024"
```

## Troubleshooting

**Database Connection Issues:**
- Verify MySQL is running
- Check database credentials in `.env`
- Ensure database and user exist

**LLM API Issues:**
- Verify LLM endpoint is accessible
- Check API key configuration
- Ensure model name is correct

**File Upload Issues:**
- Check file size limits
- Verify supported file types (PDF/DOCX/TXT)
- Ensure proper permissions