# AI Project Manager & Task Extraction Features

## Overview
Added AI-powered project management capabilities with automatic task extraction from chat messages.

## Features

### 1. AI Project Manager Commands
Type these commands in chat to get AI analysis:

- **`/project analyze`** - AI analyzes chat history and uploaded files to suggest:
  - Project goals/objectives
  - Key phases or milestones
  - Suggested tasks
  - Timeline estimates

- **`/project status`** - AI summarizes current project progress:
  - What has been completed
  - What is in progress
  - What needs attention
  - Any blockers or issues

- **`/tasks`** - Lists all pending tasks extracted from chat

### 2. Automatic Task Extraction
AI automatically detects tasks from your messages when you use phrases like:
- "we need to..."
- "should..."
- "must..."
- "TODO:"
- "task:"
- "by [date]"
- "deadline"

**Example Messages:**
- "We need to implement user authentication by Friday"
- "TODO: Fix the database connection issue"
- "Should add error handling to the API"

### 3. Task Panel
- Right sidebar shows all extracted tasks
- ✓ button to mark tasks complete
- × button to delete tasks
- Real-time updates when new tasks are detected

## Usage Example

```
User: We need to implement user authentication and add file upload validation by next week.
Bot: [Responds to message]
[Task Panel automatically shows 2 new tasks:
 1. Implement user authentication
 2. Add file upload validation by next week]

User: /project status
Bot: [Provides AI-generated project status summary]

User: /project analyze
Bot: [Provides comprehensive project analysis with phases and timeline]

User: /tasks
Bot: 📋 Pending Tasks:
1. Implement user authentication
2. Add file upload validation by next week
```

## Technical Details

### Backend
- **project_manager.py** - AI analysis functions
- **task_extractor.py** - Task detection from messages
- **Task model** - Database table for task storage
- **API endpoints**:
  - `GET /api/tasks` - List all tasks
  - `PATCH /api/tasks/{id}/complete` - Mark task complete
  - `DELETE /api/tasks/{id}` - Delete task

### Frontend
- Task panel in right sidebar
- Real-time WebSocket updates
- Complete/delete buttons per task

### Database Schema
```sql
CREATE TABLE tasks (
  id INT PRIMARY KEY AUTO_INCREMENT,
  content TEXT,
  extracted_from_message_id INT,
  status ENUM('pending', 'completed'),
  created_at TIMESTAMP
);
```

## Benefits
- **Zero manual entry** - Tasks auto-detected from natural conversation
- **Context-aware** - AI understands project from chat + files
- **Actionable insights** - Get structured project analysis on demand
- **Team visibility** - All tasks visible to group chat members
