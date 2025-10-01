"""
Startup script for VistterStream backend
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.database import create_tables
from main import app
import uvicorn

if __name__ == "__main__":
    # Create database tables
    create_tables()
    
    # Start the server
    uvicorn.run(
        app,  # Pass app directly instead of string when reload is disabled
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled reload to avoid import issues
        log_level="info"
    )
