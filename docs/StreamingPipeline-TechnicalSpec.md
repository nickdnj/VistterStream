# VistterStream Streaming Pipeline & Timeline Engine - Technical Specification

## 🎯 **Design Philosophy**

**RELIABILITY FIRST** - The show must go on, even when things break.
**SIMPLE MVP** - Go-live button simplicity, power-user features later.
**MULTI-TRACK TIMELINES** - TV show script with independent video and overlay tracks.

---

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    OPERATOR INTERFACE                        │
│              "GO LIVE" Button + Timeline Controls            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  TIMELINE ORCHESTRATOR                       │
│  • Multi-track timeline execution (video + overlay tracks)   │
│  • Sequential cue execution per track                        │
│  • State machine for playback control                        │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
┌─────────────────────────┐    ┌──────────────────────────┐
│   VIDEO TRACK EXECUTOR   │    │  OVERLAY TRACK EXECUTOR  │
│  • Camera switching      │    │  • Layer management      │
│  • Transition handling   │    │  • Timing sync           │
│  • Fallback management   │    │  • Asset preloading      │
└─────────────────────────┘    └──────────────────────────┘
                │                           │
                ▼                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     STREAM ENGINE                            │
│  • FFmpeg process management                                 │
│  • Hardware-accelerated encoding (Pi 5, Mac)                 │
│  • Multi-destination output (YouTube, Facebook, Twitch)      │
│  • Real-time overlay compositing                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  FAILURE RECOVERY SYSTEM                     │
│  • Camera failure → Backup camera OR test pattern            │
│  • Stream failure → Auto-retry with exponential backoff      │
│  • Degraded mode → Continue with warnings                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📺 **Multi-Track Timeline System**

### **Timeline Structure**

```json
{
  "timeline": {
    "id": "timeline_001",
    "name": "Daily Marina Stream",
    "duration": 3600,
    "fps": 30,
    "resolution": "1920x1080",
    "tracks": {
      "video": {
        "track_id": "video_main",
        "type": "video",
        "cues": [
          {
            "id": "cue_v1",
            "start_time": 0,
            "duration": 60,
            "action": "show_camera",
            "params": {
              "camera_id": 1,
              "preset_id": "wide_shot",
              "transition": "cut"
            }
          },
          {
            "id": "cue_v2",
            "start_time": 60,
            "duration": 5,
            "action": "show_media",
            "params": {
              "media_url": "/assets/transition_slide.png",
              "transition": "fade",
              "transition_duration": 1.0
            }
          },
          {
            "id": "cue_v3",
            "start_time": 65,
            "duration": 60,
            "action": "show_camera",
            "params": {
              "camera_id": 2,
              "preset_id": "close_up",
              "transition": "fade"
            }
          }
        ]
      },
      "overlays": [
        {
          "track_id": "overlay_1",
          "type": "overlay",
          "layer": 1,
          "cues": [
            {
              "id": "cue_o1",
              "start_time": 10,
              "duration": 15,
              "action": "show_overlay",
              "params": {
                "type": "lower_third",
                "text": "Marina Cam - Wharfside",
                "position": "bottom_left",
                "fade_in": 0.5,
                "fade_out": 0.5
              }
            },
            {
              "id": "cue_o2",
              "start_time": 70,
              "duration": 10,
              "action": "show_overlay",
              "params": {
                "type": "logo",
                "image_url": "/assets/logo.png",
                "position": "top_right",
                "opacity": 0.8
              }
            }
          ]
        },
        {
          "track_id": "overlay_2",
          "type": "overlay",
          "layer": 2,
          "cues": [
            {
              "id": "cue_o3",
              "start_time": 30,
              "duration": 20,
              "action": "show_overlay",
              "params": {
                "type": "text",
                "text": "Tide: High 3:45 PM",
                "position": "bottom_right",
                "font_size": 24
              }
            }
          ]
        }
      ]
    },
    "fallback": {
      "test_pattern": "/assets/technical_difficulties.png",
      "backup_camera_id": 3
    }
  }
}
```

### **Track Types**

1. **Video Track (Main)** - Only ONE active at a time
   - `show_camera` - Switch to camera feed (with optional PTZ preset)
   - `show_media` - Show static image or pre-recorded video
   - `transition` - Cut, fade, dissolve between sources

