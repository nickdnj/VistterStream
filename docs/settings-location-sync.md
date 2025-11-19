# General Settings & Location Sync Documentation

## Overview

The General Settings feature provides a unified interface for configuring system-wide settings and location information. Location data entered in settings automatically syncs to all assets in the system, ensuring consistent metadata across the appliance.

## Features

### System Configuration
- **Appliance Name**: Customizable name for the VistterStream appliance
- **Timezone**: Selectable timezone for accurate scheduling and timestamps
  - Supports all major US timezones (EST, CST, MST, PST, etc.)
  - UTC option available for standardized timestamps

### Location Information
- **Automatic Detection**: Attempts to detect device location using browser geolocation API
  - Requires HTTPS for security (will fail on HTTP deployments)
  - Falls back to manual entry when auto-detection unavailable
- **Reverse Geocoding**: Converts GPS coordinates to human-readable city/state using OpenStreetMap Nominatim
- **Manual Override**: Users can edit city and state fields directly
- **Read-only Coordinates**: Latitude and longitude are auto-populated and displayed as read-only
- **Re-detection**: Button to trigger location detection again if needed
- **Asset Synchronization**: Location changes automatically propagate to all assets

## Architecture

### Database Schema

#### Settings Table
```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY,
    appliance_name TEXT DEFAULT 'VistterStream Appliance',
    timezone TEXT DEFAULT 'America/New_York',
    state_name TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Assets Table (Location Fields)
```sql
ALTER TABLE assets ADD COLUMN state_name TEXT;
ALTER TABLE assets ADD COLUMN city TEXT;
ALTER TABLE assets ADD COLUMN latitude REAL;
ALTER TABLE assets ADD COLUMN longitude REAL;
```

### API Endpoints

#### GET /api/settings/
**Description:** Retrieve current system settings

**Response:**
```json
{
  "id": 1,
  "appliance_name": "VistterStream Appliance",
  "timezone": "America/New_York",
  "state_name": "NJ",
  "city": "Monmouth Beach",
  "latitude": 40.335,
  "longitude": -73.984,
  "created_at": "2025-10-26T14:39:05.682129",
  "updated_at": "2025-10-26T14:55:58.289620"
}
```

**Notes:**
- If no settings exist, creates default settings automatically
- Trailing slash required to avoid 307 redirect

#### POST /api/settings/
**Description:** Update system settings and sync location to assets

**Request Body:**
```json
{
  "appliance_name": "VistterStream Appliance",
  "timezone": "America/New_York",
  "state_name": "NJ",
  "city": "Monmouth Beach",
  "latitude": 40.335,
  "longitude": -73.984
}
```

**Response:** Same as GET response with updated values

**Behavior:**
- Updates settings record with provided fields
- Automatically syncs location fields (state_name, city, latitude, longitude) to ALL assets
- Updates `last_updated` timestamp on affected assets
- Returns updated settings object

**Notes:**
- All fields are optional (only provided fields are updated)
- Location sync occurs only when location fields are provided
- Trailing slash required to avoid 307 redirect and CORS issues

## Frontend Implementation

### Location Detection Flow

1. **On Page Load:**
   - Fetch current settings from backend
   - If latitude/longitude are null, trigger auto-detection

2. **Auto-Detection Process:**
   ```javascript
   navigator.geolocation.getCurrentPosition(
     async (pos) => {
       const { latitude, longitude } = pos.coords;
       
       // Reverse geocode using Nominatim
       const response = await fetch(
         `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`
       );
       const data = await response.json();
       
       const state_name = data.address?.state || '';
       const city = data.address?.city || data.address?.town || '';
       
       // Update form state
       setGeneralSettings({ ...settings, latitude, longitude, city, state_name });
     },
     (error) => {
       console.warn("Location detection failed:", error.message);
       // Fallback to manual entry
     }
   );
   ```

3. **Fallback Behavior:**
   - If geolocation fails (HTTP, permission denied, timeout), users can manually enter city and state
   - Latitude/longitude remain null but can be populated later

### User Interface

**System Configuration Section:**
- Appliance Name input field
- Timezone dropdown with common options

**Location Information Section:**
- Help text: "📍 Location auto-detected where possible. You can override manually. Changes sync to all assets."
- City input (editable)
- State/Province input (editable)
- Latitude display (read-only, auto-detected)
- Longitude display (read-only, auto-detected)
- "Re-detect Location" button
- Detection status indicator while processing

**Save Button:**
- Triggers POST to `/api/settings/`
- Shows loading state ("Saving...")
- Displays success/error message after completion

## Deployment Notes

### Migration Required

When deploying this feature, run the database migration:

**On Host System:**
```bash
python3 backend/migrations/add_settings_and_location_fields.py
```

**Inside Docker Container:**
```bash
docker exec -it vistterstream-backend python /app/backend/migrations/add_settings_and_location_fields.py
```

The migration will:
- Create `settings` table if it doesn't exist
- Insert default settings row
- Add location columns to `assets` table
- Skip columns that already exist (idempotent)

### CORS Configuration

Ensure backend CORS configuration includes:
- Frontend origin (e.g., `http://192.168.12.107:3000`)
- Credentials allowed
- All methods allowed (GET, POST, OPTIONS)

