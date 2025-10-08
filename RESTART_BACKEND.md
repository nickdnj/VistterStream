# 🔄 Restart Backend to Fix Preview Warning

## The Issue
The preview server is running, but the backend health check needs to be updated to accept HTTP 401 (which MediaMTX returns for unauthenticated API calls).

## ✅ Fix Applied
Updated `backend/services/preview_server_health.py` to accept both 200 and 401 status codes as "healthy".

## 🚀 Action Required: Restart Backend

### In your backend terminal (where `python start.py` is running):

1. **Stop the backend**: Press `Ctrl+C`

2. **Start it again**:
```bash
cd /Users/nickd/Workspaces/VistterStream/backend
source ../venv/bin/activate
python start.py
```

3. **Refresh your browser** (Timeline Editor page)

4. **The warning should disappear!** ✅

---

## Expected Result

**Before**: 
```
⚠️ Preview server is not running. Check system status or start MediaMTX.
[Start Preview button disabled]
```

**After**:
```
[No warning]
[Start Preview button is BLUE and ENABLED]
```

---

## Verify Everything is Working

```bash
# 1. Check Docker container
docker ps | grep preview
# Should show: Up X seconds (healthy)

# 2. Check API
curl -I http://localhost:9997/v1/config/get
# Should show: HTTP/1.1 401 Unauthorized (this is OK!)

# 3. Check backend logs
# Should show: "✅ Preview server is healthy" in logs
```

---

## 🎬 Then Test Preview!

1. Select "Wharfside Waterfront" timeline
2. Click **"Start Preview"** (should be enabled now)
3. Video should appear within 5 seconds!

---

**Ready?** Restart your backend now! 🚀

