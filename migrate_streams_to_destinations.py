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
        
        # Recreate with new schema (SQLAlchemy will handle this)
        from models.database import Base
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables['streams']])
        
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

