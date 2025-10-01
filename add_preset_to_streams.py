#!/usr/bin/env python3
"""
Add preset_id column to streams table
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from models.database import engine, SessionLocal
from sqlalchemy import text
import os

# Make sure we're using the correct database
os.environ['DATABASE_URL'] = 'sqlite:///backend/vistterstream.db'

def migrate():
    """Add preset_id column to streams table"""
    
    print("🔄 Adding preset_id column to streams table...")
    
    db = SessionLocal()
    
    try:
        # Check if column already exists
        result = db.execute(text("PRAGMA table_info(streams)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'preset_id' in columns:
            print("✅ preset_id column already exists, no migration needed")
            return
        
        # Add the preset_id column
        print("  - Adding preset_id column...")
        db.execute(text("ALTER TABLE streams ADD COLUMN preset_id INTEGER"))
        
        # Add foreign key constraint (SQLite doesn't support adding foreign keys to existing tables)
        # The relationship will be enforced in the ORM
        
        db.commit()
        print("✅ Migration complete!")
        print("\nStreams table now supports optional PTZ presets")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
