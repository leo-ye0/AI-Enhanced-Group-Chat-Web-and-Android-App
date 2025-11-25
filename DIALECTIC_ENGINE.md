# Dialectic Engine Implementation Guide

## Overview

The **Dialectic Engine** transforms your AI chat assistant from a passive responder into an active research partner that monitors conversations, detects conflicts with uploaded documents, and forces users to resolve them using logic.

## Core Concept

Instead of answering questions directly, the bot:
1. **Silently monitors** every message
2. **Detects conflicts** with the "Group Brain" (vector database)
3. **Intervenes** with Socratic questioning when conflicts arise
4. **Logs decisions** as formal project milestones

---

## Architecture Components

### 1. Silent Observer Loop (WebSocket Integration)

**Location:** `app.py` - `post_message()` endpoint

**How it works:**
- Every user message triggers `monitor_message_for_conflicts()`
- The function runs in the background WITHOUT responding unless a conflict is found
- Uses async processing to avoid blocking the chat flow

```python
# DIALECTIC ENGINE: Silent monitoring for conflicts
conflict = await monitor_message_for_conflicts(payload.content, m.id)
if conflict:
    intervention = await SocraticInterventionGenerator.generate_intervention(conflict)
    # Bot only speaks when conflict detected
    bot_msg = Message(user_id=None, content=intervention, is_bot=True)
    await broadcast_message(session, bot_msg)
```

**Key Feature:** The bot processes 50+ messages silently and only "speaks" on message #51 when it finds a conflict.

---

### 2. RAG Fact-Checking Pipeline

**Location:** `dialectic_engine.py` - `ConflictDetector` class

**Workflow:**

```
User Message: "Let's use Method A at 50°C"
    ↓
Vector DB Search: Query for "Method A" and "temperature"
    ↓
Retrieval: Finds "Method A fails above 40°C" in Smith_2024.pdf
    ↓
LLM Conflict Analysis: Compare user statement vs. retrieved fact
    ↓
Conflict Score: Similarity < 50% → TRIGGER INTERVENTION
```

**Implementation:**

```python
async def check_for_conflicts(user_statement: str) -> Optional[Dict]:
    # 1. Search vector DB
    search_results = search_documents(user_statement, n_results=3)
    
    # 2. Use LLM to determine conflict
    conflict_check_prompt = f"""
    USER STATEMENT: "{user_statement}"
    DOCUMENT EVIDENCE: "{top_doc}"
    
    Determine if there is a FACTUAL CONFLICT.
    Respond with JSON: {{"conflict": true/false, "severity": "low/medium/high"}}
    """
    
    # 3. Return conflict data if found
    if conflict_detected:
        return {
            "user_statement": user_statement,
            "conflicting_evidence": top_doc,
            "source_file": filename,
            "severity": "high"
        }
```

**Conflict Threshold:** Configurable (default: 50% similarity = conflict)

---

### 3. Socratic Intervention Protocol

**Location:** `dialectic_engine.py` - `SocraticInterventionGenerator` class

**The "Fork" Format:**

```
✋ CONFLICT DETECTED 🚨

Evidence from [Smith_2024.pdf]:
> "Method A fails above 40°C..."

Issue: User proposed 50°C exceeds documented safety limit

Decision Required - Choose One:

Option A: Keep current strategy & document mitigation plan
Option B: Revise approach to align with documented evidence  
Option C: Challenge the evidence (provide counter-source)

Reply with: @bot decision A/B/C [your reasoning]
```

**Severity Levels:**
- 🛑 **High:** Critical safety/compliance risk
- 🚨 **Medium:** Significant factual conflict
- ⚠️ **Low:** Minor discrepancy

---

### 4. Decision Log Database

**Location:** `db.py` - `Decision` model

**Schema:**

```sql
CREATE TABLE decisions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  conflict_id VARCHAR(255) NOT NULL,
  triggering_conflict TEXT NOT NULL,
  selected_option ENUM('A', 'B', 'C') NOT NULL,
  reasoning TEXT NOT NULL,
  decided_by INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (decided_by) REFERENCES users(id)
);
```

**Why Separate Table?**
- Decisions are **project milestones**, not just chat logs
- Enables audit trail for compliance
- Allows querying: "Show all times we chose Option C (challenged evidence)"

**API Endpoints:**
- `GET /api/decisions` - List all decisions
- `GET /api/decisions/{conflict_id}` - Get specific decision

---

## Usage Flow

### Example Scenario

**1. User sends message:**
```
User: "We should run the experiment at 50°C for better results"
```

**2. Silent monitoring detects conflict:**
```python
conflict = await monitor_message_for_conflicts(message, message_id)
# Searches vector DB → Finds conflicting protocol
```

