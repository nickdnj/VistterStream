"""
Database migration: Add error tracking fields to reel_capture_queue

Run this migration to add:
1. error_message column for storing failure details
2. attempt_count column for tracking retry attempts
3. last_attempt_at column for tracking when last attempt occurred

Usage:
    python backend/migrations/add_queue_error_fields.py
    
Or from Docker:
    docker exec -it vistterstream-backend python migrations/add_queue_error_fields.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from models.database import Base, DATABASE_URL


def run_migration():
    """Add error tracking columns to reel_capture_queue"""
    
    print("=" * 60)
    print("Queue Error Fields Migration")
    print("=" * 60)
    print()
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    print(f"Connected to database: {DATABASE_URL}")
    print()
    
    with engine.connect() as conn:
        # Check if table exists
        print("Step 1: Check reel_capture_queue Table")
        print("-" * 40)
        
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reel_capture_queue'"
        ))
        
        if not result.fetchone():
            print("Table 'reel_capture_queue' does not exist yet")
            print("It will be created with all columns when the app starts")
            return
        
        print("Table 'reel_capture_queue' exists")
        print()
        
        # Get existing columns
        result = conn.execute(text("PRAGMA table_info(reel_capture_queue)"))
        existing_columns = {row[1] for row in result.fetchall()}
        
        print(f"Existing columns: {', '.join(sorted(existing_columns))}")
        print()
        
        # Columns to add
        print("Step 2: Add Error Tracking Columns")
        print("-" * 40)
        
        new_columns = [
            ("error_message", "TEXT"),
            ("attempt_count", "INTEGER DEFAULT 0"),
            ("last_attempt_at", "DATETIME"),
        ]
        
        added_count = 0
        skipped_count = 0
        
        for column_name, column_type in new_columns:
            if column_name in existing_columns:
                print(f"Skipping '{column_name}' (already exists)")
                skipped_count += 1
                continue
            
            try:
                sql = f"ALTER TABLE reel_capture_queue ADD COLUMN {column_name} {column_type}"
                print(f"Adding column: {column_name} ({column_type})")
                conn.execute(text(sql))
                conn.commit()
                added_count += 1
                print(f"   Success")
            except Exception as e:
                print(f"   Error: {e}")
                conn.rollback()
        
        print()
        print(f"Result: {added_count} columns added, {skipped_count} already existed")
        
        print()
        print("=" * 60)
        print("Migration completed!")
        print("=" * 60)
        print()


if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
