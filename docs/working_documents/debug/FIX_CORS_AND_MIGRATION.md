# Fix CORS and Migration Issues

## Issue 1: CORS Errors
The backend container needs to be restarted to pick up CORS configuration.

**Fix:**
```bash
cd ~/VistterStream/docker
docker-compose -f docker-compose.rpi.yml restart backend
```

Or if using docker compose (newer version):
```bash
cd ~/VistterStream/docker
docker compose -f docker-compose.rpi.yml restart backend
```

## Issue 2: Run Migration in Container
The migration needs to run inside the backend container where the database is accessible.

**Fix:**
```bash
# First, make sure you're in the VistterStream root directory
cd ~/VistterStream

# Run the migration inside the backend container
docker exec vistterstream-backend python migrations/add_youtube_oauth_credentials_fields.py
```

## Issue 3: Check if Database is Corrupted
If destinations are still missing after migration:

```bash
# Check backend logs for errors
docker logs vistterstream-backend --tail 50

# Check if the database file exists in the volume
docker exec vistterstream-backend ls -la /data/

# Verify database integrity
docker exec vistterstream-backend python -c "from models.database import SessionLocal; from models.destination import StreamingDestination; db = SessionLocal(); print(f'Destinations: {db.query(StreamingDestination).count()}'); db.close()"
```

## Verify Everything Works
After restarting and running migration:

1. Check backend is running: `docker ps | grep backend`
2. Check CORS in backend logs: `docker logs vistterstream-backend | grep CORS`
3. Try accessing the frontend and check browser console for CORS errors





