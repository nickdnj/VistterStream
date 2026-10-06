#!/usr/bin/env python3
"""
Test script to create and start a YouTube live stream
"""

import os
import sys
import requests
import json

API_BASE = "http://localhost:8000/api"


def admin_password():
    """Admin password comes from the environment, never from this file."""
    value = os.environ.get("VISTTER_ADMIN_PASSWORD")
    if not value:
        sys.exit("Set VISTTER_ADMIN_PASSWORD to the admin password before running this script.")
    return value

def login():
    """Login and get token"""
    response = requests.post(
        f"{API_BASE}/auth/login",
        data={"username": "admin", "password": admin_password()}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Logged in successfully\n")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        return None

def get_cameras(token):
    """Get available cameras"""
    response = requests.get(
        f"{API_BASE}/cameras/",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        cameras = response.json()
        return cameras
    else:
        print(f"❌ Failed to get cameras: {response.status_code}")
        return []

def create_youtube_stream(token, camera_id):
    """Create a YouTube stream configuration"""
    print("📺 Creating YouTube stream configuration...")
    
    # Your YouTube stream details from the screenshot
    stream_data = {
        "name": "Vistter Two Live Stream",
        "camera_id": camera_id,
        "destination": "youtube",
        "stream_key": "3fxp-wjv9-xxxa-94hd-0q3p",
        "rtmp_url": "rtmp://a.rtmp.youtube.com/live2",
        "resolution": "1920x1080",
        "bitrate": "4500k",
        "framerate": 30
    }
    
    response = requests.post(
        f"{API_BASE}/streams/",
        json=stream_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        stream = response.json()
        print(f"✅ Stream created (ID: {stream['id']})")
        print(f"   Name: {stream['name']}")
        print(f"   Camera ID: {stream['camera_id']}")
        print(f"   Destination: {stream['destination']}")
        print(f"   Resolution: {stream['resolution']} @ {stream['framerate']} FPS")
        print(f"   Bitrate: {stream['bitrate']}\n")
        return stream
    else:
        print(f"❌ Failed to create stream: {response.status_code}")
        print(f"   {response.text}\n")
        return None

def start_stream(token, stream_id):
    """Start the stream"""
    print(f"🚀 Starting stream {stream_id}...")
    
    response = requests.post(
        f"{API_BASE}/streams/{stream_id}/start",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        print(f"✅ Stream started!")
        print(f"   Go to YouTube Studio to see your live stream!")
        print(f"   https://studio.youtube.com/video/1ts0PCXAjUw/livestreaming\n")
        return True
    else:
        print(f"❌ Failed to start stream: {response.status_code}")
        print(f"   {response.text}\n")
        return False

def get_stream_status(token, stream_id):
    """Get stream status"""
    response = requests.get(
        f"{API_BASE}/streams/{stream_id}/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        status = response.json()
        print(f"📊 Stream Status:")
        print(f"   Status: {status['status']}")
        print(f"   Started: {status['started_at']}")
        if status.get('error_message'):
            print(f"   Error: {status['error_message']}")
        return status
    else:
        print(f"❌ Failed to get stream status: {response.status_code}")
        return None

def main():
    print("=" * 70)
    print("🎥 VistterStream → YouTube Live Stream Test")
    print("=" * 70)
    print()
    
    # Login
    token = login()
    if not token:
        return
    
    # Get cameras
    print("📷 Available Cameras:")
    cameras = get_cameras(token)
    for cam in cameras:
        print(f"   - ID {cam['id']}: {cam['name']} ({cam['status']})")
    print()
    
    if not cameras:
        print("❌ No cameras available!")
        return
    
    # Use first online camera
    online_camera = next((c for c in cameras if c['status'] == 'online'), None)
    if not online_camera:
        print("❌ No online cameras available!")
        print("   Run: python scripts/standalone/fix_cameras.py")
        return
    
    print(f"✅ Using camera: {online_camera['name']} (ID: {online_camera['id']})\n")
    
    # Create stream
    stream = create_youtube_stream(token, online_camera['id'])
    if not stream:
        return
    
    # Start stream
    if start_stream(token, stream['id']):
        # Wait a bit and check status
        import time
        time.sleep(2)
        get_stream_status(token, stream['id'])
    
    print()
    print("=" * 70)
    print("✨ Stream is live! Check YouTube Studio!")
    print("=" * 70)

if __name__ == "__main__":
    main()