2. **Overlay Tracks (Multiple)** - Can run simultaneously
   - Independent timing from video track
   - Layer system (z-order: 1=bottom, higher=top)
   - Types: `lower_third`, `logo`, `text`, `image`, `dynamic_text`

### **Execution Model**

- **Sequential per track** - Cues execute in order within each track
- **Parallel across tracks** - Video + multiple overlay tracks run simultaneously
- **Timing sync** - All tracks share a common timeline clock (30fps precision)
- **Cue transitions** - Each cue can specify entry/exit transitions

---

## 🎬 **Streaming Pipeline Architecture**

### **1. FFmpeg Strategy**

**Single FFmpeg process per stream with dynamic filter graphs**

#### **Process Structure**
```
Input Sources → Filter Complex → Encoder → Output Destinations
```

#### **Filter Graph Template**
```
# Video Input (camera or test pattern)
[0:v] scale=1920:1080, fps=30 [video_base];

# Overlay Layer 1 (lower third)
[video_base][1:v] overlay=x=10:y=H-100:enable='between(t,10,25)' [layer1];

# Overlay Layer 2 (logo)
[layer1][2:v] overlay=x=W-120:y=10:alpha=0.8:enable='between(t,30,50)' [layer2];

# Overlay Layer 3 (dynamic text)
[layer2] drawtext=text='%{localtime}':x=10:y=10:fontsize=24:fontcolor=white [output];

[output] libx264, aac → RTMP outputs
```

### **2. Hardware Acceleration**

#### **Raspberry Pi 5**
- **Encoder**: `h264_v4l2m2m` (V4L2 hardware encoder)
- **Decoder**: `h264_v4l2m2m` 
- **Fallback**: `libx264` (software, for quality over speed)
- **Max streams**: 3 concurrent @ 1080p30 or 5 @ 720p30

#### **Mac (Development)**
- **Encoder**: `h264_videotoolbox` (Apple VideoToolbox)
- **Decoder**: `h264_videotoolbox`
- **Fallback**: `libx264`
- **Performance**: Virtually unlimited on M-series

#### **Detection & Fallback**
```python
def detect_hardware_encoder():
    # Check Pi 5 V4L2
    if check_device('/dev/video11'):  # Pi 5 encoder
        return 'h264_v4l2m2m'
    
    # Check Mac VideoToolbox
    if platform == 'darwin' and check_videotoolbox():
        return 'h264_videotoolbox'
    
    # Fallback to software
    return 'libx264'
```

### **3. Encoding Profiles**

#### **Reliability Profile (Default)**
```yaml
video_codec: h264_v4l2m2m  # or platform-specific HW encoder
resolution: 1920x1080
framerate: 30
bitrate: 4500k  # Conservative for reliability
bitrate_mode: CBR  # Constant bitrate
keyframe_interval: 2s  # Frequent keyframes for quick recovery
buffer_size: 9000k  # 2x bitrate
preset: fast  # Lower CPU, acceptable quality
profile: main
level: 4.1
```

#### **Quality Profile (Optional)**
```yaml
video_codec: h264_v4l2m2m
resolution: 1920x1080
framerate: 30
bitrate: 6000k
bitrate_mode: VBR  # Variable bitrate
keyframe_interval: 4s
buffer_size: 12000k
preset: medium
profile: high
level: 4.2
```

#### **Adaptive Profile (Future)**
- Monitor stream health (dropped frames, buffer fullness)
- Auto-reduce bitrate by 20% when issues detected
- Step back up when stable for 30 seconds

### **4. Output Destinations**

#### **Supported Platforms**
```python
DESTINATIONS = {
    'youtube': {
        'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2',
        'key_format': 'stream_key',
        'max_bitrate': 8000,  # kbps
        'recommended_keyframe': 2  # seconds
    },
    'facebook': {
        'rtmp_url': 'rtmps://live-api-s.facebook.com:443/rtmp',
        'key_format': 'stream_key',
        'max_bitrate': 4000,
        'recommended_keyframe': 2
    },
    'twitch': {
        'rtmp_url': 'rtmp://live.twitch.tv/app',
        'key_format': 'stream_key',
        'max_bitrate': 6000,
        'recommended_keyframe': 2
    },
    'custom_rtmp': {
        'rtmp_url': 'user_provided',
        'key_format': 'optional',
        'max_bitrate': None,
        'recommended_keyframe': 2
    }
}
```

