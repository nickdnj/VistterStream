"""
Startup script for VistterStream backend
"""

import sys
import os
import shutil
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.engine import make_url

from models.database import create_tables, SessionLocal, User, engine, DATABASE_URL
from routers.auth import get_user_by_username, get_password_hash
from main import app
import uvicorn
from sqlalchemy import text

def ensure_preset_token_column() -> None:
    """Ensure the presets table has a camera_preset_token column."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(presets)"))
            columns = [row[1] for row in result]
            if "camera_preset_token" not in columns:
                connection.execute(text("ALTER TABLE presets ADD COLUMN camera_preset_token TEXT"))
    except Exception as exc:
        print(f"⚠️ Unable to update presets schema: {exc}")


def ensure_streaming_destination_channel_column() -> None:
    """Ensure the streaming_destinations table has a channel_id column."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(streaming_destinations)"))
            columns = [row[1] for row in result]
            if "channel_id" not in columns:
                connection.execute(text("ALTER TABLE streaming_destinations ADD COLUMN channel_id TEXT"))
    except Exception as exc:
        print(f"⚠️ Unable to update streaming_destinations schema: {exc}")


def ensure_streaming_destination_oauth_columns() -> None:
    """Ensure the streaming_destinations table has the OAuth columns."""

    columns_to_add = [
        ("youtube_access_token", "TEXT"),
        ("youtube_refresh_token", "TEXT"),
        ("youtube_token_expiry", "DATETIME"),
        ("youtube_oauth_scope", "TEXT"),
        ("youtube_oauth_state", "TEXT"),
    ]

    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(streaming_destinations)"))
            existing_columns = {row[1] for row in result}

            for column_name, column_type in columns_to_add:
                if column_name in existing_columns:
                    continue

                try:
                    sql = f"ALTER TABLE streaming_destinations ADD COLUMN {column_name} {column_type}"
                    connection.execute(text(sql))
                    print(
                        f"✅ Added missing column '{column_name}' to streaming_destinations"
                    )
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"⚠️ Unable to add column '{column_name}' to streaming_destinations: {exc}"
                    )
    except Exception as exc:
        print(f"⚠️ Unable to update streaming_destinations OAuth schema: {exc}")


def ensure_default_admin():
    """Create a default admin user if none exists."""
    username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")

    if not username or not password:
        print("⚠️ DEFAULT_ADMIN_USERNAME or DEFAULT_ADMIN_PASSWORD not set; skipping admin bootstrap")
        return

    db = SessionLocal()
    try:
        if get_user_by_username(db, username):
            print(f"ℹ️ Admin user '{username}' already exists; skipping bootstrap")
            return

        password_hash = get_password_hash(password)
        admin_user = User(username=username, password_hash=password_hash)
        db.add(admin_user)
        db.commit()
        print(f"✅ Created default admin user '{username}'")
    except Exception as exc:
        db.rollback()
        print(f"❌ Failed to create default admin user: {exc}")
    finally:
        db.close()


def ensure_sqlite_database_seeded() -> None:
    """Ensure the SQLite database file exists when running inside Docker.

    Older deployments stored the SQLite file inside the application directory
    (e.g. ``/app/backend/vistterstream.db``). When we moved to mounting
    ``/data`` as a persistent volume, the new location can start empty on the
    first boot which caused previously defined destinations to disappear after
    a rebuild.

    When the configured ``DATABASE_URL`` points at a SQLite file that does not
    yet exist, we try to copy the legacy database into the new location before
    creating tables. This keeps existing data intact for users upgrading from
    the old layout.
    """

    try:
        url = make_url(DATABASE_URL)
        if url.get_backend_name() != "sqlite":
            return

        database = url.database
        if not database:
            return

        raw_path = Path(database)
        if not raw_path.is_absolute():
            target_path = (Path.cwd() / raw_path).resolve()
        else:
            target_path = raw_path

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.exists():
            return

        legacy_candidates = [
            Path("/app/backend/vistterstream.db"),
            Path("/app/vistterstream.db"),
            Path.cwd() / "vistterstream.db",
        ]

        for legacy_path in legacy_candidates:
            try:
                if legacy_path == target_path:
                    continue
                if legacy_path.exists() and legacy_path.is_file():
                    shutil.copy2(legacy_path, target_path)
                    print(
                        "📦 Copied existing SQLite database from"
                        f" {legacy_path} to {target_path}"
                    )
                    return
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ Unable to copy legacy database from {legacy_path}: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ SQLite database bootstrap failed: {exc}")


if __name__ == "__main__":
    ensure_sqlite_database_seeded()
    # Create database tables
    create_tables()
    ensure_preset_token_column()
    ensure_streaming_destination_channel_column()
    ensure_streaming_destination_oauth_columns()
    ensure_default_admin()

    # Start the server
    uvicorn.run(
        app,  # Pass app directly instead of string when reload is disabled
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled reload to avoid import issues
        log_level="info"
    )
