#!/usr/bin/env python3
"""
Reset admin user password to default (admin/admin)
This script will:
1. Delete existing admin user if it exists
2. Create a new admin user with password "admin"
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from models.database import SessionLocal, User
from routers.auth import get_password_hash, get_user_by_username

def reset_admin_password():
    """Reset admin user password"""
    db = SessionLocal()
    try:
        username = "admin"
        password = "admin"
        
        # Check if admin exists
        admin_user = get_user_by_username(db, username)
        
        if admin_user:
            print(f"Found existing admin user '{username}'")
            # Update password
            admin_user.password_hash = get_password_hash(password)
            db.commit()
            print(f"✅ Reset password for admin user '{username}'")
        else:
            print(f"Admin user '{username}' not found, creating new one...")
            # Create new admin user
            password_hash = get_password_hash(password)
            admin_user = User(username=username, password_hash=password_hash)
            db.add(admin_user)
            db.commit()
            print(f"✅ Created admin user '{username}' with password '{password}'")
        
        # Verify it works
        test_user = get_user_by_username(db, username)
        if test_user:
            print(f"✅ Verification: Admin user exists (ID: {test_user.id}, Active: {test_user.is_active})")
        else:
            print("❌ ERROR: Admin user not found after reset!")
            return False
            
        return True
        
    except Exception as exc:
        db.rollback()
        print(f"❌ Failed to reset admin password: {exc}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🔐 Resetting admin password...")
    success = reset_admin_password()
    sys.exit(0 if success else 1)

