# YouTube Studio Button - Quick Access Guide

## Overview

The Timeline Editor includes a **Studio** button that provides instant access to the YouTube Live Control Room for your active stream. This button dynamically constructs the correct YouTube Studio URL based on your channel configuration.

## How It Works

### URL Resolution Priority

The Studio button constructs URLs using the following fallback priority:

1. **Video/Stream ID** (Primary) - If a `youtube_stream_id` or `youtube_broadcast_id` is configured:
   ```
   https://studio.youtube.com/video/{VIDEO_ID}/livestreaming
   ```

2. **Channel ID** (Fallback) - If only a `channel_id` is configured:
   ```
   https://studio.youtube.com/channel/{CHANNEL_ID}/livestreaming
   ```

3. **Studio Homepage** (Last Resort) - If neither ID is configured:
   ```
   https://studio.youtube.com
   ```

### Button States

- **Enabled (Red)**: Appears when a YouTube destination is selected AND either a Stream ID or Channel ID is configured
- **Disabled (Gray)**: Appears when no YouTube destination is selected OR no IDs are configured
- **Hidden**: Button only appears when YouTube is in the active destination list

## Configuration

### Setting Up Stream IDs

To enable the Studio button with full functionality:

1. Navigate to **Settings → Streaming Destinations**
2. Select or create a YouTube destination
3. Fill in one or both of these fields:
   - **YouTube Stream ID**: The specific video/stream ID (preferred)
   - **Channel ID**: Your YouTube channel ID (fallback)

### Finding Your YouTube IDs

#### Stream ID / Video ID
1. Go to YouTube Studio: https://studio.youtube.com
2. Navigate to **Content → Live**
3. Click on your livestream
4. The URL will show your video ID: `studio.youtube.com/video/VIDEO_ID_HERE/livestreaming`

#### Channel ID
1. Go to YouTube Studio: https://studio.youtube.com
2. Click **Settings** (gear icon)
3. Select **Channel → Advanced settings**
4. Your Channel ID is displayed at the top

Alternatively, from your channel page, the URL contains your channel ID:
```
https://www.youtube.com/channel/YOUR_CHANNEL_ID
```

## Using the Studio Button

### In the Timeline Editor

1. **Select a Timeline**: Choose or create a timeline
2. **Select YouTube Destination**: Check the YouTube destination in the destination selector
3. **Click Studio ↗**: The button opens YouTube Studio in a new tab, taking you directly to:
   - Your specific livestream control room (if Stream ID is configured)
   - Your channel's livestreaming page (if only Channel ID is configured)

### Tooltip Information

Hover over the Studio button to see its status:
- **Enabled**: "Open YouTube Live Studio for this stream" or "Open YouTube Live Studio for this channel"
- **Disabled**: "Add Stream ID or Channel ID to destination to enable Studio link"

## Multiple Destinations

If you have multiple YouTube destinations configured:
- The Studio button uses the **first selected** YouTube destination
- If multiple YouTube channels are selected, only the first one determines the Studio URL
- Each destination can have its own Stream ID and Channel ID configuration

## Troubleshooting

### Button is Disabled

**Problem**: Studio button appears grayed out

**Solutions**:
1. Verify a YouTube destination is selected in the destination list
2. Check that the destination has either a Stream ID or Channel ID configured
3. Edit the destination in Settings → Streaming Destinations
4. Add at least one of: `youtube_stream_id`, `youtube_broadcast_id`, or `channel_id`

### Wrong Stream Opens

**Problem**: Studio button opens the wrong stream or channel

**Solutions**:
1. Verify the correct YouTube destination is selected
2. Update the Stream ID in the destination settings to match your current stream
3. If using multiple YouTube destinations, ensure only the intended one is selected

### Studio Button Missing

**Problem**: Studio button doesn't appear at all

**Solutions**:
1. Ensure you have at least one YouTube destination configured
2. Check that the YouTube destination is marked as active
3. Refresh the page to reload destination data

## Technical Details

### URL Construction Logic

```typescript
// Priority-based URL resolution
const youtubeStudioUrl = youtubeStreamId
  ? `https://studio.youtube.com/video/${youtubeStreamId}/livestreaming`
  : youtubeChannelId
  ? `https://studio.youtube.com/channel/${youtubeChannelId}/livestreaming`
  : 'https://studio.youtube.com';
```

### Destination Model Fields

The following fields from the Destination model are used for Studio URL construction:

- `youtube_stream_id` (string, optional): Specific stream/video ID
- `youtube_broadcast_id` (string, optional): Alternative stream ID field
- `channel_id` (string, optional): YouTube channel ID
- `platform` (string): Must be "youtube" for button to appear

### API Endpoints

Destinations are loaded from:
```
GET /destinations/
```

Response includes all active destinations with their YouTube-specific fields.

## Best Practices

1. **Always Configure Stream ID**: For the most direct access, configure the `youtube_stream_id` for each stream
2. **Use Channel ID as Backup**: Configure `channel_id` even if you have a Stream ID, as a fallback
3. **Update Before Going Live**: Update the Stream ID in your destination before starting each new livestream
4. **One YouTube Destination per Stream**: For clarity, use separate YouTube destinations for different channels or streams
5. **Test Before Live**: Click the Studio button during preview mode to verify it opens the correct control room

## Integration with YouTube Watchdog

The Studio button integrates seamlessly with the YouTube Watchdog system:
- Stream IDs configured for the Studio button are also used by the watchdog for health monitoring
- The watchdog can automatically populate the Stream ID when a stream goes live
- Channel IDs are shared between the Studio button and public channel preview links

## Related Features

- **Channel Button**: Opens the public YouTube channel page (`youtube.com/channel/{channel_id}/live`)
- **YouTube Watchdog**: Monitors stream health using the same Stream ID
- **Auto-Recovery**: Uses destination configuration to restart streams

## Support

For issues or questions:
1. Check this documentation
2. Verify your YouTube destination configuration
3. Review the Console for any API errors
4. Check that destinations are loading correctly from the backend

---

**Last Updated**: October 26, 2025  
**Component**: Timeline Editor → YouTube Studio Button  
**Related Files**: 
- `frontend/src/components/TimelineEditor.tsx`
- `frontend/src/components/StreamingDestinations.tsx`
- `backend/models/destination.py`

