"""
Startup script for VistterStream backend
"""

import sys
import os
import secrets
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
        ("youtube_oauth_client_id", "TEXT"),
        ("youtube_oauth_client_secret_enc", "TEXT"),
        ("youtube_oauth_redirect_uri", "TEXT"),
        ("youtube_oauth_refresh_token_enc", "TEXT"),
        ("youtube_oauth_connected", "BOOLEAN DEFAULT 0"),
        ("youtube_oauth_channel_name", "TEXT"),
        ("youtube_oauth_token_expires_at", "DATETIME"),
        ("youtube_oauth_code_verifier", "TEXT"),
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


def ensure_preset_thumbnail_column() -> None:
    """Ensure the presets table has a thumbnail_path column."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(presets)"))
            columns = [row[1] for row in result]
            if "thumbnail_path" not in columns:
                connection.execute(text("ALTER TABLE presets ADD COLUMN thumbnail_path TEXT"))
    except Exception as exc:
        print(f"⚠️ Unable to update presets schema for thumbnails: {exc}")


def ensure_timeline_broadcast_columns() -> None:
    """Ensure the timelines table has the broadcast metadata columns."""
    columns_to_add = [
        ("broadcast_title", "TEXT"),
        ("broadcast_description", "TEXT"),
        ("broadcast_tags", "TEXT"),
        ("broadcast_privacy", "TEXT DEFAULT 'public'"),
        ("broadcast_category_id", "TEXT"),
        ("broadcast_thumbnail_enabled", "BOOLEAN DEFAULT 1"),
    ]

    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(timelines)"))
            existing_columns = {row[1] for row in result}

            for column_name, column_type in columns_to_add:
                if column_name in existing_columns:
                    continue

                try:
                    sql = f"ALTER TABLE timelines ADD COLUMN {column_name} {column_type}"
                    connection.execute(text(sql))
                    print(f"✅ Added missing column '{column_name}' to timelines")
                except Exception as exc:
                    print(f"⚠️ Unable to add column '{column_name}' to timelines: {exc}")
    except Exception as exc:
        print(f"⚠️ Unable to update timelines broadcast schema: {exc}")


def ensure_tempest_url_port_fix() -> None:
    """Fix legacy 8085 port in tempest_api_url to 8036."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(reelforge_settings)"))
            columns = {row[1] for row in result}
            if "tempest_api_url" in columns:
                connection.execute(text(
                    "UPDATE reelforge_settings SET tempest_api_url = REPLACE(tempest_api_url, ':8085', ':8036') "
                    "WHERE tempest_api_url LIKE '%:8085%'"
                ))
    except Exception as exc:
        print(f"⚠️ Unable to fix tempest_api_url port: {exc}")


def ensure_default_admin():
    """Create or reset the default admin user.

    If DEFAULT_ADMIN_PASSWORD is set, use it (for automated deployments).
    If not set and no admin exists yet, generate a random password and print it.
    If not set and admin already exists, do nothing (don't reset).
    """
    username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD")

    db = SessionLocal()
    try:
        existing_user = get_user_by_username(db, username)

        if existing_user:
            if password:
                # Env var is set — reset password for automated deployments
                existing_user.password_hash = get_password_hash(password)
                existing_user.is_active = True
                db.commit()
                print(f"✅ Reset password for admin user '{username}'")
            # If no env var and user exists, leave it alone
        else:
            # No admin exists — create one
            if not password:
                password = secrets.token_urlsafe(16)
                print("=" * 60)
                print(f"*** INITIAL ADMIN PASSWORD: {password} ***")
                print("Change this immediately via Settings > Change Password")
                print("=" * 60)
            admin_user = User(username=username, password_hash=get_password_hash(password))
            db.add(admin_user)
            db.commit()
            print(f"✅ Created admin user '{username}'")
    except Exception as exc:
        db.rollback()
        print(f"❌ Failed to create/reset default admin user: {exc}")
        import traceback
        traceback.print_exc()
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


def ensure_destination_secrets_encrypted() -> None:
    """Encrypt any plaintext stream_key and youtube_api_key values in streaming_destinations."""
    from utils.crypto import encrypt

    try:
        db = SessionLocal()
        rows = db.execute(
            text("SELECT id, stream_key, youtube_api_key FROM streaming_destinations")
        ).fetchall()
        updated = 0
        for row in rows:
            dest_id, stream_key, api_key = row
            updates = {}
            # Check if stream_key is plaintext (not a Fernet token)
            if stream_key and not stream_key.startswith("gAAAAA"):
                updates["stream_key"] = encrypt(stream_key)
            # Check if youtube_api_key is plaintext
            if api_key and not api_key.startswith("gAAAAA"):
                updates["youtube_api_key"] = encrypt(api_key)
            if updates:
                set_clause = ", ".join(f"{k} = :v_{k}" for k in updates)
                params = {f"v_{k}": v for k, v in updates.items()}
                params["id"] = dest_id
                db.execute(text(f"UPDATE streaming_destinations SET {set_clause} WHERE id = :id"), params)
                updated += 1
        if updated:
            db.commit()
            print(f"🔒 Encrypted secrets for {updated} destination(s)")
        db.close()
    except Exception as e:
        print(f"⚠️ Could not encrypt destination secrets: {e}")


if __name__ == "__main__":
    ensure_sqlite_database_seeded()
    # Create database tables
    create_tables()
    ensure_preset_token_column()
    ensure_preset_thumbnail_column()
    ensure_streaming_destination_channel_column()
    ensure_streaming_destination_oauth_columns()
    ensure_timeline_broadcast_columns()
    ensure_tempest_url_port_fix()
    ensure_destination_secrets_encrypted()
    ensure_default_admin()

    # Start the server
    uvicorn.run(
        app,  # Pass app directly instead of string when reload is disabled
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled reload to avoid import issues
        log_level="info"
    )
