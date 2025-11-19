# YouTube OAuth Connection Fix

## Problem Summary

The YouTube OAuth connection workflow was completing successfully (showing "Authorization Complete" message), but the application wasn't properly handling the connection or updating the UI to reflect the successful authorization.

## What Was Fixed

### 1. **Enhanced OAuth Callback Error Handling** (`backend/routers/destinations.py`)

**Before:** The OAuth callback endpoint would fail silently if there were any errors during token exchange, and users wouldn't know why the connection failed.

**After:** 
- Added comprehensive error handling with user-friendly HTML error pages
- Errors now show specific details about what went wrong (missing credentials, invalid tokens, etc.)
- Success page auto-closes after 3 seconds and notifies the parent window

### 2. **Implemented Window Messaging** (Backend & Frontend)

**Before:** The frontend only relied on polling every 5 seconds (up to 12 attempts = 1 minute) to detect OAuth completion.

**After:**
- OAuth success page now sends a `postMessage` to the parent window
- Frontend listens for this message and immediately refreshes the destination list
- Polling still works as a fallback for reliability
- Window auto-closes after showing success message

### 3. **Added OAuth Credential Validation** (`frontend/src/components/StreamingDestinations.tsx`)

**Before:** Users could click "Connect OAuth" even without proper credentials configured.

**After:**
- Frontend validates that OAuth credentials are set before starting the flow
- Shows a helpful dialog prompting users to configure credentials if missing
- Provides clear instructions on what's needed

### 4. **Improved UI Instructions and Feedback**

**Before:** Limited guidance on the OAuth process.

**After:**
- Added step-by-step instructions for the OAuth flow
- Added informational box explaining what OAuth credentials are for
- Added link to Google Cloud Console for obtaining credentials
- Better visual feedback during the process

## How to Use YouTube OAuth Connection

### Prerequisites

You need OAuth 2.0 credentials from Google Cloud. You can configure them either:
- **Per-destination** (stored in database, different credentials per destination)
- **Environment variables** (backend-wide, same credentials for all destinations)

### Getting OAuth Credentials from Google

