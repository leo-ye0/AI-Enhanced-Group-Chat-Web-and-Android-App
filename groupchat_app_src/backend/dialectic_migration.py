"""
Migration script to add Dialectic Engine decision logging table.
Run this to upgrade existing databases.
"""
from sqlalchemy import text
from db import engine

async def add_decisions_table():
    """Add decisions table for Dialectic Engine."""
    async with engine.begin() as conn:
        # Check if table exists
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'decisions'"
        ))
        exists = result.scalar() > 0
        
        if exists:
            print("✓ Decisions table already exists")
            return
        
        # Create decisions table
        await conn.execute(text("""
            CREATE TABLE decisions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                conflict_id VARCHAR(255) NOT NULL,
                triggering_conflict TEXT NOT NULL,
                selected_option ENUM('A', 'B', 'C') NOT NULL,
                reasoning TEXT NOT NULL,
                decided_by INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_decision_user FOREIGN KEY (decided_by) 
                    REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_conflict_id (conflict_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
        
        print("✓ Created decisions table for Dialectic Engine")

if __name__ == "__main__":
    import asyncio
    asyncio.run(add_decisions_table())
