"""
Database migration: Add weather integration fields to ReelForge settings

Run this migration to add:
1. tempest_api_url column to reelforge_settings table
2. weather_enabled column to reelforge_settings table

Usage:
    python backend/migrations/add_weather_integration.py
    
Or from Docker:
    docker exec -it vistterstream-backend python migrations/add_weather_integration.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from models.database import Base, DATABASE_URL


def run_migration():
    """Add weather integration columns to ReelForge settings"""
    
    print("=" * 60)
    print("Weather Integration Migration")
    print("=" * 60)
    print()
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    print(f"Connected to database: {DATABASE_URL}")
    print()
    
    with engine.connect() as conn:
        # ========================================
        # Check if reelforge_settings table exists
        # ========================================
        print("Step 1: Check ReelForge Settings Table")
        print("-" * 40)
        
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reelforge_settings'"
        ))
        
        if not result.fetchone():
            print("❌ Table 'reelforge_settings' does not exist!")
            print("   Please run add_reelforge_settings.py migration first")
            return
        
        print("✅ Table 'reelforge_settings' exists")
        print()
        
        # ========================================
        # Add weather columns
        # ========================================
        print("Step 2: Add Weather Integration Columns")
        print("-" * 40)
        
        # Get existing columns
        result = conn.execute(text("PRAGMA table_info(reelforge_settings)"))
        existing_columns = {row[1] for row in result.fetchall()}
        
        print(f"Existing columns: {', '.join(sorted(existing_columns))}")
        print()
        
        # Columns to add
        weather_columns = [
            ("tempest_api_url", "TEXT DEFAULT 'http://host.docker.internal:8085'"),
            ("weather_enabled", "BOOLEAN DEFAULT 1"),
        ]
        
        added_count = 0
        skipped_count = 0
        
        for column_name, column_type in weather_columns:
            if column_name in existing_columns:
                print(f"⏭️  Skipping '{column_name}' (already exists)")
                skipped_count += 1
                continue
            
            try:
                sql = f"ALTER TABLE reelforge_settings ADD COLUMN {column_name} {column_type}"
                print(f"➕ Adding column: {column_name} ({column_type})")
                conn.execute(text(sql))
                conn.commit()
                added_count += 1
                print(f"   ✅ Success")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                conn.rollback()
        
        print()
        print(f"Weather columns: {added_count} added, {skipped_count} already existed")
        
        print()
        print("=" * 60)
        print("Migration completed!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Ensure TempestWeather is running and accessible")
        print("  2. Go to ReelForge Settings to configure weather integration")
        print("  3. Test the connection using the 'Test Connection' button")
        print()
        print("TempestWeather must expose the /api/data endpoint.")
        print("See TempestWeather instructions for setting up this endpoint.")
        print()


if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