#### **Multi-Destination Strategy**
- **Single encode, multiple outputs** (tee muxer)
- **Independent retry logic** per destination
- **Failure isolation** - One destination failing doesn't affect others

```
FFmpeg → [tee] → RTMP #1 (YouTube)
               → RTMP #2 (Facebook)  
               → RTMP #3 (Twitch)
```

---

## 🛡️ **Failure Recovery System**

### **Camera Failure Handling**

```python
class CameraFailureHandler:
    """
    Priority order:
    1. Switch to backup camera (if configured)
    2. Show test pattern with message
    3. Continue stream with last good frame
    """
    
    def handle_camera_failure(self, failed_camera_id):
        # Check for backup camera
        backup = self.get_backup_camera(failed_camera_id)
        if backup and backup.status == 'online':
            self.switch_to_camera(backup.id)
            self.show_overlay("Switched to backup camera", duration=5)
            return
        
        # Fall back to test pattern
        test_pattern = "/assets/technical_difficulties.png"
        self.switch_to_media(test_pattern)
        self.show_overlay("Technical Difficulties - We'll be right back", persistent=True)
        
        # Alert operator
        self.alert_operator(f"Camera {failed_camera_id} failed, showing test pattern")
        
        # Retry camera connection in background
        self.schedule_retry(failed_camera_id, interval=10)
```

### **Stream Failure Handling**

```python
class StreamFailureHandler:
    """
    Retry logic with exponential backoff
    """
    
    def handle_stream_failure(self, stream_id, destination, error):
        retry_count = self.get_retry_count(stream_id)
        
        # Max retries: 10
        if retry_count >= 10:
            self.mark_stream_failed(stream_id)
            self.alert_operator(f"Stream {stream_id} permanently failed: {error}")
            return
        
        # Exponential backoff: 2s, 4s, 8s, 16s, 32s, 60s (max)
        wait_time = min(2 ** retry_count, 60)
        
        self.schedule_retry(stream_id, wait_time)
        self.log_warning(f"Stream {stream_id} retry {retry_count+1} in {wait_time}s")
```

### **Degraded Mode Operation**

```python
class DegradedModeManager:
    """
    Continue streaming with reduced capability
    """
    
    def enter_degraded_mode(self, reason):
        if reason == 'high_cpu':
            # Reduce resolution or framerate
            self.reduce_encoding_quality()
        
        elif reason == 'network_issues':
            # Reduce bitrate
            self.reduce_bitrate(percentage=20)
        
        elif reason == 'encoder_overload':
            # Disable overlays temporarily
            self.disable_overlays()
        
        # Show warning on stream
        self.show_overlay("⚠️ Degraded Mode", position='top_left', duration=10)
        
        # Monitor for recovery
        self.schedule_health_check(interval=30)
```

---

## 🎨 **Overlay System (MVP)**

### **Simple Overlay Types**

1. **Text Overlay**
   - Dynamic text rendering via FFmpeg `drawtext` filter
   - Position: `top_left`, `top_right`, `bottom_left`, `bottom_right`, `center`
   - Font size, color, background
   - Fade in/out support

2. **Image Overlay (Logo/Graphic)**
   - PNG with alpha transparency
   - Fixed or timed display
   - Position and scale control
   - Opacity control

3. **Lower Third**
   - Pre-designed PNG template
   - Dynamic text replacement
   - Standard positions and timings

### **Overlay Assets**

```
/assets/overlays/
├── lower_thirds/
│   ├── default.png
│   └── branded.png
├── logos/
│   ├── main_logo.png
│   └── sponsor_logo.png
├── test_patterns/
│   ├── technical_difficulties.png
│   ├── please_stand_by.png
│   └── color_bars.png
└── transitions/
    ├── fade_to_black.png
    └── slide_transition.png
```

### **Dynamic Text Updates**

