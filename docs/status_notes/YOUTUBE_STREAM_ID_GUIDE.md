# Finding Your YouTube Stream ID & Channel ID

Quick reference guide for configuring YouTube quick links in VistterStream Timeline Editor.

---

## 🎯 What You Need

For the Timeline Editor YouTube buttons to work, you need two IDs:

1. **Stream ID** (or Broadcast ID) → For Studio button
2. **Channel ID** → For Channel button

---

## 📺 Finding Your Stream ID

The Stream ID is in the URL when you're managing your live stream in YouTube Studio.

### Method 1: From YouTube Studio

1. Go to https://studio.youtube.com
2. Click on "Go Live" or "Content"
3. Open your live stream or scheduled broadcast
4. Look at the URL in your browser:
   ```
   https://studio.youtube.com/video/s6qs14YByEQ/livestreaming
                                   ^^^^^^^^^^^^
                                   This is your Stream ID
   ```

### Method 2: From Live Dashboard

1. Start a live stream or schedule one
2. Click on the stream in your YouTube Studio dashboard
3. The URL will contain your stream ID
4. Copy the alphanumeric code between `/video/` and `/livestreaming`

**Example Stream IDs:**
- `s6qs14YByEQ`
- `dQw4w9WgXcQ`
- `JgXKZRWRjZk`

---

## 🏠 Finding Your Channel ID

Your Channel ID is a permanent identifier for your YouTube channel.

### Method 1: From YouTube Studio

1. Go to https://studio.youtube.com
2. Click "Settings" (gear icon)
3. Click "Channel" in the left sidebar
4. Look for "Channel ID" - it starts with `UC`
   ```
   Channel ID: UCfWC5cyYX15sSolvZya5RUQ
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
   ```

### Method 2: From Your Channel URL

1. Go to your YouTube channel
2. Look at the URL - if it contains `/channel/`, that's your ID:
   ```
   https://www.youtube.com/channel/UCfWC5cyYX15sSolvZya5RUQ
                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                   This is your Channel ID
   ```

### Method 3: From Custom URL (if you have one)

If your channel has a custom URL (like `@YourChannelName`):

1. Go to your channel page
2. Click "About" tab
3. Click "Share channel" button
4. Click "Copy channel ID"

**Example Channel IDs:**
- `UCfWC5cyYX15sSolvZya5RUQ` (always starts with `UC`)
- `UC-lHJZR3Gqxm24_Vd_AJ5Yw`
- `UCX6OQ3DkcsbYNE6H8uQQuVA`

---

## ⚙️ Configuring in VistterStream

Once you have both IDs:

1. **Open VistterStream**
2. Go to **Settings → Streaming Destinations**
3. **Edit** your YouTube destination
4. Fill in the fields:
   - **YouTube Channel ID:** `UCfWC5cyYX15sSolvZya5RUQ`
   - **YouTube Stream ID:** `s6qs14YByEQ` (in watchdog section or custom field)
5. **Save** the destination

### Where to Enter the Stream ID

The Stream ID can be entered in one of these fields (depending on your setup):
- `youtube_stream_id` (preferred)
- `youtube_broadcast_id` (alternative)
- If using the watchdog feature, you may see a dedicated "Stream ID" field

---

## ✅ Testing the Buttons

After configuring the IDs:

1. Go to **Timeline Editor**
2. **Select** your YouTube destination from the dropdown
3. Verify the buttons:
   - **Studio ↗** should be RED and active (if stream_id is set)
   - **Channel ↗** should be GRAY and active (if channel_id is set)
4. Click each button to test:
   - **Studio ↗** → Opens `https://studio.youtube.com/video/{your_stream_id}/livestreaming`
   - **Channel ↗** → Opens `https://www.youtube.com/channel/{your_channel_id}/live`

---

## ⚠️ Troubleshooting

### Studio Button is Grayed Out

**Problem:** Button shows "Studio ↗" but is disabled  
**Cause:** No `youtube_stream_id` or `youtube_broadcast_id` configured  
**Solution:** Add your Stream ID to the destination settings

### Channel Button is Grayed Out

**Problem:** Button shows "Channel ↗" but is disabled  
**Cause:** No `channel_id` configured  
**Solution:** Add your Channel ID to the destination settings

### Both Buttons are Grayed Out

**Problem:** Both buttons disabled  
**Cause:** No YouTube destination selected  
**Solution:** Select a YouTube destination from the dropdown above

### Wrong Stream Opens

**Problem:** Studio button opens wrong stream  
**Cause:** Stream ID is from an old or different broadcast  
**Solution:** Get the current Stream ID from your active or scheduled stream and update the destination

---

## 📝 Notes

- **Stream ID changes** for each new broadcast/stream (unless you reuse the same stream key)
- **Channel ID is permanent** and doesn't change
- You can find your Stream ID **before** or **during** a live stream
- Both buttons work independently - you can have just channel_id or just stream_id

---

## 🔗 Quick Links

- [YouTube Studio](https://studio.youtube.com)
- [VistterStream Streaming Destinations Docs](./docs/StreamingPipeline-TechnicalSpec.md)
- [YouTube API Documentation](https://developers.google.com/youtube/v3)

---

**Last Updated:** October 25, 2025  
**VistterStream Version:** UI Refinement Update (Commit a406ef0)

