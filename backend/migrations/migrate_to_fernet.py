"""Migrate base64-encoded secrets to Fernet encryption.

Run once after deploying the Fernet encryption update.
Reads existing base64-encoded values from the database and re-encrypts them
with Fernet. The crypto.decrypt() function already handles legacy base64
values transparently, so this migration is optional but recommended to
ensure all stored secrets are properly encrypted.

Usage:
    ENCRYPTION_KEY=<key> python -m migrations.migrate_to_fernet
"""

import os
import sys

# Ensure ENCRYPTION_KEY is set before importing crypto
if not os.getenv("ENCRYPTION_KEY"):
    print("ERROR: ENCRYPTION_KEY environment variable must be set.")
    print("Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
    sys.exit(1)

from utils.crypto import encrypt, decrypt
from models.database import SessionLocal, Camera
from models.reelforge import ReelForgeSettings

def migrate():
    db = SessionLocal()
    migrated = 0

    try:
        # Migrate camera passwords
        cameras = db.query(Camera).filter(Camera.password_enc.isnot(None)).all()
        for camera in cameras:
            try:
                plaintext = decrypt(camera.password_enc)
                camera.password_enc = encrypt(plaintext)
                migrated += 1
            except Exception as e:
                print(f"  SKIP camera {camera.id} ({camera.name}): {e}")

        # Migrate ReelForge settings (YouTube secrets, OpenAI key)
        settings = db.query(ReelForgeSettings).all()
        for s in settings:
            for field in ["youtube_client_secret_enc", "youtube_refresh_token_enc", "openai_api_key_enc"]:
                val = getattr(s, field, None)
                if val:
                    try:
                        plaintext = decrypt(val)
                        setattr(s, field, encrypt(plaintext))
                        migrated += 1
                    except Exception as e:
                        print(f"  SKIP ReelForgeSettings.{field}: {e}")

        db.commit()
        print(f"Migrated {migrated} secret(s) to Fernet encryption.")

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