**3. Bot intervenes:**
```
✋ CONFLICT DETECTED 🚨

Evidence from [Lab_Protocol_v2.pdf]:
> "Temperature must not exceed 40°C per safety guidelines..."

Issue: Proposed temperature violates documented safety protocol

Decision Required - Choose One:

Option A: Keep 50°C strategy & document risk mitigation
Option B: Revise to 40°C per protocol
Option C: Challenge the protocol (provide updated source)

Reply with: @bot decision A/B/C [your reasoning]
```

**4. User responds:**
```
User: "@bot decision B We'll follow the protocol and use 40°C for safety"
```

**5. Decision logged:**
```
✅ Decision Recorded: Team elected Option B

Reasoning: We'll follow the protocol and use 40°C for safety
```

**6. Database entry created:**
```json
{
  "conflict_id": "conflict_12345",
  "selected_option": "B",
  "reasoning": "Follow protocol for safety",
  "decided_by": "john_doe",
  "created_at": "2024-01-15 14:30:00"
}
```

---

## Configuration

### Adjust Conflict Sensitivity

**File:** `dialectic_engine.py`

```python
# Lower = stricter (more conflicts detected)
# Higher = lenient (fewer conflicts)
CONFLICT_THRESHOLD = 0.5  # Default: 50%
```

### Disable for Specific Topics

```python
# Skip conflict detection for casual chat
if any(word in message.lower() for word in ['hello', 'thanks', 'bye']):
    return None
```

---

## API Integration

### Check for Active Conflicts

```javascript
// Frontend: Display conflict indicator
fetch('/api/decisions')
  .then(res => res.json())
  .then(data => {
    if (data.decisions.length > 0) {
      showConflictBadge();
    }
  });
```

### Decision History Panel

```javascript
// Show decision audit trail
fetch('/api/decisions')
  .then(res => res.json())
  .then(data => {
    data.decisions.forEach(decision => {
      displayDecision(decision.selected_option, decision.reasoning);
    });
  });
```

---

## Benefits

### 1. **Prevents Groupthink**
- Forces team to confront contradictions
- Ensures evidence-based decisions

### 2. **Compliance Tracking**
- Audit trail for regulatory requirements
- Documents why protocols were followed/challenged

### 3. **Knowledge Enforcement**
- Uploaded documents become "source of truth"
- Prevents outdated information from spreading

### 4. **Active Learning**
- Team learns by resolving conflicts
- Socratic method encourages critical thinking

---

## Technical Highlights

### Async Processing
```python
# Non-blocking conflict detection
asyncio.create_task(monitor_message_for_conflicts(message))
```

### Vector Similarity Search
```python
# Semantic search for relevant documents
search_results = search_documents(query, n_results=3)
```

### LLM-Powered Analysis
```python
# AI determines if conflict exists
conflict_data = await chat_completion(conflict_check_prompt)
```

### State Management
```python
# Track active conflicts globally
active_conflicts: Dict[str, Dict] = {}
```

---

## Future Enhancements

### 1. Thread-Based UI
- Open conflicts in modal/sidebar
- Keep main chat clean

### 2. Multi-Source Conflicts
- Show conflicts between multiple documents
- "Document A says X, but Document B says Y"

### 3. Confidence Scoring
- Display certainty level: "80% confident this is a conflict"

### 4. Auto-Resolution
- For low-severity conflicts, suggest resolution automatically

### 5. Conflict Analytics
- Dashboard: "Most challenged documents"
- Trend: "Option A chosen 70% of the time"

---

## Testing

### Test Conflict Detection

```bash
# 1. Upload a document with specific facts
curl -X POST http://localhost:8000/api/upload \
  -F "file=@protocol.pdf"

# 2. Send conflicting message
curl -X POST http://localhost:8000/api/messages \
  -H "Authorization: Bearer <token>" \
  -d '{"content": "We should use Method X at 100°C"}'

# 3. Verify intervention appears
# Expected: Bot responds with conflict warning
```

### Test Decision Logging

```bash
# 1. Trigger conflict (see above)

# 2. Respond with decision
curl -X POST http://localhost:8000/api/messages \
  -H "Authorization: Bearer <token>" \
  -d '{"content": "@bot decision B We will follow the protocol"}'

# 3. Check decision was logged
curl http://localhost:8000/api/decisions \
  -H "Authorization: Bearer <token>"
```

---

## Summary

The Dialectic Engine transforms your chat app into an **active research partner** that:

✅ **Monitors silently** - Processes every message without spam  
✅ **Detects conflicts** - Uses RAG to find contradictions  
✅ **Forces decisions** - Socratic method with A/B/C options  
✅ **Logs outcomes** - Audit trail for compliance  

**Result:** Evidence-based collaboration with built-in quality control.
