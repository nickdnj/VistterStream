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

from utils.logging_config import configure_logging
configure_logging()

import logging
logger = logging.getLogger(__name__)

from models.database import create_tables, SessionLocal, User, engine, DATABASE_URL
from routers.auth import get_user_by_username, get_password_hash
from main import app
import uvicorn
from sqlalchemy import text
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

def ensure_preset_token_column() -> None:
    """Ensure the presets table has a camera_preset_token column."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(presets)"))
            columns = [row[1] for row in result]
            if "camera_preset_token" not in columns:
                connection.execute(text("ALTER TABLE presets ADD COLUMN camera_preset_token TEXT"))
    except Exception as exc:
        logger.warning("Unable to update presets schema: %s", exc)


def ensure_streaming_destination_channel_column() -> None:
    """Ensure the streaming_destinations table has a channel_id column."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(streaming_destinations)"))
            columns = [row[1] for row in result]
            if "channel_id" not in columns:
                connection.execute(text("ALTER TABLE streaming_destinations ADD COLUMN channel_id TEXT"))
    except Exception as exc:
        logger.warning("Unable to update streaming_destinations schema: %s", exc)


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
                    logger.info("Added missing column '%s' to streaming_destinations", column_name)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Unable to add column '%s' to streaming_destinations: %s", column_name, exc)
    except Exception as exc:
        logger.warning("Unable to update streaming_destinations OAuth schema: %s", exc)


def ensure_preset_thumbnail_column() -> None:
    """Ensure the presets table has a thumbnail_path column."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(presets)"))
            columns = [row[1] for row in result]
            if "thumbnail_path" not in columns:
                connection.execute(text("ALTER TABLE presets ADD COLUMN thumbnail_path TEXT"))
    except Exception as exc:
        logger.warning("Unable to update presets schema for thumbnails: %s", exc)


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
                    logger.info("Added missing column '%s' to timelines", column_name)
                except Exception as exc:
                    logger.warning("Unable to add column '%s' to timelines: %s", column_name, exc)
    except Exception as exc:
        logger.warning("Unable to update timelines broadcast schema: %s", exc)


def ensure_tempest_url_port_fix() -> None:
    """Fix legacy 8085 port in tempest_api_url to 8036."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("PRAGMA table_info(reelforge_settings)"))
            columns = {row[1] for row in result}
            if "tempest_api_url" in columns:
                connection.execute(
                    text(
                        "UPDATE reelforge_settings SET tempest_api_url = REPLACE(tempest_api_url, :old_port, :new_port) "
                        "WHERE tempest_api_url LIKE :pattern"
                    ),
                    {"old_port": ":8085", "new_port": ":8036", "pattern": "%:8085%"},
                )
    except Exception as exc:
        logger.warning("Unable to fix tempest_api_url port: %s", exc)


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
                logger.info("Reset password for admin user '%s'", username)
            # If no env var and user exists, leave it alone
        else:
            # No admin exists — create one
            if not password:
                password = secrets.token_urlsafe(16)
                logger.warning("=" * 60)
                logger.warning("*** INITIAL ADMIN PASSWORD: %s ***", password)
                logger.warning("Change this immediately via Settings > Change Password")
                logger.warning("=" * 60)
            admin_user = User(username=username, password_hash=get_password_hash(password))
            db.add(admin_user)
            db.commit()
            logger.info("Created admin user '%s'", username)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create/reset default admin user: %s", exc, exc_info=True)
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
                    logger.info("Copied existing SQLite database from %s to %s", legacy_path, target_path)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unable to copy legacy database from %s: %s", legacy_path, exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("SQLite database bootstrap failed: %s", exc)


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
            logger.info("Encrypted secrets for %d destination(s)", updated)
        db.close()
    except Exception as e:
        logger.warning("Could not encrypt destination secrets: %s", e)


def ensure_shortforge_timeline_id_column() -> None:
    """Add timeline_id column to shortforge_config if missing."""
    try:
        db = SessionLocal()
        cols = [r[1] for r in db.execute(text("PRAGMA table_info(shortforge_config)")).fetchall()]
        if "timeline_id" not in cols:
            db.execute(text("ALTER TABLE shortforge_config ADD COLUMN timeline_id INTEGER"))
            db.commit()
            logger.info("Added timeline_id column to shortforge_config")
        db.close()
    except Exception as e:
        logger.warning("Could not ensure timeline_id: %s", e)


def ensure_shortforge_capture_windows_column() -> None:
    """Add capture_windows_json column and seed defaults if missing."""
    import json as _json
    try:
        db = SessionLocal()
        # Check if column exists
        cols = [r[1] for r in db.execute(text("PRAGMA table_info(shortforge_config)")).fetchall()]
        if "capture_windows_json" not in cols:
            db.execute(text("ALTER TABLE shortforge_config ADD COLUMN capture_windows_json TEXT"))
            db.commit()
            logger.info("Added capture_windows_json column to shortforge_config")

        # Seed defaults if empty
        row = db.execute(text("SELECT id, capture_windows_json FROM shortforge_config LIMIT 1")).fetchone()
        if row and not row[1]:
            defaults = _json.dumps([
                {"name": "morning_golden", "label": "Morning Golden Hour", "reference": "sunrise", "offset_minutes": 0, "duration_minutes": 60, "enabled": True},
                {"name": "midday_1", "label": "Late Morning", "reference": "sunrise", "offset_minutes": 180, "duration_minutes": 120, "enabled": True},
                {"name": "midday_2", "label": "Early Afternoon", "reference": "sunset", "offset_minutes": -240, "duration_minutes": 120, "enabled": True},
                {"name": "evening_golden", "label": "Evening Golden Hour", "reference": "sunset", "offset_minutes": -60, "duration_minutes": 60, "enabled": True},
            ])
            db.execute(text("UPDATE shortforge_config SET capture_windows_json = :val WHERE id = :id"), {"val": defaults, "id": row[0]})
            db.commit()
            logger.info("Seeded default capture windows")
        db.close()
    except Exception as e:
        logger.warning("Could not ensure capture_windows_json: %s", e)


