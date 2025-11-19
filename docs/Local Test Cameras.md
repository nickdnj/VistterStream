# Local Test Cameras

This document provides example camera configurations for testing VistterStream. Replace credentials with your actual camera usernames and passwords.

## Reolink (Fixed position camera)

* **Main Stream:** `rtsp://username:password@192.168.86.24:554/Preview_01_main`  
* **Snapshot:** `http://username:password@192.168.86.24:80/cgi-bin/api.cgi?cmd=onvifSnapPic&channel=0`

## Sunba (PTZ camera with ONVIF support)

* **Main Stream:** `rtsp://192.168.86.250:554/user=admin_password=password_channel=0_stream=0&onvif=0.sdp?real_stream`  
* **Snapshot:** `http://192.168.86.250/webcapture.jpg?command=snap&channel=0&user=admin&password=password`

