#!/usr/bin/env python3
"""
Migrate streams table to use destination_id instead of direct destination fields
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from models.database import engine, SessionLocal
from sqlalchemy import text

def migrate():
    """Drop and recreate streams table with new schema"""
    
    print("🔄 Migrating streams table to use destination_id...")
    
    db = SessionLocal()
    
    try:
        # Drop the streams table
        print("  - Dropping old streams table...")
        db.execute(text("DROP TABLE IF EXISTS streams"))
        db.commit()
        
        # Recreate with new schema explicitly
        print("  - Creating new streams table with destination_id...")
        create_table_sql = """
        CREATE TABLE streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR NOT NULL,
            camera_id INTEGER NOT NULL,
            destination_id INTEGER NOT NULL,
            resolution VARCHAR DEFAULT '1920x1080',
            bitrate VARCHAR DEFAULT '4500k',
            framerate INTEGER DEFAULT 30,
            status VARCHAR DEFAULT 'stopped',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME,
            started_at DATETIME,
            stopped_at DATETIME,
            last_error VARCHAR,
            FOREIGN KEY (camera_id) REFERENCES cameras(id),
            FOREIGN KEY (destination_id) REFERENCES streaming_destinations(id)
        )
        """
        db.execute(text(create_table_sql))
        db.commit()
        
        print("✅ Migration complete!")
        print("\nStreams table now uses destination_id to reference streaming_destinations")
        print("Old streams have been deleted. Create new ones using the Destinations.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

