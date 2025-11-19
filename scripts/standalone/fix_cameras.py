#!/usr/bin/env python3
"""
Fix camera configurations with correct IPs and test them
Based on Local Test Cameras.md
"""

import requests
import json
import sys

API_BASE = "http://localhost:8000"

def login():
    """Login and get token"""
    print("🔑 Logging in...")
    response = requests.post(
        f"{API_BASE}/api/auth/login",
        data={
            "username": "admin",
            "password": "admin123"
        }
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Logged in successfully\n")
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        sys.exit(1)

def delete_all_cameras(token):
    """Delete all existing cameras"""
    print("🗑️  Deleting old cameras...")
    response = requests.get(
        f"{API_BASE}/api/cameras/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        cameras = response.json()
        for cam in cameras:
            print(f"   Deleting: {cam['name']} (ID: {cam['id']})")
            requests.delete(
                f"{API_BASE}/api/cameras/{cam['id']}",
                headers={"Authorization": f"Bearer {token}"}
            )
        print("✅ Old cameras deleted\n")

def add_reolink_camera(token):
    """Add Reolink camera with CORRECT IP (192.168.86.24)"""
    print("📷 Adding Reolink camera at 192.168.86.24...")
    
    camera_data = {
        "name": "Reolink Camera",
        "type": "stationary",
        "protocol": "rtsp",
        "address": "192.168.86.24",  # CORRECT IP!
        "username": "username",
        "password": "password",
        "port": 554,
        "stream_path": "/Preview_01_main",
        "snapshot_url": "http://192.168.86.24:80/cgi-bin/api.cgi?cmd=onvifSnapPic&channel=0"
    }
    
    response = requests.post(
        f"{API_BASE}/api/cameras/",
        json=camera_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        camera = response.json()
        print(f"✅ Reolink camera added (ID: {camera['id']})")
        print(f"   RTSP: rtsp://username:***@192.168.86.24:554/Preview_01_main\n")
        return camera
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}\n")
        return None

def add_sunba_camera(token):
    """Add Sunba PTZ camera with CORRECT IP (192.168.86.250)"""
    print("📷 Adding Sunba PTZ camera at 192.168.86.250...")
    
    camera_data = {
        "name": "Sunba PTZ",
        "type": "ptz",
        "protocol": "rtsp",
        "address": "192.168.86.250",  # CORRECT IP!
        "username": "admin",
        "password": "password",
        "port": 554,
        "stream_path": "/user=admin_password=password_channel=0_stream=0&onvif=0.sdp?real_stream",
        "snapshot_url": "http://192.168.86.250/webcapture.jpg?command=snap&channel=0&user=admin&password=password"
    }
    
    response = requests.post(
        f"{API_BASE}/api/cameras/",
        json=camera_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        camera = response.json()
        print(f"✅ Sunba PTZ camera added (ID: {camera['id']})")
        print(f"   RTSP: rtsp://admin:***@192.168.86.250:554/...\n")
        return camera
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}\n")
        return None

def test_camera(token, camera_id, camera_name):
    """Test camera connectivity with longer timeout"""
    print(f"🔍 Testing {camera_name}...")
    print(f"   (This may take up to 15 seconds per camera)")
    
    response = requests.post(
        f"{API_BASE}/api/cameras/{camera_id}/test",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30  # Allow time for the test
    )
    
    if response.status_code == 200:
        result = response.json()
        
        rtsp_status = "✅ WORKING" if result['rtsp_accessible'] else "❌ FAILED"
        snapshot_status = "✅ WORKING" if result['snapshot_accessible'] else "❌ FAILED"
        
        print(f"   RTSP Stream: {rtsp_status}")
        print(f"   Snapshot:    {snapshot_status}")
        
        if result.get('error_details'):
            print(f"   Details: {result['error_details']}")
        
        print()
        return result
    else:
        print(f"❌ Test request failed: {response.status_code}\n")
        return None

def test_snapshot_direct(camera_name, snapshot_url):
    """Test snapshot URL directly"""
    print(f"🖼️  Testing {camera_name} snapshot directly...")
    try:
        response = requests.get(snapshot_url, timeout=10)
        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
            print(f"   ✅ Snapshot working! Size: {len(response.content)} bytes\n")
            return True
        else:
            print(f"   ❌ Snapshot failed: HTTP {response.status_code}\n")
            return False
    except Exception as e:
        print(f"   ❌ Snapshot error: {e}\n")
        return False

def main():
    print("="*70)
    print("🔧 VistterStream Camera Configuration Fix")
    print("   Using CORRECT IPs from Local Test Cameras.md")
    print("="*70)
    print()
    
    token = login()
    
    # Delete old cameras with wrong IPs
    delete_all_cameras(token)
    
    # Add cameras with CORRECT IPs
    print("📸 Adding Cameras with Correct IPs:")
    print("-"*70)
    reolink = add_reolink_camera(token)
    sunba = add_sunba_camera(token)
    
    # Test direct snapshot URLs first
    print("="*70)
    print("📸 Testing Snapshot URLs Directly")
    print("="*70)
    print()
    
    test_snapshot_direct(
        "Reolink",
        "http://username:password@192.168.86.24:80/cgi-bin/api.cgi?cmd=onvifSnapPic&channel=0"
    )
    
    test_snapshot_direct(
        "Sunba PTZ",
        "http://192.168.86.250/webcapture.jpg?command=snap&channel=0&user=admin&password=password"
    )
    
    # Test cameras via API
    print("="*70)
    print("🎬 Testing Camera Connections via API")
    print("   (Using FFmpeg for RTSP, HTTP for snapshots)")
    print("="*70)
    print()
    
    if reolink:
        test_camera(token, reolink['id'], "Reolink Camera")
    
    if sunba:
        test_camera(token, sunba['id'], "Sunba PTZ")
    
    print("="*70)
    print("✅ Configuration Complete!")
    print("="*70)
    print()
    print("🌐 Open your browser: http://localhost:3000")
    print("🔑 Login: admin / admin123")
    print("📷 Check Camera Management page")
    print()
    print("="*70)

if __name__ == "__main__":
    main()