1. **Visit [Google Cloud Console](https://console.cloud.google.com)**

2. **Create or select a project**
   - Click "Select a project" → "New Project"
   - Name it (e.g., "VistterStream YouTube Integration")

3. **Enable YouTube Data API v3**
   - Go to "APIs & Services" → "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

4. **Configure OAuth Consent Screen**
   - Go to "APIs & Services" → "OAuth consent screen"
   - User type: **External**
   - Fill in app name, email, etc.
   - Add scopes:
     - `https://www.googleapis.com/auth/youtube`
     - `https://www.googleapis.com/auth/youtube.readonly`
     - `https://www.googleapis.com/auth/youtubepartner`
   - Add test users (your Gmail address)

5. **Create OAuth Client Credentials**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: **Web application**
   - Add authorized redirect URI:
     ```
     http://your-backend-address:8000/api/destinations/youtube/oauth/callback
     ```
     Examples:
     - `http://localhost:8000/api/destinations/youtube/oauth/callback`
     - `http://192.168.1.100:8000/api/destinations/youtube/oauth/callback`
     - `https://your-domain.com/api/destinations/youtube/oauth/callback`
   
6. **Copy the credentials**
   - Client ID: `xxxxx.apps.googleusercontent.com`
   - Client Secret: `xxxxxx`

### Configuration Options

#### Option 1: Per-Destination Configuration (Recommended)

1. Open VistterStream → Streaming Destinations
2. Edit or create a YouTube destination
3. Scroll to "YouTube OAuth Credentials" section
4. Fill in:
   - **OAuth Client ID**: Your client ID from Google Cloud
   - **OAuth Client Secret**: Your client secret
   - **OAuth Redirect URI**: Must match what you configured in Google Cloud
     ```
     http://your-backend-address:8000/api/destinations/youtube/oauth/callback
     ```
5. Save the destination

#### Option 2: Backend Environment Variables

Add to your `.env` file or environment:

```bash
YOUTUBE_OAUTH_CLIENT_ID=xxxxx.apps.googleusercontent.com
YOUTUBE_OAUTH_CLIENT_SECRET=xxxxxx
YOUTUBE_OAUTH_REDIRECT_URI=http://your-backend:8000/api/destinations/youtube/oauth/callback
```

If using Docker, add these to your `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - YOUTUBE_OAUTH_CLIENT_ID=xxxxx.apps.googleusercontent.com
      - YOUTUBE_OAUTH_CLIENT_SECRET=xxxxxx
      - YOUTUBE_OAUTH_REDIRECT_URI=http://backend:8000/api/destinations/youtube/oauth/callback
```

### Connecting OAuth

1. **Navigate to Streaming Destinations**
   - Open VistterStream UI
   - Go to "Streaming Destinations" page

2. **Find your YouTube destination**
   - Look for the "YouTube OAuth" section in the destination card
   - Status will show "Not connected" if not yet authorized

3. **Click "Connect OAuth"**
   - A popup window will open with Google sign-in
   - If popup is blocked, allow popups for your VistterStream domain

4. **Authorize in Google**
   - Sign in with your YouTube account
   - Review and grant the requested permissions
   - Click "Allow"

5. **Confirmation**
   - You'll see "✅ Authorization Complete!" message
   - Popup will auto-close after 3 seconds
   - Status in VistterStream will update to "Connected" (green)
   - Token expiry time will be displayed

6. **If status doesn't update automatically**
   - Click the "Refresh Status" button
   - This manually checks the OAuth connection status

## Troubleshooting

### "OAuth credentials are not configured"

**Solution:** Fill in OAuth Client ID, Secret, and Redirect URI in either:
- The destination settings (per-destination)
- Backend environment variables

### "Authorization Failed - Invalid or expired OAuth state"

**Causes:**
- OAuth flow was started too long ago (state expired)
- Database state mismatch

**Solution:** Close the popup and click "Connect OAuth" again to restart the flow.

### "Failed to exchange OAuth code"

**Common causes:**
1. **Wrong Redirect URI**: The redirect URI in your destination settings must EXACTLY match what's configured in Google Cloud Console
2. **Invalid credentials**: Double-check your Client ID and Client Secret
3. **API not enabled**: Make sure YouTube Data API v3 is enabled in your Google Cloud project

**Solution:** 
- Verify redirect URI matches exactly (including protocol, host, port, path)
- Check credentials are correct
- Ensure YouTube Data API v3 is enabled

### "No refresh token returned"

**Cause:** Google only returns a refresh token on the first authorization or when forcing consent.

**Solution:** Click "Reconnect OAuth" (which forces consent prompt) or revoke app access in your Google Account settings and reconnect.

### Popup gets blocked

**Solution:** 
- Allow popups for your VistterStream domain
- Check browser settings/extensions that might block popups

### Status shows "Not connected" but I completed authorization

**Solutions:**
1. Click "Refresh Status" button to manually check
2. Refresh the entire page
3. Check browser console for error messages
4. Check backend logs: `docker logs vistterstream-backend --tail 50`

### Connection works but watchdog doesn't stream

Make sure you've also configured:
- YouTube Stream ID
- YouTube Broadcast ID
- Enable Watchdog toggle is ON
- Watchdog check interval is set

## Testing the Connection

After connecting OAuth, you can test it's working:

1. **Check OAuth Status**
   - Status badge should show "Connected" in green
   - Token expiry time should be displayed
   - Scopes should be listed

2. **Test API Access** (Optional)
   - If you have YouTube Stream ID configured, you can check stream health
   - The watchdog service will use this OAuth connection

3. **View Backend Logs**
   ```bash
   docker logs vistterstream-backend --tail 100
   ```
   Look for messages like:
   - `✅ Authorization Complete`
   - No error messages about OAuth

## What OAuth Enables

Once connected, VistterStream can:

- ✅ Automatically manage YouTube live broadcast lifecycle
- ✅ Transition broadcasts between testing/live/complete states
- ✅ Monitor stream health through YouTube API
- ✅ Perform frame probing to verify video is actually streaming
- ✅ Reset broadcasts daily (if enabled)
- ✅ Recover from stream failures automatically

## Security Notes

- OAuth credentials are stored in the database (per-destination) or environment variables
- Access tokens expire after ~1 hour but are automatically refreshed using the refresh token
- Refresh tokens are long-lived and stored securely
- Never share your Client Secret publicly
- You can revoke access anytime from your Google Account settings

## Changes Made to Codebase

### Backend Changes (`backend/routers/destinations.py`)
- Enhanced `youtube_oauth_callback()` endpoint with comprehensive error handling
- Added try-catch blocks for HTTPException and general exceptions
- Improved HTML response pages with better styling and error messages
- Added JavaScript postMessage to notify parent window on success
- Added auto-close timer (3 seconds) for success popup

### Frontend Changes (`frontend/src/components/StreamingDestinations.tsx`)
- Added event listener for OAuth completion messages (`window.addEventListener('message')`)
- Added validation check before starting OAuth flow
- Improved popup window handling with better error checking
- Enhanced UI with instructional boxes and setup guidance
- Added link to Google Cloud Console
- Improved OAuth credentials section with warning and setup instructions

## For Developers

If you need to debug the OAuth flow:

1. **Backend logs:**
   ```bash
   docker logs -f vistterstream-backend
   ```

2. **Frontend console:**
   - Open browser DevTools (F12)
   - Look for messages like "OAuth completed, refreshing destinations..."

3. **Test OAuth state endpoint:**
   ```bash
   curl http://localhost:8000/api/destinations/{destination_id}/youtube/oauth-status
   ```

4. **Database inspection:**
   ```bash
   docker exec vistterstream-backend python -c "from models.database import SessionLocal; from models.destination import StreamingDestination; db = SessionLocal(); dest = db.query(StreamingDestination).first(); print(f'OAuth connected: {dest.youtube_oauth_connected}'); print(f'Refresh token: {bool(dest.youtube_refresh_token)}'); db.close()"
   ```

## Summary

The OAuth connection flow is now much more robust with:
- ✅ Better error handling and user feedback
- ✅ Immediate UI updates via window messaging
- ✅ Clear instructions and validation
- ✅ Auto-closing success popup
- ✅ Comprehensive troubleshooting guidance

The connection now "works" completely - not just showing a success message, but actually saving the tokens and enabling full YouTube API integration for stream management!



