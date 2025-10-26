"""
Database migration: Add Settings table and location fields to assets

Run this migration to create the settings table and add location fields 
to the assets table.

Usage:
    python backend/migrations/add_settings_and_location_fields.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from models.database import Base, DATABASE_URL


def run_migration():
    """Create settings table and add location fields to assets table"""
    
    print("=" * 60)
    print("Settings and Location Fields Migration")
    print("=" * 60)
    print()
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    print(f"Connected to database: {DATABASE_URL}")
    print()
    
    with engine.connect() as conn:
        # Check if settings table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
        ))
        settings_exists = result.fetchone() is not None
        
        if not settings_exists:
            print("➕ Creating 'settings' table...")
            create_settings_sql = """
            CREATE TABLE settings (
                id INTEGER PRIMARY KEY,
                appliance_name TEXT DEFAULT 'VistterStream Appliance',
                timezone TEXT DEFAULT 'America/New_York',
                state_name TEXT,
                city TEXT,
                latitude REAL,
                longitude REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            conn.execute(text(create_settings_sql))
            conn.commit()
            print("   ✅ Settings table created")
            
            # Insert default settings row
            print("➕ Inserting default settings row...")
            insert_sql = """
            INSERT INTO settings (appliance_name, timezone)
            VALUES ('VistterStream Appliance', 'America/New_York')
            """
            conn.execute(text(insert_sql))
            conn.commit()
            print("   ✅ Default settings created")
        else:
            print("⏭️  Settings table already exists")
        
        print()
        
        # Add location fields to assets table if it exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='assets'"
        ))
        if result.fetchone():
            # Get existing columns in assets table
            result = conn.execute(text("PRAGMA table_info(assets)"))
            existing_columns = {row[1] for row in result.fetchall()}
            
            print(f"Assets table existing columns: {', '.join(sorted(existing_columns))}")
            print()
            
            # List of columns to add to assets
            asset_migrations = [
                ("state_name", "TEXT"),
                ("city", "TEXT"),
                ("latitude", "REAL"),
                ("longitude", "REAL"),
            ]
            
            added_count = 0
            skipped_count = 0
            
            for column_name, column_type in asset_migrations:
                if column_name in existing_columns:
                    print(f"⏭️  Skipping 'assets.{column_name}' (already exists)")
                    skipped_count += 1
                    continue
                
                try:
                    sql = f"ALTER TABLE assets ADD COLUMN {column_name} {column_type}"
                    print(f"➕ Adding column to assets: {column_name} ({column_type})")
                    conn.execute(text(sql))
                    conn.commit()
                    added_count += 1
                    print(f"   ✅ Success")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    conn.rollback()
            
            print()
            print(f"Assets table: {added_count} columns added, {skipped_count} columns already existed")
        else:
            print("⚠️  Assets table does not exist yet.")
            print("Creating all tables from models...")
            Base.metadata.create_all(bind=engine)
            print("✅ All tables created successfully")
        
        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print()


if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

