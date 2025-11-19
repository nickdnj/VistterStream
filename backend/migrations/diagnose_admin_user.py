#!/usr/bin/env python3
"""
Diagnostic script to check admin user status in the database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import SessionLocal, User
from routers.auth import get_password_hash, verify_password
import bcrypt

def diagnose_admin_user():
    """Check admin user status"""
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if not admin_user:
            print("❌ Admin user does not exist in database")
            return
        
        print(f"✅ Admin user found:")
        print(f"   ID: {admin_user.id}")
        print(f"   Username: {admin_user.username}")
        print(f"   Is Active: {admin_user.is_active}")
        print(f"   Password Hash Length: {len(admin_user.password_hash) if admin_user.password_hash else 0}")
        print(f"   Password Hash Preview: {admin_user.password_hash[:50] if admin_user.password_hash else 'None'}...")
        
        # Test password verification
        print("\n🔍 Testing password verification:")
        test_passwords = ["admin", "wrong", ""]
        
        for test_pwd in test_passwords:
            try:
                if not admin_user.password_hash:
                    print(f"   ❌ No password hash stored")
                    break
                
                # Try direct bcrypt
                result = bcrypt.checkpw(
                    test_pwd.encode('utf-8'),
                    admin_user.password_hash.encode('utf-8')
                )
                print(f"   Password '{test_pwd}': {'✅ MATCH' if result else '❌ NO MATCH'}")
            except Exception as e:
                print(f"   Password '{test_pwd}': ❌ ERROR - {e}")
        
        # Try to create a new hash
        print("\n🔧 Testing hash generation:")
        try:
            new_hash = get_password_hash("admin")
            print(f"   ✅ New hash generated: {new_hash[:50]}...")
            
            # Test the new hash
            test_result = verify_password("admin", new_hash)
            print(f"   ✅ New hash verification: {'PASS' if test_result else 'FAIL'}")
        except Exception as e:
            print(f"   ❌ Hash generation failed: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error diagnosing admin user: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnose_admin_user()


