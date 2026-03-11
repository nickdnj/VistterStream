"""
Database migration: Add YouTube OAuth fields to streaming_destinations table

Run this migration to add OAuth credential and connection state columns
for the youtube_oauth platform type.

Usage:
    python backend/migrations/add_youtube_oauth_fields.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from models.database import Base, DATABASE_URL


def run_migration():
    """Add YouTube OAuth fields to streaming_destinations table"""

    print("=" * 60)
    print("YouTube OAuth Fields Migration")
    print("=" * 60)
    print()

    engine = create_engine(DATABASE_URL)

    print(f"Connected to database: {DATABASE_URL}")
    print()

    migrations = [
        ("youtube_oauth_client_id", "TEXT"),
        ("youtube_oauth_client_secret_enc", "TEXT"),
        ("youtube_oauth_redirect_uri", "TEXT"),
        ("youtube_oauth_refresh_token_enc", "TEXT"),
        ("youtube_oauth_connected", "BOOLEAN DEFAULT 0"),
        ("youtube_oauth_channel_name", "TEXT"),
        ("youtube_oauth_token_expires_at", "DATETIME"),
    ]

    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='streaming_destinations'"
        ))
        if not result.fetchone():
            print("Table 'streaming_destinations' does not exist yet.")
            print("Creating all tables from models...")
            Base.metadata.create_all(bind=engine)
            print("All tables created successfully")
            return

        # Get existing columns
        result = conn.execute(text("PRAGMA table_info(streaming_destinations)"))
        existing_columns = {row[1] for row in result.fetchall()}

        print(f"Existing columns: {', '.join(sorted(existing_columns))}")
        print()

        added_count = 0
        skipped_count = 0

        for column_name, column_type in migrations:
            if column_name in existing_columns:
                print(f"  Skipping '{column_name}' (already exists)")
                skipped_count += 1
                continue

            try:
                sql = f"ALTER TABLE streaming_destinations ADD COLUMN {column_name} {column_type}"
                print(f"  Adding column: {column_name} ({column_type})")
                conn.execute(text(sql))
                conn.commit()
                added_count += 1
                print(f"    OK")
            except Exception as e:
                print(f"    Error: {e}")
                conn.rollback()

        print()
        print("=" * 60)
        print(f"Migration completed:")
        print(f"  - {added_count} columns added")
        print(f"  - {skipped_count} columns already existed")
        print("=" * 60)
        print()


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
