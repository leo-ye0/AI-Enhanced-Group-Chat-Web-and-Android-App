from llm import chat_completion
from sqlalchemy import select, delete
from db import Milestone, ProjectSettings, SessionLocal
import json
import re

async def detect_milestone_changes(content: str, user_id: int) -> bool:
    """Detect if user wants to modify milestones and handle it."""
    milestone_keywords = ['milestone', 'phase', 'deadline', 'timeline', 'schedule', 'project plan']
    action_keywords = ['change', 'update', 'modify', 'add', 'remove', 'delete', 'extend', 'move', 'shift']
    
    content_lower = content.lower()
    has_milestone = any(keyword in content_lower for keyword in milestone_keywords)
    has_action = any(keyword in content_lower for keyword in action_keywords)
    
    if has_milestone and has_action:
        return await process_milestone_change(content, user_id)
    return False

async def process_milestone_change(content: str, user_id: int) -> str:
    """Process milestone change request and return response."""
    async with SessionLocal() as session:
        # Get current milestones
        milestones_res = await session.execute(select(Milestone).order_by(Milestone.start_date))
        current_milestones = milestones_res.scalars().all()
        
        # Get ship date
        settings_res = await session.execute(select(ProjectSettings).limit(1))
        settings = settings_res.scalar_one_or_none()
        ship_date = settings.ship_date if settings else None
        
        # Build context for LLM
        current_context = ""
        if current_milestones:
            current_context = "Current milestones:\n"
            for m in current_milestones:
                current_context += f"- {m.title}: {m.start_date} to {m.end_date}\n"
        
        ship_context = f"\nShip date: {ship_date}" if ship_date else ""
        
        prompt = f"""User wants to modify project milestones. Analyze their request and provide updated milestones.

{current_context}{ship_context}

User request: "{content}"

Respond with ONLY a JSON object in this format:
{{
  "action": "update|add|delete|none",
  "milestones": [
    {{"title": "Phase Name", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}},
    ...
  ],
  "response": "Brief explanation of changes made"
}}

Rules:
- Keep existing milestones unless specifically asked to change them
- Dates must be in YYYY-MM-DD format
- If ship_date exists, all milestones must end before it
- If action is "none", return empty milestones array"""

        try:
            llm_response = await chat_completion([{"role": "user", "content": prompt}])
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if not json_match:
                return "I couldn't understand your milestone request. Please be more specific."
            
            result = json.loads(json_match.group())
            
            if result.get("action") == "none":
                return result.get("response", "No changes needed to milestones.")
            
            # Clear existing milestones
            await session.execute(delete(Milestone))
            
            # Add new milestones
            for m_data in result.get("milestones", []):
                milestone = Milestone(
                    title=m_data["title"],
                    start_date=m_data["start_date"],
                    end_date=m_data["end_date"],
                    created_by=user_id
                )
                session.add(milestone)
            
            await session.commit()
            
            # Broadcast update
            from websocket_manager import ConnectionManager
            manager = ConnectionManager()
            await manager.broadcast({"type": "milestones_updated"})
            
            return f"✅ **Milestones Updated**\n\n{result.get('response', 'Milestones have been updated.')}"
            
        except Exception as e:
            return f"Error processing milestone request: {str(e)}"