### HTTPS Considerations

**Geolocation API Limitation:**
- Browser geolocation only works on HTTPS (secure origins)
- On HTTP deployments, auto-detection will fail with security error
- Users can still manually enter location data
- Consider setting up HTTPS for production deployments

## Troubleshooting

### "Failed to save settings" Error

**Symptoms:** POST request fails with CORS error or net::ERR_FAILED

**Causes:**
1. **Missing trailing slash:** Ensure API calls use `/api/settings/` (not `/api/settings`)
2. **Database migration not run:** Check backend logs for `no such column: assets.state_name`
3. **Container database mismatch:** Migration run on host but container uses different DB

**Solutions:**
```bash
# 1. Check backend logs
docker logs vistterstream-backend --tail 50

# 2. Run migration inside container
docker exec -it vistterstream-backend python /app/backend/migrations/add_settings_and_location_fields.py

# 3. Restart backend
docker restart vistterstream-backend

# 4. Verify migration success
docker exec -it vistterstream-backend sqlite3 /app/backend/vistterstream.db "PRAGMA table_info(assets);"
```

### Location Detection Not Working

**Error:** "Only secure origins are allowed"

**Cause:** Browser geolocation requires HTTPS

**Solution:** This is expected on HTTP deployments. Users should manually enter location data.

### Settings Not Loading

**Symptoms:** "Loading settings..." displays indefinitely

**Cause:** Backend API not accessible or returning errors

**Solutions:**
```bash
# Check backend health
curl http://localhost:8000/api/health

# Check settings endpoint
curl http://localhost:8000/api/settings/

# Restart backend if needed
docker restart vistterstream-backend
```

## Integration with Assets

When settings are saved with location data, the backend automatically:

1. Queries all assets: `db.query(Asset).all()`
2. Updates each asset with location fields:
   ```python
   for asset in assets:
       asset.state_name = settings.state_name
       asset.city = settings.city
       asset.latitude = settings.latitude
       asset.longitude = settings.longitude
       asset.last_updated = datetime.utcnow()
   ```
3. Commits changes to database
4. Logs sync confirmation: `✅ Synced location to N asset(s)`

This ensures all assets inherit the device location, useful for:
- Geographic metadata in streams
- Location-based overlay graphics
- Compliance and record-keeping
- Multi-location deployments

## Future Enhancements

Potential improvements for future versions:

- **Per-Asset Location Override:** Allow individual assets to have different locations
- **Timezone Auto-Detection:** Use browser timezone API to suggest appropriate timezone
- **HTTPS Setup Guide:** Documentation for enabling HTTPS on Raspberry Pi
- **Location History:** Track location changes over time
- **Weather Integration:** Use location data to fetch local weather for overlays
- **Geocoding Service Selection:** Option to use Google Maps API or other providers
- **Batch Asset Updates:** UI to review which assets will be updated before saving

## API Examples

### Retrieve Current Settings
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://192.168.12.107:8000/api/settings/
```

### Update Appliance Name Only
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"appliance_name": "Studio Camera System"}' \
  http://192.168.12.107:8000/api/settings/
```

### Update Location Data
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Monmouth Beach",
    "state_name": "NJ",
    "latitude": 40.335,
    "longitude": -73.984
  }' \
  http://192.168.12.107:8000/api/settings/
```

## Summary

The General Settings feature provides a centralized location for system configuration with intelligent location detection and automatic synchronization to assets. The implementation handles both automatic geolocation (when available) and manual entry, ensuring broad compatibility across deployment scenarios.

Key benefits:
- ✅ Unified settings interface
- ✅ Automatic location detection with fallback
- ✅ Asset synchronization for consistent metadata
- ✅ Timezone management for scheduling
- ✅ RESTful API for programmatic access
- ✅ Docker-compatible deployment






