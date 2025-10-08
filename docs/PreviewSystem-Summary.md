# Preview System - Executive Summary

**VistterStream Preview Server + Preview Window Subsystem**

---

## What Was Delivered

A **complete technical specification** for adding a local preview and go-live workflow to VistterStream, enabling operators to:

1. **Preview timelines locally** before streaming to public platforms
2. **Verify camera switching and overlays** in real-time with <2s latency
3. **Go live with one click** when satisfied with the preview
4. **Work offline** - no internet needed for preview testing

---

## Documentation Suite

### 📘 **PreviewSystem-Specification.md** (18,000 words)
**Complete PRD + SAD style specification** with:

- **Architecture diagrams** and component responsibilities
- **Functional requirements** (preview mode, go-live workflow, operator UX)
- **Non-functional requirements** (performance, reliability, security)
- **API specifications** with request/response examples
- **UI component specifications** with full React/TypeScript code
- **Database schema** (minimal changes, mostly in-memory state)
- **Deployment instructions** (Mac development, Pi 5 production)
- **Operational runbook** (troubleshooting, monitoring, maintenance)
- **Implementation phases** (7 phases, 4 weeks)
- **Testing strategy** (unit, integration, E2E, performance)
- **Future enhancements** (seamless go-live, WebRTC, DVR)

**Status**: ✅ Complete, implementation-ready

---

### 🚀 **PreviewSystem-QuickStart.md**
**30-minute setup guide** for developers:

- Step-by-step installation (MediaMTX, backend, frontend)
- Configuration examples
- Test procedures
- Troubleshooting common issues
- API reference with curl examples
- Performance targets

**Status**: ✅ Complete

---

### ✅ **PreviewSystem-TODO.md**
**Detailed implementation checklist** with:

- 57 actionable tasks across 7 phases
- Time estimates per task (142 hours total)
- Acceptance criteria per phase
- Ownership assignments (Backend/Frontend/Testing/DevOps)
- Progress tracking checkboxes
- Risk register
- Success metrics

**Status**: ✅ Ready for development kickoff

---

## System Overview

### What It Does

```
┌─────────────────────────────────────────────────────────┐
│                 OPERATOR WORKFLOW                        │
└─────────────────────────────────────────────────────────┘

1. SELECT TIMELINE
   ↓
2. CLICK "START PREVIEW"
   ↓
   Timeline streams to local MediaMTX server
   ↓
   Browser displays HLS video with <2s latency
   ↓
3. VERIFY LOOKS GOOD
   • Camera switching works
   • Overlays appear correctly
   • Timing is right
   ↓
4. SELECT DESTINATIONS (YouTube, Facebook, etc.)
   ↓
5. CLICK "GO LIVE"
   ↓
   Timeline restarts with live destinations
   ↓
6. NOW STREAMING TO PUBLIC PLATFORMS ✨
```

### Technical Architecture

```
Timeline Executor (existing)
    ↓
Stream Router (new)
    ↓
    ├─→ Preview Server (MediaMTX) → HLS → PreviewWindow.tsx
    └─→ Live Destinations (YouTube, Facebook)
```

**Key Components**:

1. **MediaMTX** - RTMP ingest server + HLS transcoder (open source, single binary)
2. **Stream Router** - Python service routing timeline output to preview or live
3. **Preview Control API** - FastAPI endpoints (`/api/preview/*`)
4. **Preview Window** - React component with HLS.js player and controls

---

## Key Technical Decisions

### 1. MediaMTX Over Nginx-RTMP

**Rationale**:
- Single binary, no dependencies (perfect for appliance)
- Native ARM64 support (Raspberry Pi)
- Built-in low-latency HLS support
- Active maintenance (Nginx-RTMP deprecated)

### 2. HLS Over WebRTC

**Rationale**:
- Broad browser compatibility (Chrome, Safari, Firefox)
- No NAT traversal complexity (local only)
- 2s latency acceptable for preview workflow
- Simpler implementation

**Future**: WebRTC option for <500ms latency (Phase 4)

### 3. Timeline Restart on Go-Live

**Rationale**:
- FFmpeg doesn't support dynamic output switching
- Acceptable for MVP (operator expects some transition)
- Seamless transition planned for Phase 2 (Q1 2026)

### 4. Local-Only Preview

**Rationale**:
- No authentication needed (localhost trust boundary)
- Reduced complexity
- Matches single-operator appliance model

---

## Implementation Plan

### Timeline: 4 Weeks (142 hours)