```python
# Update overlay text without restarting stream
def update_overlay_text(overlay_id, new_text):
    # Generate new drawtext filter
    new_filter = f"drawtext=text='{new_text}':x=10:y=10:fontsize=24"
    
    # Send filter update to FFmpeg (requires filtergraph reload)
    # OR: Use separate overlay process and composite
```

---

## 🎛️ **Operator Interface**

### **"GO LIVE" Experience**

#### **Pre-flight Checklist**
```
1. ✅ Cameras online (2/2)
2. ✅ Timeline loaded
3. ✅ Destinations configured (YouTube ✓, Facebook ✓)
4. ✅ Overlays ready
5. ⚠️ Warning: Backup camera offline
```

#### **Go Live Button**
```
┌────────────────────────────────────┐
│                                    │
│         🔴  GO LIVE                │
│                                    │
│    Start streaming to all          │
│    destinations with timeline      │
│                                    │
└────────────────────────────────────┘

[ Countdown: 5 seconds ]
OR
[ Start Immediately ]
```

#### **Live Controls**
```
┌─────────────────────────────────────────────────┐
│  🔴 LIVE  |  Timeline: "Daily Marina Stream"    │
│                                                 │
│  [⏸ Pause Timeline]  [⏹ Stop Stream]           │
│                                                 │
│  Camera: #1 Wide Shot                          │
│  Overlays: Lower Third (15s left)              │
│  Destinations: YouTube ✓ Facebook ✓ Twitch ✗   │
│                                                 │
│  Bitrate: 4.5 Mbps  |  CPU: 45%  |  Temp: 62°C │
└─────────────────────────────────────────────────┘

Manual Overrides:
┌─────────────────────────────────────────────────┐
│  [ Emergency: Show Test Pattern ]               │
│  [ Force Camera Switch ] [ Pin Current Camera ] │
│  [ Clear All Overlays ]                         │
└─────────────────────────────────────────────────┘
```

---

## 📊 **Monitoring & Telemetry**

### **Real-time Metrics**

```python
STREAM_METRICS = {
    'bitrate_current': float,  # Mbps
    'bitrate_target': float,
    'framerate_actual': float,
    'framerate_target': float,
    'dropped_frames': int,
    'encoding_cpu': float,  # percentage
    'encoding_time_ms': float,  # per frame
    'buffer_fullness': float,  # percentage
    'uptime_seconds': int,
    'total_bytes_sent': int,
    'destinations': {
        'youtube': {'status': 'active', 'bitrate': 4.5},
        'facebook': {'status': 'active', 'bitrate': 4.5},
    }
}
```

### **Health Checks**

```python
def check_stream_health():
    health = {
        'status': 'healthy',
        'warnings': [],
        'errors': []
    }
    
    # Check encoding performance
    if encoding_cpu > 90:
        health['warnings'].append('High CPU usage')
        health['status'] = 'degraded'
    
    # Check dropped frames
    if dropped_frames_per_second > 5:
        health['errors'].append('Dropping frames')
        health['status'] = 'unhealthy'
    
    # Check buffer
    if buffer_fullness < 10:
        health['warnings'].append('Low buffer')
    
    # Check destinations
    for dest, status in destinations.items():
        if status != 'active':
            health['errors'].append(f'{dest} disconnected')
            health['status'] = 'unhealthy'
    
    return health
```

---

## 🗄️ **Database Schema Extensions**

### **Timelines Table**
```sql
CREATE TABLE timelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    duration INTEGER NOT NULL,  -- seconds
    fps INTEGER DEFAULT 30,
    resolution VARCHAR(20) DEFAULT '1920x1080',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE
);
```

### **Timeline Tracks Table**
```sql
CREATE TABLE timeline_tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timeline_id INTEGER REFERENCES timelines(id) ON DELETE CASCADE,
    track_type VARCHAR(20) NOT NULL,  -- 'video', 'overlay'
    track_name VARCHAR(50),
    layer INTEGER DEFAULT 1,  -- z-order for overlays
    is_enabled BOOLEAN DEFAULT TRUE
);
```

