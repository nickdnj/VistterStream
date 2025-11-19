# Deploying OAuth Connection Fix

## Changes Summary

- ✅ Backend: Enhanced OAuth callback error handling
- ✅ Frontend: Immediate OAuth status updates via window messaging
- ✅ UI: Better instructions and validation
- ✅ Documentation: Comprehensive guides

## Files Changed

- `backend/routers/destinations.py` - Enhanced OAuth callback
- `frontend/src/components/StreamingDestinations.tsx` - OAuth messaging & validation
- `docs/OAUTH_CONNECTION_FIX.md` - Complete guide (new)
- `OAUTH_FIX_SUMMARY.md` - Quick summary (new)

## Deployment Steps

### For Development (Local)

1. **Rebuild Frontend** (if using compiled build):
   ```bash
   cd frontend
   npm run build
   cd ..
   ```

2. **Restart Backend** (to pick up Python changes):
   ```bash
   # If running directly:
   # Stop the backend (Ctrl+C) and restart:
   cd backend
   python start.py
   
   # OR if using Docker:
   cd docker
   docker-compose restart backend
   ```

3. **Refresh Browser**:
   - Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)
   - Or clear cache and reload

### For Docker Deployment

#### Option 1: Restart Services (fastest)

```bash
cd /Users/nickd/Workspaces/VistterStream/docker

# Restart backend (Python changes)
docker-compose restart backend

# Rebuild and restart frontend (TypeScript changes)
docker-compose up -d --build frontend
```

#### Option 2: Full Rebuild (if restart doesn't work)

```bash
cd /Users/nickd/Workspaces/VistterStream

# Stop everything
docker-compose -f docker/docker-compose.yml down

# Rebuild images
docker-compose -f docker/docker-compose.yml build backend frontend

# Start everything
docker-compose -f docker/docker-compose.yml up -d
```

### For Raspberry Pi Deployment

```bash
cd ~/VistterStream/docker

# Restart backend
docker-compose -f docker-compose.rpi.yml restart backend

# Rebuild frontend
docker-compose -f docker-compose.rpi.yml up -d --build frontend
```

### Using the Force Rebuild Script

```bash
cd /Users/nickd/Workspaces/VistterStream
./force-rebuild.sh
```

## Verification Steps

After deployment:

1. **Check Backend is Running**:
   ```bash
   docker ps | grep backend
   # or
   curl http://localhost:8000/api/health
   ```

2. **Check Frontend Loaded**:
   - Open browser to http://localhost:3000 (or your frontend URL)
   - Open DevTools (F12) → Console
   - Should see no errors

3. **Test OAuth Flow**:
   - Go to Streaming Destinations
   - Open a YouTube destination (create one if needed)
   - Verify new UI elements are present:
     - Blue info box about OAuth credentials
     - Step-by-step instructions box
     - "How it works" section
   - Click "Connect OAuth" (will need valid credentials)
   - Should see validation or open popup

4. **Check Backend Logs** (if testing OAuth):
   ```bash
   docker logs vistterstream-backend --tail 50
   ```
   Look for any errors

## No Restart Needed For:

- ✅ Documentation files (`.md`)
- ✅ Already-running backend (Python auto-reloads if in dev mode)
- ✅ Frontend if using development server (`npm start`)

## Restart Needed For:

- ⚠️ Backend if running in production mode or Docker
- ⚠️ Frontend if using built/compiled version
- ⚠️ Browser cache (hard refresh recommended)

## Quick Test Without Full Restart

If you want to test quickly without restarting everything:

1. **Backend changes** will need a restart (Python doesn't hot-reload in production)
2. **Frontend changes** can be tested by:
   - Opening DevTools
   - Going to Application → Clear Storage → Clear site data
   - Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)

## Rollback (if needed)

If something breaks:

```bash
cd /Users/nickd/Workspaces/VistterStream

# See changes
git diff backend/routers/destinations.py
git diff frontend/src/components/StreamingDestinations.tsx

# Revert specific files
git checkout backend/routers/destinations.py
git checkout frontend/src/components/StreamingDestinations.tsx

# Then restart services
docker-compose -f docker/docker-compose.yml restart backend frontend
```

## Expected Behavior After Deployment

### In the UI (Streaming Destinations page):

1. **When editing/creating YouTube destination**:
   - Should see blue info box "🔐 Required for YouTube API Integration"
   - Link to Google Cloud Console visible
   - OAuth credential fields clearly labeled

2. **When viewing YouTube destination card**:
   - OAuth status section visible
   - "How it works" instruction box with 5 steps
   - Warning about configuring credentials

3. **When clicking "Connect OAuth"**:
   - If credentials missing: Alert dialog prompts to configure
   - If credentials present: Popup opens to Google OAuth
   - Browser console logs: "OAuth completed, refreshing destinations..."

4. **After completing OAuth in popup**:
   - Popup shows "✅ Authorization Complete!"
   - Popup auto-closes after 3 seconds
   - Main window status badge immediately turns green
   - Token expiry time displayed

### In Backend Logs:

```
✅ Authorization Complete
OAuth tokens saved for destination ID: X
```

### In Browser Console:

```
OAuth completed, refreshing destinations...
```

## Troubleshooting Deployment

**Backend changes not applying:**
```bash
# Force recreate container
docker-compose -f docker/docker-compose.yml up -d --force-recreate backend
```

**Frontend changes not applying:**
```bash
# Clear build cache and rebuild
docker-compose -f docker/docker-compose.yml build --no-cache frontend
docker-compose -f docker/docker-compose.yml up -d frontend
```

**Still showing old version:**
- Clear browser cache completely
- Try incognito/private window
- Check browser DevTools → Network tab → Disable cache
- Hard refresh multiple times

**Docker issues:**
```bash
# Check logs
docker logs vistterstream-backend
docker logs vistterstream-frontend

# Check if containers are running
docker ps

# Restart Docker daemon (last resort)
# On Mac: Docker Desktop → Restart
# On Linux: sudo systemctl restart docker
```

## Next Steps After Deployment

1. **Configure OAuth credentials** (if not already done)
   - See `OAUTH_FIX_SUMMARY.md` for setup guide
   - Or see `docs/OAUTH_CONNECTION_FIX.md` for detailed instructions

2. **Test the OAuth flow** with real Google account

3. **Monitor backend logs** during first OAuth connection to ensure everything works

4. **Configure YouTube broadcast settings** (Stream ID, Broadcast ID) for full functionality

---

**Ready to deploy!** These changes are backward compatible and won't break existing functionality. 🚀



