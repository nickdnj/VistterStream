"""
Database migration: Add ReelForge settings table and capture queue fields

Run this migration to add:
1. reelforge_settings table for AI configuration
2. trigger_mode and scheduled_at columns to reel_capture_queue table

Usage:
    python backend/migrations/add_reelforge_settings.py
    
Or from Docker:
    docker exec -it vistterstream-backend python migrations/add_reelforge_settings.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from models.database import Base, DATABASE_URL


def run_migration():
    """Add ReelForge settings table and capture queue fields"""
    
    print("=" * 60)
    print("ReelForge Settings Migration")
    print("=" * 60)
    print()
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    print(f"Connected to database: {DATABASE_URL}")
    print()
    
    with engine.connect() as conn:
        # ========================================
        # 1. Create reelforge_settings table
        # ========================================
        print("Step 1: ReelForge Settings Table")
        print("-" * 40)
        
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reelforge_settings'"
        ))
        
        if result.fetchone():
            print("⏭️  Table 'reelforge_settings' already exists")
        else:
            print("➕ Creating 'reelforge_settings' table...")
            
            create_sql = """
            CREATE TABLE reelforge_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                openai_api_key_enc TEXT,
                openai_model TEXT DEFAULT 'gpt-4o-mini',
                system_prompt TEXT,
                temperature REAL DEFAULT 0.8,
                max_tokens INTEGER DEFAULT 500,
                default_template_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (default_template_id) REFERENCES reel_templates(id)
            )
            """
            
            try:
                conn.execute(text(create_sql))
                conn.commit()
                print("   ✅ Table created successfully")
            except Exception as e:
                print(f"   ❌ Error creating table: {e}")
                conn.rollback()
        
        print()
        
        # ========================================
        # 2. Add columns to reel_capture_queue
        # ========================================
        print("Step 2: Capture Queue Columns")
        print("-" * 40)
        
        # Check if table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reel_capture_queue'"
        ))
        
        if not result.fetchone():
            print("⏭️  Table 'reel_capture_queue' does not exist yet")
            print("   It will be created with all columns when the app starts")
        else:
            # Get existing columns
            result = conn.execute(text("PRAGMA table_info(reel_capture_queue)"))
            existing_columns = {row[1] for row in result.fetchall()}
            
            print(f"Existing columns: {', '.join(sorted(existing_columns))}")
            
            # Columns to add
            queue_columns = [
                ("trigger_mode", "TEXT DEFAULT 'next_view'"),
                ("scheduled_at", "DATETIME"),
            ]
            
            added_count = 0
            skipped_count = 0
            
            for column_name, column_type in queue_columns:
                if column_name in existing_columns:
                    print(f"⏭️  Skipping '{column_name}' (already exists)")
                    skipped_count += 1
                    continue
                
                try:
                    sql = f"ALTER TABLE reel_capture_queue ADD COLUMN {column_name} {column_type}"
                    print(f"➕ Adding column: {column_name} ({column_type})")
                    conn.execute(text(sql))
                    conn.commit()
                    added_count += 1
                    print(f"   ✅ Success")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    conn.rollback()
            
            print()
            print(f"Capture queue: {added_count} columns added, {skipped_count} already existed")
        
        print()
        print("=" * 60)
        print("Migration completed!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Refresh the ReelForge page in your browser")
        print("  2. Go to Settings tab to configure your OpenAI API key")
        print("  3. Create templates with AI content configuration")
        print()


if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
