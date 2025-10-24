"""
Database migration: Add YouTube watchdog fields to streaming_destinations table

Run this migration to add YouTube API and watchdog configuration fields
to existing StreamingDestination records.

Usage:
    python backend/migrations/add_youtube_watchdog_fields.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, Column, Integer, String, Boolean, text
from models.database import Base, DATABASE_URL
from models.destination import StreamingDestination


def run_migration():
    """Add YouTube watchdog fields to streaming_destinations table"""
    
    print("=" * 60)
    print("YouTube Watchdog Fields Migration")
    print("=" * 60)
    print()
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    print(f"Connected to database: {DATABASE_URL}")
    print()
    
    # List of columns to add
    migrations = [
        ("channel_id", "TEXT"),
        ("enable_watchdog", "BOOLEAN DEFAULT 0"),
        ("youtube_api_key", "TEXT"),
        ("youtube_stream_id", "TEXT"),
        ("youtube_broadcast_id", "TEXT"),
        ("youtube_watch_url", "TEXT"),
        ("watchdog_check_interval", "INTEGER DEFAULT 30"),
        ("watchdog_enable_frame_probe", "BOOLEAN DEFAULT 0"),
        ("watchdog_enable_daily_reset", "BOOLEAN DEFAULT 0"),
        ("watchdog_daily_reset_hour", "INTEGER DEFAULT 3"),
    ]
    
    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='streaming_destinations'"
        ))
        if not result.fetchone():
            print("⚠️  Table 'streaming_destinations' does not exist yet.")
            print("Creating all tables from models...")
            Base.metadata.create_all(bind=engine)
            print("✅ All tables created successfully")
            return
        
        # Get existing columns
        result = conn.execute(text("PRAGMA table_info(streaming_destinations)"))
        existing_columns = {row[1] for row in result.fetchall()}
        
        print(f"Existing columns: {', '.join(sorted(existing_columns))}")
        print()
        
        # Add each column if it doesn't exist
        added_count = 0
        skipped_count = 0
        
        for column_name, column_type in migrations:
            if column_name in existing_columns:
                print(f"⏭️  Skipping '{column_name}' (already exists)")
                skipped_count += 1
                continue
            
            try:
                sql = f"ALTER TABLE streaming_destinations ADD COLUMN {column_name} {column_type}"
                print(f"➕ Adding column: {column_name} ({column_type})")
                conn.execute(text(sql))
                conn.commit()
                added_count += 1
                print(f"   ✅ Success")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                conn.rollback()
        
        print()
        print("=" * 60)
        print(f"Migration completed:")
        print(f"  - {added_count} columns added")
        print(f"  - {skipped_count} columns already existed")
        print("=" * 60)
        print()
        
        # Show sample record if any exist
        result = conn.execute(text("SELECT COUNT(*) FROM streaming_destinations"))
        count = result.fetchone()[0]
        
        if count > 0:
            print(f"ℹ️  Found {count} existing destination(s)")
            print("   These destinations now have watchdog fields available.")
            print("   Edit them via the API to enable watchdog monitoring.")
        else:
            print("ℹ️  No existing destinations found.")
            print("   Create YouTube destinations with watchdog enabled via the API.")
        
        print()


if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

