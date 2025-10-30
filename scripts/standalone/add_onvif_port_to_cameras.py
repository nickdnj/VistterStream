#!/usr/bin/env python3
"""
Add onvif_port column to cameras table and set intelligent defaults
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from models.database import engine, SessionLocal
from sqlalchemy import text

def migrate():
    """Add onvif_port column to cameras table"""
    
    print("🔄 Adding onvif_port column to cameras table...")
    
    db = SessionLocal()
    
    try:
        # Check if column already exists
        result = db.execute(text("PRAGMA table_info(cameras)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'onvif_port' in columns:
            print("✅ onvif_port column already exists, updating defaults...")
        else:
            # Add the onvif_port column
            print("  - Adding onvif_port column...")
            db.execute(text("ALTER TABLE cameras ADD COLUMN onvif_port INTEGER DEFAULT 80"))
            db.commit()
        
        # Update existing Sunba PTZ cameras to use port 8899
        print("  - Setting ONVIF port 8899 for Sunba PTZ cameras...")
        db.execute(text("""
            UPDATE cameras 
            SET onvif_port = 8899 
            WHERE type = 'ptz' AND (name LIKE '%Sunba%' OR name LIKE '%sunba%')
        """))
        db.commit()
        
        print("✅ Migration complete!")
        print("\nCamera ONVIF ports configured:")
        print("  - Sunba PTZ cameras: port 8899")
        print("  - Other cameras: port 80 (default)")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()


