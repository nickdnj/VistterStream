#!/usr/bin/env python3
"""
Test script to add cameras and validate connectivity
"""

import os
import requests
import json
import sys

API_BASE = "http://localhost:8000"


def admin_password():
    """Admin password comes from the environment, never from this file."""
    value = os.environ.get("VISTTER_ADMIN_PASSWORD")
    if not value:
        sys.exit("Set VISTTER_ADMIN_PASSWORD to the admin password before running this script.")
    return value

def create_user():
    """Create default admin user"""
    print("🔐 Creating admin user...")
    response = requests.post(
        f"{API_BASE}/api/auth/register",
        json={
            "username": "admin",
            "password": admin_password()
        }
    )
    if response.status_code == 200:
        print("✅ Admin user created")
        return response.json()
    else:
        print(f"ℹ️  User might already exist: {response.status_code}")
        return None

def login():
    """Login and get token"""
    print("\n🔑 Logging in...")
    response = requests.post(
        f"{API_BASE}/api/auth/login",
        data={
            "username": "admin",
            "password": admin_password()
        }
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Logged in successfully")
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        sys.exit(1)

def add_reolink_camera(token):
    """Add Reolink camera"""
    print("\n📷 Adding Reolink camera...")
    
    camera_data = {
        "name": "Reolink Camera",
        "type": "stationary",
        "protocol": "rtsp",
        "address": "192.168.86.24",
        "username": "username",
        "password": "password",
        "port": 554,
        "stream_path": "/Preview_01_main",
        "snapshot_url": "http://username:password@192.168.86.24:80/cgi-bin/api.cgi?cmd=onvifSnapPic&channel=0"
    }
    
    response = requests.post(
        f"{API_BASE}/api/cameras/",
        json=camera_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        camera = response.json()
        print(f"✅ Reolink camera added (ID: {camera['id']})")
        return camera
    else:
        print(f"❌ Failed to add Reolink: {response.status_code} - {response.text}")
        return None

def add_sunba_camera(token):
    """Add Sunba PTZ camera"""
    print("\n📷 Adding Sunba PTZ camera...")
    
    camera_data = {
        "name": "Sunba PTZ",
        "type": "ptz",
        "protocol": "rtsp",
        "address": "192.168.86.250",
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
        return camera
    else:
        print(f"❌ Failed to add Sunba: {response.status_code} - {response.text}")
        return None

def test_camera_connection(token, camera_id, camera_name):
    """Test camera connectivity"""
    print(f"\n🔍 Testing {camera_name} connectivity...")
    
    response = requests.post(
        f"{API_BASE}/api/cameras/{camera_id}/test",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   RTSP: {'✅ Accessible' if result['rtsp_accessible'] else '❌ Not accessible'}")
        print(f"   Snapshot: {'✅ Accessible' if result['snapshot_accessible'] else '❌ Not accessible'}")
        if result.get('error_details'):
            print(f"   Error: {result['error_details']}")
        return result
    else:
        print(f"❌ Test failed: {response.status_code}")
        return None

def get_all_cameras(token):
    """Get all cameras with status"""
    print("\n📋 Fetching all cameras...")
    
    response = requests.get(
        f"{API_BASE}/api/cameras/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        cameras = response.json()
        print(f"✅ Found {len(cameras)} camera(s)")
        for cam in cameras:
            print(f"   - {cam['name']} (ID: {cam['id']}, Type: {cam['type']}, Status: {cam['status']})")
        return cameras
    else:
        print(f"❌ Failed to get cameras: {response.status_code}")
        return []

def main():
    print("="*60)
    print("🎬 VistterStream Camera Setup & Testing")
    print("="*60)
    
    # Create user (might already exist)
    create_user()
    
    # Login
    token = login()
    
    # Add cameras
    reolink = add_reolink_camera(token)
    sunba = add_sunba_camera(token)
    
    # Get all cameras
    cameras = get_all_cameras(token)
    
    # Test connections
    if reolink:
        test_camera_connection(token, reolink['id'], "Reolink")
    
    if sunba:
        test_camera_connection(token, sunba['id'], "Sunba PTZ")
    
    print("\n" + "="*60)
    print("✅ Camera setup complete!")
    print("="*60)
    print("\n📱 Now open your browser to:")
    print("   🌐 http://localhost:3000")
    print("\n🔑 Login credentials:")
    print("   Username: admin")
    print("   Password: the value of VISTTER_ADMIN_PASSWORD")
    print("\n📷 You should see both cameras in the dashboard!")
    print("="*60)

if __name__ == "__main__":
    main()

