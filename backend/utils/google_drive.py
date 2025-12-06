"""
Google Drive utility functions for parsing and converting Google Drive Drawing URLs
"""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


def parse_google_drawing_url(url: str) -> Optional[str]:
    """
    Parse a Google Drive Drawing sharing URL and convert it to a PNG export URL.
    
    Handles various URL formats:
    - https://docs.google.com/drawings/d/{FILE_ID}/edit?usp=sharing
    - https://docs.google.com/drawings/d/{FILE_ID}/edit
    - https://docs.google.com/drawings/d/{FILE_ID}
    
    Args:
        url: Google Drive Drawing sharing URL
        
    Returns:
        PNG export URL if valid, None otherwise
    """
    if not url:
        return None
    
    # Pattern to match Google Drive Drawing URLs
    # Matches: /d/{FILE_ID}/ with optional /edit and query params
    pattern = r'/drawings/d/([a-zA-Z0-9_-]+)'
    
    match = re.search(pattern, url)
    if not match:
        return None
    
    file_id = match.group(1)
    
    # Construct PNG export URL
    export_url = f"https://docs.google.com/drawings/d/{file_id}/export/png"
    
    return export_url