def ensure_moment_preset_id_column() -> None:
    """Add preset_id column to moments if missing."""
    try:
        db = SessionLocal()
        cols = [r[1] for r in db.execute(text("PRAGMA table_info(moments)")).fetchall()]
        if "preset_id" not in cols:
            db.execute(text("ALTER TABLE moments ADD COLUMN preset_id INTEGER"))
            db.commit()
            logger.info("Added preset_id column to moments")
        db.close()
    except Exception as exc:
        logger.warning("ensure_moment_preset_id_column: %s", exc)


def ensure_narration_config_columns() -> None:
    """Add narration config columns to shortforge_config if missing."""
    columns_to_add = [
        ("narration_voice", "TEXT DEFAULT 'shimmer'"),
        ("narration_speed", "REAL DEFAULT 0.95"),
        ("narration_persona", "TEXT DEFAULT 'chill_surfer'"),
        ("narration_prompt", "TEXT"),
        ("text_position", "TEXT DEFAULT 'upper'"),
        ("image_enhance", "TEXT DEFAULT 'vivid'"),
    ]
    try:
        db = SessionLocal()
        cols = [r[1] for r in db.execute(text("PRAGMA table_info(shortforge_config)")).fetchall()]
        for column_name, column_type in columns_to_add:
            if column_name not in cols:
                db.execute(text(f"ALTER TABLE shortforge_config ADD COLUMN {column_name} {column_type}"))
                logger.info("Added %s column to shortforge_config", column_name)
        db.commit()
        db.close()
    except Exception as e:
        logger.warning("Could not ensure narration config columns: %s", e)


def ensure_shortforge_thresholds_fix() -> None:
    """Fix ShortForge detection thresholds — original defaults (0.6, 0.5, 0.7) were too high."""
    try:
        db = SessionLocal()
        row = db.execute(
            text("SELECT id, motion_threshold, brightness_threshold, activity_threshold FROM shortforge_config LIMIT 1")
        ).fetchone()
        if row and row[1] is not None and row[1] >= 0.5:
            db.execute(
                text("UPDATE shortforge_config SET motion_threshold = 0.05, brightness_threshold = 0.15, activity_threshold = 0.10 WHERE id = :id"),
                {"id": row[0]},
            )
            db.commit()
            logger.info("Fixed ShortForge thresholds: motion=0.05, brightness=0.15, activity=0.10")
        db.close()
    except Exception as e:
        logger.warning("Could not fix ShortForge thresholds: %s", e)


def run_alembic_migrations() -> None:
    """Run Alembic migrations to bring the database schema up to date.

    On first run against an existing database (pre-Alembic), this stamps
    the current revision so that future migrations apply cleanly.
    """
    try:
        alembic_cfg = AlembicConfig(str(backend_dir / "alembic.ini"))
        # Override the script location to be absolute
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
        # Use the same DATABASE_URL as the app
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        # Check if this is a pre-existing database without Alembic version tracking.
        # If so, stamp it at head so future migrations apply cleanly.
        from alembic.runtime.migration import MigrationContext
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            current_rev = ctx.get_current_revision()

        if current_rev is None:
            # Existing database, no Alembic history — stamp at head
            alembic_command.stamp(alembic_cfg, "head")
            logger.info("Alembic: stamped existing database at head")
        else:
            alembic_command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations applied")
    except Exception as exc:
        logger.warning("Alembic migration failed (falling back to legacy migrations): %s", exc)


if __name__ == "__main__":
    ensure_sqlite_database_seeded()
    # Create database tables
    create_tables()

    # Run Alembic migrations (handles new columns/tables going forward)
    run_alembic_migrations()

    # Legacy ensure_* functions kept for backward compatibility — they are
    # no-ops once the Alembic migration has already added the columns.
    ensure_preset_token_column()
    ensure_preset_thumbnail_column()
    ensure_streaming_destination_channel_column()
    ensure_streaming_destination_oauth_columns()
    ensure_timeline_broadcast_columns()
    ensure_tempest_url_port_fix()
    ensure_destination_secrets_encrypted()
    ensure_shortforge_thresholds_fix()
    ensure_shortforge_timeline_id_column()
    ensure_shortforge_capture_windows_column()
    ensure_moment_preset_id_column()
    ensure_narration_config_columns()
    ensure_default_admin()

    # Start the server
    uvicorn.run(
        app,  # Pass app directly instead of string when reload is disabled
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled reload to avoid import issues
        log_level="info",
        timeout_keep_alive=5,  # Close idle keep-alive connections after 5s (Slowloris mitigation)
    )
