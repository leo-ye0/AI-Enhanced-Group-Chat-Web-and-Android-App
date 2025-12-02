from llm import chat_completion
from sqlalchemy import select, desc, asc
from db import Message, User, SessionLocal
from datetime import datetime, timedelta

async def compact_chat_history(threshold_messages: int = 100):
    """Compact old chat messages into a summary when history gets too long."""
    async with SessionLocal() as session:
        # Count total messages
        total_count = await session.execute(select(Message))
        total_messages = len(total_count.scalars().all())
        
        if total_messages <= threshold_messages:
            return None
        
        # Get oldest 50% of messages for compaction
        compact_count = total_messages // 2
        old_messages = await session.execute(
            select(Message).order_by(asc(Message.created_at)).limit(compact_count)
        )
        messages_to_compact = old_messages.scalars().all()
        
        # Create summary
        chat_lines = []
        for msg in messages_to_compact:
            if not msg.is_bot:
                if msg.user_id:
                    user = await session.get(User, msg.user_id)
                    username = user.username if user else "unknown"
                else:
                    username = "unknown"
                chat_lines.append(f"{username}: {msg.content}")
        chat_text = "\n".join(chat_lines)
        
        prompt = f"""Summarize this chat history into key points and decisions:

{chat_text[:3000]}

Create a concise summary covering:
• Main topics discussed
• Key decisions made
• Important information shared
• Action items mentioned

Format as: 📝 CHAT SUMMARY (Messages 1-{compact_count})"""
        
        summary = await chat_completion([{"role": "user", "content": prompt}])
        
        # Delete old messages and insert summary
        for msg in messages_to_compact:
            await session.delete(msg)
        
        # Create summary message
        summary_msg = Message(
            content=summary.strip(),
            user_id=None,
            is_bot=True,
            created_at=messages_to_compact[0].created_at
        )
        session.add(summary_msg)
        await session.commit()
        
        return f"Compacted {compact_count} messages into summary"

async def should_compact_history():
    """Check if chat history needs compacting."""
    async with SessionLocal() as session:
        total_count = await session.execute(select(Message))
        return len(total_count.scalars().all()) > 100