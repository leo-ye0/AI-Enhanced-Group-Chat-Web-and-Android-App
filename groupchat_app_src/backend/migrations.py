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
        
        # Check if assigned_to column exists
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'tasks' 
            AND column_name = 'assigned_to'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE tasks ADD COLUMN assigned_to TEXT NULL"))
            await session.commit()
            print("✅ Added assigned_to column to tasks table")
        else:
            # Check if it's INT type and needs conversion
            result = await session.execute(text("""
                SELECT DATA_TYPE FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'tasks' 
                AND column_name = 'assigned_to'
            """))
            data_type = result.scalar()
            if data_type == 'int':
                await session.execute(text("ALTER TABLE tasks MODIFY COLUMN assigned_to TEXT NULL"))
                await session.commit()
                print("✅ Converted assigned_to column to TEXT")
            else:
                print("✅ assigned_to column already exists")
        
        # Check if due_date column exists
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'tasks' 
            AND column_name = 'due_date'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE tasks ADD COLUMN due_date VARCHAR(100) NULL"))
            await session.commit()
            print("✅ Added due_date column to tasks table")
        else:
            print("✅ due_date column already exists")
        
        # Check if attendees column exists
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'meetings' 
            AND column_name = 'attendees'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE meetings ADD COLUMN attendees TEXT NULL"))
            await session.commit()
            print("✅ Added attendees column to meetings table")
        else:
            print("✅ attendees column already exists")