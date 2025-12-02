from llm import chat_completion
from sqlalchemy import select
from db import User, Task, TaskStatus, Milestone, GroupMembership
import json
from datetime import datetime

async def assign_task_to_user(session, task_content: str, task_id: int = None, user_message: str = None, group_id: int = None) -> dict:
    """Use LLM to assign task to ONE best-suited user based on roles and workload, with auto due date."""
    print(f"\n📋 TASK ASSIGNMENT: '{task_content[:60]}...'")
    if user_message:
        print(f"   User request: '{user_message[:60]}...'")
    if group_id:
        print(f"   Group ID: {group_id}")
    
    # Get users in current group with their group-specific roles
    if group_id:
        memberships_res = await session.execute(
            select(GroupMembership, User)
            .join(User, GroupMembership.user_id == User.id)
            .where(GroupMembership.group_id == group_id)
        )
        memberships = memberships_res.all()
        users = [(m.GroupMembership, m.User) for m in memberships]
    else:
        # Fallback to all users if no group specified
        users_res = await session.execute(select(User))
        users = [(None, u) for u in users_res.scalars().all()]
    
    if not users:
        print("   ❌ No users available")
        return {"assigned_to": None, "reason": "No users available", "due_date": None}
    
    # Get milestones for due date suggestion
    milestones_res = await session.execute(select(Milestone).order_by(Milestone.start_date))
    milestones = milestones_res.scalars().all()
    milestone_context = "\n".join([f"- {m.title}: {m.start_date} to {m.end_date}" for m in milestones]) if milestones else "No milestones set"
    
    # Get task counts per user
    from sqlalchemy import func
    task_counts_res = await session.execute(
        select(Task.assigned_to, func.count(Task.id))
        .where(Task.status == TaskStatus.pending)
        .group_by(Task.assigned_to)
    )
    task_counts = {row[0]: row[1] for row in task_counts_res.all()}
    
    # Build user list with roles and workload
    user_list = []
    print("   👥 Available users in group:")
    for membership, user in users:
        # Use group-specific role if available, otherwise fall back to user's global role
        role = membership.role if membership and membership.role else (user.role if user.role else "No role")
        pending_tasks = task_counts.get(user.username, 0)
        user_list.append(f"{user.username} ({role}, {pending_tasks} pending tasks)")
        print(f"      - {user.username}: role='{role}', pending={pending_tasks}")
    
    # Parse user message for explicit assignee if provided
    explicit_assignee = None
    if user_message:
        for membership, user in users:
            if user.username.lower() in user_message.lower():
                explicit_assignee = user.username
                print(f"   🎯 Explicit assignee detected: {explicit_assignee}")
                break
    
    prompt = f"""Assign this task to ONE team member, suggest a due date, and understand natural language.

Task: {task_content}
{f"User request: {user_message}" if user_message else ""}

Team Members:
{chr(10).join([f"- {u}" for u in user_list])}

Project Milestones:
{milestone_context}

Return ONLY a JSON object:
{{"assigned_to": "username", "due_date": "YYYY-MM-DD", "reason": "brief explanation"}}

Rules:
- Pick ONE username only
{f"- MUST assign to {explicit_assignee} if mentioned in user request" if explicit_assignee else "- Match role by KEYWORDS (e.g., 'goalkeeper' task → user with 'goalkeeper' in their role)"}
- If task mentions a role (goalkeeper, developer, etc.), assign to user whose role contains that keyword
- If multiple users match, pick the one with fewer pending tasks
- Suggest due_date based on milestones (pick a date within the relevant milestone period)
- If no milestones, suggest 7 days from today ({datetime.now().strftime('%Y-%m-%d')})
- Keep reason under 20 words
"""
    
    try:
        print("   🤖 Asking LLM for assignment...")
        response = await chat_completion([{"role": "user", "content": prompt}])
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            result = json.loads(response[json_start:json_end])
            print(f"   ✅ Assigned to: {result.get('assigned_to')}")
            print(f"      Due date: {result.get('due_date')}")
            print(f"      Reason: {result.get('reason')}")
            
            # Update task if task_id provided
            if task_id:
                task = await session.get(Task, task_id)
                if task:
                    task.assigned_to = result.get("assigned_to")
                    if result.get("due_date"):
                        task.due_date = result.get("due_date")
                    await session.commit()
            
            return result
        print("   ⚠️  Using default assignment")
        return {"assigned_to": users[0][1].username, "reason": "Default assignment", "due_date": None}
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"assigned_to": users[0][1].username, "reason": "Default assignment", "due_date": None}
