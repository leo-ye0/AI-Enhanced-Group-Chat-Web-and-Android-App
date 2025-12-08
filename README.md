# AI-Enhanced Group Chat with RAG System

A real-time group chat application with AI assistant, file upload capabilities, and Retrieval Augmented Generation (RAG) system for context-aware responses.

## Features

- **Real-time Group Chat**: WebSocket-based messaging with multiple users
- **AI Assistant**: LLM bot responds to questions (messages containing "?")
- **Dialectic Engine**: Active research partner that monitors conversations, detects conflicts with uploaded documents, and forces evidence-based decisions using Socratic method
- **File Upload & RAG**: Upload PDF/DOCX/TXT files with automatic text extraction and vector search
- **Auto-Summarization**: AI-generated summaries for uploaded documents
- **Conversation Memory**: Context-aware responses using chat history
- **Decision Logging**: Permanent audit trail for team decisions with conflict resolution tracking
- **File Management**: Preview, download, and delete uploaded files
- **Responsive UI**: Works on desktop and mobile devices

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

1. **Sign Up/Login**: Create an account or log in
2. **Chat**: Send messages in the group chat
3. **Ask Questions**: Messages with "?" trigger AI responses
4. **Upload Files**: Click "Upload File" to add PDF/DOCX/TXT documents
5. **View Summaries**: Auto-generated summaries appear for uploaded files
6. **Toggle Summaries**: Use "Hide Summaries" button to minimize file view
7. **File Actions**: View files in browser or delete them

## API Endpoints

- `POST /api/signup` - User registration
- `POST /api/login` - User authentication
- `GET /api/messages` - Retrieve chat messages
- `POST /api/messages` - Send new message
- `DELETE /api/messages` - Clear chat history
- `POST /api/upload` - Upload file
- `GET /api/files` - List uploaded files
- `GET /api/files/{id}/download` - Download file
- `DELETE /api/files/delete/{id}` - Delete file
- `GET /api/decisions` - List all logged decisions (Dialectic Engine)
- `GET /api/decisions/{conflict_id}` - Get specific decision
- `WebSocket /ws` - Real-time messaging

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
- `users` - User accounts
- `messages` - Chat messages
- `uploaded_files` - File metadata and content

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

## Dialectic Engine

The **Dialectic Engine** is an active AI research partner that:

1. **Monitors Silently**: Processes every message without responding unless a conflict is detected
2. **Detects Conflicts**: Uses RAG to find contradictions between user statements and uploaded documents
3. **Forces Decisions**: Presents Socratic fork with 3 options (A: Keep & Mitigate, B: Align with Evidence, C: Challenge Evidence)
4. **Logs Outcomes**: Creates permanent audit trail in database

**Usage:**
```
User: "We should use Method A at 60°C"

Bot: ✋ CONFLICT DETECTED 🚨
Evidence from [protocol.pdf]: "Max temp is 45°C"

Decision Required:
Option A: Keep 60°C & document mitigation
Option B: Revise to 45°C per protocol
Option C: Challenge the protocol

Reply: @bot decision A/B/C [reasoning]

User: "@bot decision B We'll follow the protocol"

Bot: ✅ Decision Recorded: Team elected Option B
```

**Documentation:**
- Technical Guide: `DIALECTIC_ENGINE.md`
- User Guide: `DIALECTIC_QUICKSTART.md`
- Setup: `IMPLEMENTATION_SUMMARY.md`

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