| Phase | Duration | Focus |
|-------|----------|-------|
| **Phase 1** | Week 1 | Install MediaMTX, test RTMP→HLS |
| **Phase 2** | Week 1-2 | Build StreamRouter service |
| **Phase 3** | Week 2 | Build Preview Control API |
| **Phase 4** | Week 2-3 | Build PreviewWindow React component |
| **Phase 5** | Week 3 | Integrate with Timeline Editor |
| **Phase 6** | Week 3-4 | Test on Pi 5, edge cases, performance |
| **Phase 7** | Week 4 | Documentation, demo, release |

### Resource Requirements

- **1 Backend Developer** (60 hours)
- **1 Frontend Developer** (50 hours)
- **1 QA/Testing** (32 hours)
- **DevOps Support** (10 hours)

### Dependencies

- VistterStream backend (existing)
- VistterStream frontend (existing)
- FFmpeg with hardware acceleration (existing)
- MediaMTX v1.3.0+ (download from GitHub)
- HLS.js v1.4.0+ (npm install)

---

## Success Criteria

### Technical

- ✅ Preview latency <2s (P95)
- ✅ CPU overhead <15% on Raspberry Pi 5
- ✅ Preview server uptime >99%
- ✅ Go-live success rate >99%

### User Experience

- ✅ Non-technical operator can use without training
- ✅ Time from "Start Preview" to video visible: <5s
- ✅ Clear error messages for all failure modes
- ✅ Seamless integration with existing UI

### Business

- ✅ -50% reduction in live stream errors (due to preview testing)
- ✅ -30% faster timeline creation (iterate in preview)
- ✅ >80% feature adoption (operators using preview)

---

## Non-Functional Guarantees

### Performance

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Latency** | <2s glass-to-glass | Operator needs fast feedback |
| **CPU** | <15% additional | Must not impact live streaming |
| **Memory** | <200MB | Embedded appliance constraint |
| **Time to Preview** | <5s | Instant gratification for operator |

### Reliability

- Auto-restart on crash (systemd)
- Graceful degradation (preview fails → live still works)
- Resource cleanup (old HLS segments auto-deleted)

### Security

- Local-only access (no external exposure)
- No authentication needed (localhost)
- Audit logging for preview/live transitions

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **MediaMTX crashes** | Systemd auto-restart + health monitoring |
| **Latency >2s** | Tune HLS settings, WebRTC fallback plan |
| **CPU overload on Pi** | Performance testing, adaptive quality |
| **Go-live transition fails** | Validate destinations, error recovery |

---

## Future Roadmap

### Q1 2026: Seamless Go-Live
- Transition from preview to live without restarting timeline
- Requires FFmpeg dynamic output switching or RTMP relay

### Q2 2026: Advanced Features
- Multi-user preview (remote producer views)
- DVR / instant replay (last N minutes)
- Preview recording for audit compliance
- Preview quality presets (low/medium/high)

### Q3 2026: Low-Latency Preview
- WebRTC option for <500ms latency
- Better for interactive workflows

---

## What's Next?

### For Product Manager
1. Review `PreviewSystem-Specification.md` (Sections 2-6)
2. Approve functional requirements
3. Prioritize future enhancements

### For Tech Lead
1. Review architecture (Section 4)
2. Validate technical decisions
3. Assign tasks from `PreviewSystem-TODO.md`

### For Development Team
1. Start with `PreviewSystem-QuickStart.md`
2. Follow `PreviewSystem-TODO.md` phases
3. Reference full spec for implementation details

### For QA Team
1. Review testing strategy (Section 9 in spec)
2. Prepare test environments (Mac, Pi 5)
3. Plan performance benchmarking

---

## Questions?

- **Architecture**: See `PreviewSystem-Specification.md` Section 4
- **Setup**: See `PreviewSystem-QuickStart.md`
- **Tasks**: See `PreviewSystem-TODO.md`
- **API**: See spec Section 4.3 (Preview Control API)
- **UI**: See spec Section 4.4 (Preview Window Component)

---

## Approval Checklist

- [ ] Product Manager approves functional requirements
- [ ] Tech Lead approves architecture
- [ ] Frontend Lead approves UI design
- [ ] Backend Lead approves API design
- [ ] QA Lead approves testing strategy
- [ ] DevOps approves deployment plan

---

**Status**: ✅ Documentation complete, ready for implementation kickoff

**Estimated Delivery**: 4 weeks from start (1 developer full-time)

**Next Action**: Schedule kickoff meeting to review spec and assign tasks

---

**Questions or concerns?** Contact: [Tech Lead / Platform Team]

