# Debugging OAuth "Not Connected" Issue

## Symptoms
- OAuth flow completes and shows "It Works!" dialog
- Status remains "Not connected" (red)
- Frontend shows new UI but backend may not be updated

## Diagnostic Steps

### 1. Check if Backend Changes Were Applied

The fact that you see "It Works!" instead of "✅ Authorization Complete!" suggests the backend changes haven't been deployed yet.

**On Raspberry Pi, run:**

```bash
# Check if you pulled the latest changes
cd ~/VistterStream
git log --oneline -1
# Should show: 8429e8d Fix YouTube OAuth connection workflow

# Check if backend was restarted
docker logs vistterstream-backend --tail 5 | grep "Starting"
```

**If you haven't deployed yet:**

```bash
cd ~/VistterStream
git pull origin master
cd docker
docker-compose -f docker-compose.rpi.yml restart backend
docker-compose -f docker-compose.rpi.yml up -d --build frontend
```

### 2. Check OAuth Credentials Configuration

The warning says "Make sure OAuth credentials are configured above or set in backend environment variables."

**Option A: Check destination settings (edit the destination)**
- Scroll to "YouTube OAuth Credentials" section
- Verify these fields are filled:
  - OAuth Client ID: `xxxxx.apps.googleusercontent.com`
  - OAuth Client Secret: `xxxxxxx`
  - OAuth Redirect URI: `http://192.168.12.107:8000/api/destinations/youtube/oauth/callback`

**Option B: Check backend environment variables**

```bash
docker exec vistterstream-backend env | grep YOUTUBE_OAUTH
```

Should show:
```
YOUTUBE_OAUTH_CLIENT_ID=xxxxx.apps.googleusercontent.com
YOUTUBE_OAUTH_CLIENT_SECRET=xxxxxx
YOUTUBE_OAUTH_REDIRECT_URI=http://192.168.12.107:8000/api/destinations/youtube/oauth/callback
```

### 3. Check Backend Logs During OAuth

**Run this BEFORE clicking "Connect OAuth":**

```bash
# Follow backend logs in real-time
docker logs -f vistterstream-backend
```

Then click "Connect OAuth" and complete the flow. Look for:

**Expected (good):**
```
✅ Authorization Complete
OAuth tokens saved for destination ID: X
```

**Errors (bad):**
```
❌ YouTube OAuth environment variables are not fully configured
❌ Failed to exchange OAuth code
❌ OAuth state mismatch
❌ No refresh token returned
```

### 4. Check Database After OAuth

After completing the OAuth flow, check if tokens were saved:

```bash
docker exec vistterstream-backend python3 -c "
from models.database import SessionLocal
from models.destination import StreamingDestination

db = SessionLocal()
dest = db.query(StreamingDestination).filter(StreamingDestination.name == 'Vistter 2').first()

if dest:
    print(f'Destination: {dest.name}')
    print(f'OAuth Connected: {dest.youtube_oauth_connected}')
    print(f'Has Refresh Token: {bool(dest.youtube_refresh_token)}')
    print(f'Has Access Token: {bool(dest.youtube_access_token)}')
    print(f'Token Expiry: {dest.youtube_token_expiry}')
    print(f'OAuth Scopes: {dest.youtube_oauth_scope}')
else:
    print('Destination not found')
    
db.close()
"
```

**Expected output if working:**
```
Destination: Vistter 2
OAuth Connected: True
Has Refresh Token: True
Has Access Token: True
Token Expiry: 2025-10-31 23:45:00
OAuth Scopes: https://www.googleapis.com/auth/youtube ...
```

**If OAuth Connected is False:**
- Tokens weren't saved
- OAuth callback failed
- Credentials are misconfigured

### 5. Test OAuth Status Endpoint

```bash
# Replace X with your destination ID (probably 1 or 2)
curl http://192.168.12.107:8000/api/destinations/1/youtube/oauth-status
```

**Expected if connected:**
```json
{
  "connected": true,
  "expires_at": "2025-10-31T23:45:00",
  "scopes": "https://www.googleapis.com/auth/youtube ..."
}
```

**If not connected:**
```json
{
  "connected": false,
  "expires_at": null,
  "scopes": null
}
```

### 6. Common Issues

#### Issue 1: Backend Not Updated
**Symptom:** Seeing "It Works!" instead of "✅ Authorization Complete!"

**Fix:**
```bash
cd ~/VistterStream
git pull origin master
cd docker
docker-compose -f docker-compose.rpi.yml restart backend
```

#### Issue 2: Missing OAuth Credentials
**Symptom:** Error in logs: "YouTube OAuth environment variables are not fully configured"

**Fix:** Edit destination and fill in OAuth credentials, OR set environment variables

#### Issue 3: Wrong Redirect URI
**Symptom:** Error: "redirect_uri_mismatch" in popup

**Fix:** 
- In Google Cloud Console, the redirect URI must EXACTLY match
- Must be: `http://192.168.12.107:8000/api/destinations/youtube/oauth/callback`
- No trailing slash, exact protocol (http not https), exact host and port

#### Issue 4: No Refresh Token
**Symptom:** Error: "No refresh token returned"

**Fix:** 
- Click "Reconnect OAuth" (forces consent prompt)
- Or revoke app access in Google Account settings and reconnect

### 7. Manual OAuth Test

Try this step-by-step:

1. **Clear any existing OAuth state:**
   ```bash
   docker exec vistterstream-backend python3 -c "
   from models.database import SessionLocal
   from models.destination import StreamingDestination
   
   db = SessionLocal()
   dest = db.query(StreamingDestination).filter(StreamingDestination.name == 'Vistter 2').first()
   if dest:
       dest.youtube_oauth_state = None
       dest.youtube_access_token = None
       dest.youtube_refresh_token = None
       dest.youtube_token_expiry = None
       db.commit()
       print('Cleared OAuth state')
   db.close()
   "
   ```

2. **Start watching logs:**
   ```bash
   docker logs -f vistterstream-backend
   ```

3. **In another terminal, verify credentials are set:**
   ```bash
   # Check destination credentials
   docker exec vistterstream-backend python3 -c "
   from models.database import SessionLocal
   from models.destination import StreamingDestination
   
   db = SessionLocal()
   dest = db.query(StreamingDestination).filter(StreamingDestination.name == 'Vistter 2').first()
   if dest:
       print(f'Client ID: {bool(dest.youtube_oauth_client_id)}')
       print(f'Client Secret: {bool(dest.youtube_oauth_client_secret)}')
       print(f'Redirect URI: {dest.youtube_oauth_redirect_uri}')
   db.close()
   "
   ```

4. **Click "Connect OAuth" in UI**

5. **Complete authorization in popup**

6. **Check logs for errors**

## Quick Fix Checklist

- [ ] Git pull latest changes (`git pull origin master`)
- [ ] Backend restarted (`docker-compose restart backend`)
- [ ] Frontend rebuilt (`docker-compose up -d --build frontend`)
- [ ] OAuth credentials configured (in destination settings OR env vars)
- [ ] Redirect URI matches exactly in Google Cloud Console
- [ ] Backend logs show no errors during OAuth callback
- [ ] Database shows tokens saved after OAuth

## Next Steps

Run through steps 1-5 above and let me know:
1. What the backend logs show during OAuth
2. What the database query returns
3. Any error messages you see

This will help identify exactly where the OAuth flow is failing.



