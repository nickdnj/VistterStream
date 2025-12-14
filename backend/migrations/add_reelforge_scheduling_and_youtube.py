"""
Database migration: Add ReelForge scheduling and YouTube publishing fields

Run this migration to add:
- Scheduling fields to reel_posts
- YouTube OAuth fields to reelforge_settings

Usage:
    docker exec vistterstream-backend python backend/migrations/add_reelforge_scheduling_and_youtube.py
"""

import sqlite3
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_migration():
    """Add scheduling and YouTube fields"""
    
    # Database path
    db_path = os.environ.get("DATABASE_PATH", "/data/vistterstream.db")
    
    print("ReelForge Scheduling and YouTube Publishing Migration")
    print("=" * 55)
    print(f"Database: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # New columns for reel_posts table
    reel_posts_columns = [
        ("scheduled_capture_at", "DATETIME"),
        ("recurring_schedule", "TEXT"),  # JSON
        ("auto_publish", "BOOLEAN DEFAULT 0"),
        ("publish_platform", "TEXT"),
        ("publish_title", "TEXT"),
        ("publish_description", "TEXT"),
        ("publish_tags", "TEXT"),
        ("published_at", "DATETIME"),
        ("published_url", "TEXT"),
    ]
    
    # New columns for reelforge_settings table
    settings_columns = [
        ("youtube_client_id", "TEXT"),
        ("youtube_client_secret_enc", "TEXT"),
        ("youtube_refresh_token_enc", "TEXT"),
        ("youtube_connected", "BOOLEAN DEFAULT 0"),
        ("youtube_channel_name", "TEXT"),
    ]
    
    # Add columns to reel_posts
    print("\nAdding columns to reel_posts table...")
    for col_name, col_type in reel_posts_columns:
        try:
            cursor.execute(f"ALTER TABLE reel_posts ADD COLUMN {col_name} {col_type}")
            print(f"  Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  Column already exists: {col_name}")
            else:
                print(f"  Error adding {col_name}: {e}")
    
    # Add columns to reelforge_settings
    print("\nAdding columns to reelforge_settings table...")
    for col_name, col_type in settings_columns:
        try:
            cursor.execute(f"ALTER TABLE reelforge_settings ADD COLUMN {col_name} {col_type}")
            print(f"  Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  Column already exists: {col_name}")
            else:
                print(f"  Error adding {col_name}: {e}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 55)
    print("Migration complete!")
    print("\nNew capabilities:")
    print("  - Schedule one-time or recurring post captures")
    print("  - Auto-publish to YouTube Shorts")
    print("  - YouTube OAuth integration")


if __name__ == "__main__":
    run_migration()
