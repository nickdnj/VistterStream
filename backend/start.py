"""
Startup script for VistterStream backend
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.database import create_tables, SessionLocal, User
from routers.auth import get_user_by_username, get_password_hash
from main import app
import uvicorn


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


if __name__ == "__main__":
    # Create database tables
    create_tables()
    ensure_default_admin()

    # Start the server
    uvicorn.run(
        app,  # Pass app directly instead of string when reload is disabled
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled reload to avoid import issues
        log_level="info"
    )