### **Timeline Cues Table**
```sql
CREATE TABLE timeline_cues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER REFERENCES timeline_tracks(id) ON DELETE CASCADE,
    cue_order INTEGER NOT NULL,
    start_time FLOAT NOT NULL,  -- seconds with decimal precision
    duration FLOAT NOT NULL,
    action_type VARCHAR(50) NOT NULL,  -- 'show_camera', 'show_overlay', etc.
    action_params JSON NOT NULL,  -- Store params as JSON
    transition_type VARCHAR(20) DEFAULT 'cut',
    transition_duration FLOAT DEFAULT 0
);
```

### **Timeline Execution History**
```sql
CREATE TABLE timeline_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timeline_id INTEGER REFERENCES timelines(id),
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20),  -- 'running', 'completed', 'stopped', 'error'
    executed_by INTEGER REFERENCES users(id),
    error_message TEXT,
    metrics JSON  -- Store execution stats
);
```

### **Assets Table**
```sql
CREATE TABLE assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type VARCHAR(20) NOT NULL,  -- 'image', 'video', 'audio'
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    checksum VARCHAR(64),  -- SHA256
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON  -- dimensions, duration, etc.
);
```

---

## 🚀 **Implementation Phases**

### **Phase 1: Core Streaming (Week 1)**
- [ ] FFmpeg process manager with hardware acceleration detection
- [ ] Single camera to single destination streaming
- [ ] Basic health monitoring and auto-restart
- [ ] Test pattern fallback on camera failure

### **Phase 2: Multi-Track Timeline (Week 2)**
- [ ] Timeline data model and database schema
- [ ] Timeline orchestrator with track execution
- [ ] Video track: camera switching with transitions
- [ ] Simple overlay track: text and image overlays

### **Phase 3: Advanced Features (Week 3)**
- [ ] Multi-destination streaming (3+ simultaneous)
- [ ] Backup camera failover
- [ ] Timeline builder UI (drag-drop cues)
- [ ] Asset management system

### **Phase 4: Operator Experience (Week 4)**
- [ ] "GO LIVE" button with pre-flight checks
- [ ] Live monitoring dashboard
- [ ] Manual override controls
- [ ] Timeline library (browse, clone, import/export)

### **Phase 5: Polish & Hardening (Week 5)**
- [ ] Comprehensive error handling and recovery
- [ ] Performance optimization for Pi 5
- [ ] Operator documentation and tutorials
- [ ] Load testing and chaos engineering

---

## ✅ **Success Criteria**

### **Reliability Goals**
- ✅ 99% uptime during scheduled streams
- ✅ Automatic recovery from camera failures < 3 seconds
- ✅ Stream destination retry successful within 30 seconds
- ✅ Zero manual interventions for common failures

### **Performance Goals**
- ✅ 3 concurrent 1080p30 streams on Raspberry Pi 5
- ✅ Timeline cue execution latency < 500ms
- ✅ Overlay updates without stream interruption
- ✅ CPU usage < 80% under normal operation

### **Operator Experience Goals**
- ✅ "GO LIVE" to streaming in < 10 seconds
- ✅ Non-technical operator can create basic timeline
- ✅ All errors show actionable remediation steps
- ✅ Real-time preview of output available

---

## 🎯 **Definition of AWESOME**

### **The Moment You Say "FUCK YEAH!"**

1. **Reliability** - Stream runs for 8 hours, camera fails twice, backup takes over seamlessly, operator never knows
2. **Simplicity** - Non-technical venue manager creates 30-minute looping timeline in 5 minutes
3. **Power** - Producer runs complex multi-camera show with overlays, all synchronized perfectly
4. **Recovery** - Internet drops for 30 seconds, stream reconnects automatically, viewers barely notice
5. **Monitoring** - Something goes wrong, operator gets clear alert: "Camera 2 offline - switched to backup"

### **This Beats OBS/vMix When:**
- ✅ Completely unattended 24/7 streaming (can't do this with OBS)
- ✅ Cloud-controlled fleet of appliances (future VistterStudio integration)
- ✅ Automatic failover and recovery (set it and forget it)
- ✅ Timeline-based productions (no manual switching needed)
- ✅ Turnkey appliance deployment (no PC required)

---

**LET'S BUILD THIS BEAST!** 🚀🔥
