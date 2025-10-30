# ✅ Auto-Recovery V2 - Cue Change Detection

## What Changed

### Removed (Didn't Work):
- ❌ "Switching Camera..." overlay popup (you didn't like it)
- ❌ Error-based recovery (too late, stream already broken)
- ❌ Manual manifest reloading (didn't work reliably)

### Added (Better Approach):
- ✅ **Proactive cue change detection**
- ✅ **Complete HLS player reinitialization**
- ✅ **Clean video recovery**

---

## 🎯 How It Works Now

### Detection Strategy:
```typescript
1. Poll /api/preview/playback-position every 500ms
2. Track current_cue_id
3. When cue_id changes:
   - Destroy old HLS player
   - Wait 3 seconds for new FFmpeg to start
   - Create fresh HLS player with cache-busting
   - Video resumes automatically
```

### Timeline Flow:
```
0s-41s: Cue ID=1 (Camera 7)
  → Playing normally
  → Position polling detects cue_id=1
  
41s: Backend switches to Cue ID=2
  → Position API returns cue_id=2
  → Frontend detects change: 1 → 2
  → Console: "Camera switch detected: Cue 1 → 2"
  → Console: "Reinitializing HLS player for new camera..."
  → Destroy old player
  → Wait 3 seconds
  → Create new player with fresh URL
  → Video resumes with Camera 6! ✅
  
81.5s: Backend switches to Cue ID=3
  → Same process repeats
  → Automatic recovery
```

---

## 🎬 User Experience

### What You'll See:

**During Normal Playback:**
- Video playing smoothly
- Playhead advancing
- No interruptions

**At Camera Switch (41s, 81.5s):**
- Brief black screen (~3-5 seconds)
- Console log: "Camera switch detected..."
- Video automatically resumes with new camera
- **NO POPUP, NO MANUAL REFRESH NEEDED**

---

## 📊 Recovery Timeline

```
T+0s: Backend starts Cue 2
T+0s: FFmpeg stops old stream
T+0.5s: Position API returns new cue_id
T+0.5s: Frontend detects cue change
T+0.5s: Destroy old HLS player
T+3.5s: Initialize new HLS player
T+3.5s: New FFmpeg is publishing
T+4.5s: HLS.js loads manifest
T+5.5s: Video playing again ✅

Total interruption: ~5 seconds
```

---

## 🔧 Technical Details

### Cue Change Detection:
```typescript
// Store last cue ID
const [lastCueId, setLastCueId] = useState<number | null>(null);

// Poll position every 500ms
if (newCueId !== lastCueId) {
  // Camera switch detected!
  cleanupHlsPlayer();
  setTimeout(() => {
    initializeHlsPlayer(newUrl);
  }, 3000);
  setLastCueId(newCueId);
}
```

### Why 3 Seconds?
- FFmpeg needs ~2 seconds to:
  1. Stop old stream
  2. Move camera to preset (if needed)
  3. Start new RTSP connection
  4. Begin publishing to RTMP
- MediaMTX needs ~1 second to:
  1. Receive first frames
  2. Generate HLS segments
  3. Create manifest

**Total: ~3 seconds minimum**

---

## ✅ Advantages

### vs. Error-Based Recovery:
- ✅ **Proactive** (detects switches before they fail)
- ✅ **Predictable** (always waits 3s)
- ✅ **Clean** (no error states to handle)
- ✅ **Reliable** (fresh player every time)

### vs. Manual Refresh:
- ✅ **Automatic** (no user intervention)
- ✅ **Seamless** (user just waits)
- ✅ **Professional** (looks intentional, not broken)

---

## 🧪 Test It

1. **Hard Refresh Browser** (`Cmd+Shift+R`)
2. **Start Preview** on "Wharfside Waterfront"
3. **Watch the Timeline:**

```
0s-41s: Camera 1 (Sunba PTZ)
  - Video playing ✅
  - Playhead advancing ✅
  
~41s: CAMERA SWITCH
  - Screen goes black for ~5s
  - Console: "Camera switch detected: Cue 1 → 2"
  - Console: "Reinitializing HLS player..."
  - Video AUTOMATICALLY resumes ✅
  
41s-81.5s: Camera 2 (Reolink)
  - Video playing ✅
  - No manual refresh needed ✅
  
~81.5s: CAMERA SWITCH
  - Same auto-recovery process
  - Video resumes with Camera 3 ✅
  
81.5s-122s: Camera 3 (Sunba PTZ)
  - Video playing ✅
  
~122s: LOOP
  - Back to Camera 1
  - Loop 2 badge appears ✅
```

---

## 📈 Expected Behavior

### SUCCESS: Camera switches auto-recover
- Brief 5-second black screen
- Console shows detection logs
- Video resumes automatically
- Playhead continues advancing

### FAILURE: If it doesn't work
- Check console for "Camera switch detected" logs
- Verify playback position API is responding
- Ensure FFmpeg is restarting properly

---

## ⚠️ Limitations

- **5-second interruption** on each switch (acceptable for preview)
- **Brief black screen** (intentional, not a bug)
- **Future**: Seamless Executor will eliminate this

---

**Refresh and test now! Camera switches will auto-recover without any popups!** 🎥

