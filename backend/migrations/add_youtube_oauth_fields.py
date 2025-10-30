"""Database migration: Add YouTube OAuth fields to streaming_destinations table"""

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import Base, DATABASE_URL  # noqa: E402


def run_migration():
    print("=" * 60)
    print("YouTube OAuth Fields Migration")
    print("=" * 60)
    print()

    engine = create_engine(DATABASE_URL)
    print(f"Connected to database: {DATABASE_URL}")
    print()

    columns = [
        ("youtube_access_token", "TEXT"),
        ("youtube_refresh_token", "TEXT"),
        ("youtube_token_expiry", "DATETIME"),
        ("youtube_oauth_scope", "TEXT"),
        ("youtube_oauth_state", "TEXT"),
    ]

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='streaming_destinations'")
        )
        if not result.fetchone():
            print("⚠️  Table 'streaming_destinations' not found. Creating tables from models...")
            Base.metadata.create_all(bind=engine)
            print("✅ Tables created")
            return

        result = conn.execute(text("PRAGMA table_info(streaming_destinations)"))
        existing_columns = {row[1] for row in result.fetchall()}
        print(f"Existing columns: {', '.join(sorted(existing_columns))}")
        print()

        added = 0
        skipped = 0
        for column_name, column_type in columns:
            if column_name in existing_columns:
                print(f"⏭️  Skipping '{column_name}' (already exists)")
                skipped += 1
                continue

            try:
                sql = f"ALTER TABLE streaming_destinations ADD COLUMN {column_name} {column_type}"
                print(f"➕ Adding column: {column_name} ({column_type})")
                conn.execute(text(sql))
                conn.commit()
                added += 1
                print("   ✅ Success")
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                print(f"   ❌ Failed to add column '{column_name}': {exc}")

        print()
        print("=" * 60)
        print("Migration completed")
        print(f"  - {added} column(s) added")
        print(f"  - {skipped} column(s) skipped")
        print("=" * 60)


if __name__ == "__main__":
    run_migration()
