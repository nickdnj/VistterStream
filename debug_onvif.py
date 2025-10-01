#!/usr/bin/env python3
"""
Debug ONVIF connection to Sunba camera
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from onvif import ONVIFCamera
    from onvif.exceptions import ONVIFError
    print("✅ ONVIF library imported successfully")
except ImportError as e:
    print(f"❌ ONVIF import failed: {e}")
    sys.exit(1)

# Camera details
address = "192.168.86.250"
username = "admin"
password = "sOKDKxsV"

# Common ONVIF ports to try
ports_to_try = [80, 8000, 8080, 8899, 554, 37777, 34567]

for port in ports_to_try:
    print(f"\n🔍 Trying ONVIF on {address}:{port}")
    try:
        camera = ONVIFCamera(address, port, username, password)
        print(f"   ✅ ONVIFCamera created successfully")
        
        # Try to get device info
        device_mgmt = camera.create_devicemgmt_service()
        device_info = device_mgmt.GetDeviceInformation()
        print(f"   ✅ Device Info: {device_info.Manufacturer} {device_info.Model}")
        
        # Try to get capabilities
        capabilities = device_mgmt.GetCapabilities({'Category': 'All'})
        print(f"   ✅ Got capabilities")
        
        # Try PTZ service
        try:
            ptz_service = camera.create_ptz_service()
            print(f"   ✅ PTZ service created")
            
            # Get media profiles
            media_service = camera.create_media_service()
            profiles = media_service.GetProfiles()
            print(f"   ✅ Found {len(profiles)} media profiles")
            
            if profiles:
                profile = profiles[0]
                print(f"   📹 Using profile: {profile.Name}")
                
                # Try to get current position
                try:
                    request = ptz_service.create_type('GetStatus')
                    request.ProfileToken = profile.token
                    status = ptz_service.GetStatus(request)
                    
                    if status and status.Position:
                        pan = status.Position.PanTilt.x if status.Position.PanTilt else 0.0
                        tilt = status.Position.PanTilt.y if status.Position.PanTilt else 0.0
                        zoom = status.Position.Zoom.x if status.Position.Zoom else 1.0
                        print(f"   🎯 Current position: pan={pan}, tilt={tilt}, zoom={zoom}")
                    else:
                        print(f"   ⚠️  No position data available")
                        
                except Exception as e:
                    print(f"   ❌ PTZ GetStatus failed: {e}")
                    
        except Exception as e:
            print(f"   ❌ PTZ service failed: {e}")
            
        print(f"🎉 SUCCESS! ONVIF working on port {port}")
        break
        
    except ONVIFError as e:
        print(f"   ❌ ONVIF Error: {e}")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")

print("\n🏁 ONVIF debug complete")
