from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from db import SessionLocal

async def run_migrations():
    """Run database migrations to update schema."""
    async with SessionLocal() as session:
        # Check if summary column exists
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'uploaded_files' 
            AND column_name = 'summary'
        """))
        
        count = result.scalar()
        
        if count == 0:
            # Add summary column if it doesn't exist
            await session.execute(text("ALTER TABLE uploaded_files ADD COLUMN summary TEXT NULL"))
            await session.commit()
            print("✅ Added summary column to uploaded_files table")
        else:
            print("✅ Summary column already exists")
        
        # Check if transcript_file_id column exists
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'meetings' 
            AND column_name = 'transcript_file_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE meetings ADD COLUMN transcript_file_id INT NULL"))
            await session.commit()
            print("✅ Added transcript_file_id column to meetings table")
        else:
            print("✅ transcript_file_id column already exists")