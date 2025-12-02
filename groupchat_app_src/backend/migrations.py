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
        
        # Check if group_id column exists in messages table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'messages' 
            AND column_name = 'group_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE messages ADD COLUMN group_id INT NULL"))
            await session.commit()
            print("✅ Added group_id column to messages table")
        else:
            print("✅ group_id column already exists")
        
        # Check if group_id column exists in tasks table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'tasks' 
            AND column_name = 'group_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE tasks ADD COLUMN group_id INT NULL"))
            await session.commit()
            print("✅ Added group_id column to tasks table")
        else:
            print("✅ group_id column already exists")
        
        # Check if group_id column exists in meetings table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'meetings' 
            AND column_name = 'group_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE meetings ADD COLUMN group_id INT NULL"))
            await session.commit()
            print("✅ Added group_id column to meetings table")
        else:
            print("✅ group_id column already exists")
        
        # Check if group_id column exists in uploaded_files table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'uploaded_files' 
            AND column_name = 'group_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE uploaded_files ADD COLUMN group_id INT NULL"))
            await session.commit()
            print("✅ Added group_id column to uploaded_files table")
        else:
            print("✅ group_id column already exists")
        
        # Check if role column exists in group_memberships table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'group_memberships' 
            AND column_name = 'role'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE group_memberships ADD COLUMN role VARCHAR(100) NULL"))
            await session.commit()
            print("✅ Added role column to group_memberships table")
        else:
            print("✅ role column already exists")
        
        # Check if group_id column exists in milestones table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'milestones' 
            AND column_name = 'group_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE milestones ADD COLUMN group_id INT NULL"))
            await session.commit()
            print("✅ Added group_id column to milestones table")
        else:
            print("✅ group_id column already exists")
        
        # Check if group_id column exists in active_conflicts table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'active_conflicts' 
            AND column_name = 'group_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE active_conflicts ADD COLUMN group_id INT NULL"))
            await session.commit()
            print("✅ Added group_id column to active_conflicts table")
        else:
            print("✅ group_id column already exists")
        
        # Check if last_active_group_id column exists in users table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'users' 
            AND column_name = 'last_active_group_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE users ADD COLUMN last_active_group_id INT NULL"))
            await session.commit()
            print("✅ Added last_active_group_id column to users table")
        else:
            print("✅ last_active_group_id column already exists")
        
        # Check if group_id column exists in decision_log table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'decision_log' 
            AND column_name = 'group_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE decision_log ADD COLUMN group_id INT NULL"))
            await session.commit()
            print("✅ Added group_id column to decision_log table")
        else:
            print("✅ group_id column already exists in decision_log")
        
        # Check if group_id column exists in project_settings table
        result = await session.execute(text("""
            SELECT COUNT(*) as count 
            FROM information_schema.columns 
            WHERE table_schema = DATABASE() 
            AND table_name = 'project_settings' 
            AND column_name = 'group_id'
        """))
        
        count = result.scalar()
        
        if count == 0:
            await session.execute(text("ALTER TABLE project_settings ADD COLUMN group_id INT NULL"))
            await session.commit()
            print("✅ Added group_id column to project_settings table")
        else:
            print("✅ group_id column already exists in project_settings")