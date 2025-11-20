"""
Migration script to add cloud_pairing_token, cloud_device_id, and cloud_api_url to settings table
"""
import sys
import os
from sqlalchemy import create_engine, text

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DATABASE_URL

def migrate():
    print(f"Connecting to database: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("PRAGMA table_info(settings)"))
        columns = [row[1] for row in result.fetchall()]
        
        if "cloud_pairing_token" not in columns:
            print("Adding cloud_pairing_token column...")
            conn.execute(text("ALTER TABLE settings ADD COLUMN cloud_pairing_token VARCHAR"))
        else:
            print("cloud_pairing_token column already exists")
            
        if "cloud_device_id" not in columns:
            print("Adding cloud_device_id column...")
            conn.execute(text("ALTER TABLE settings ADD COLUMN cloud_device_id VARCHAR"))
        else:
            print("cloud_device_id column already exists")
            
        if "cloud_api_url" not in columns:
            print("Adding cloud_api_url column...")
            conn.execute(text("ALTER TABLE settings ADD COLUMN cloud_api_url VARCHAR DEFAULT 'wss://api.vistterstudio.com/ws/device'"))
        else:
            print("cloud_api_url column already exists")
            
        conn.commit()
        print("Migration completed successfully")

if __name__ == "__main__":
    migrate()
