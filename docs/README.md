# VistterStream Documentation Index

Welcome to the VistterStream documentation! This index helps you find the right documentation for your needs.

## 🚀 Getting Started

**New to VistterStream?** Start here:

1. **[Quick Start Guide](QUICK_START_GUIDE.md)** - Get streaming in 5 minutes
2. **[Complete User Guide](USER_GUIDE.md)** - Comprehensive feature reference with screenshots
3. **[Raspberry Pi Setup](RaspberryPi-Docker.md)** - Deploy on Raspberry Pi hardware

## 📚 Documentation by Role

### For End Users

**Setup & Installation:**
- [Quick Start Guide](QUICK_START_GUIDE.md) - First-time setup
- [Raspberry Pi Docker Setup](RaspberryPi-Docker.md) - Pi-specific deployment
- [Docker Testing Guide](Docker-Testing-Complete.md) - Advanced Docker deployment
- [Local Test Cameras](Local%20Test%20Cameras.md) - Test camera configurations

**Using VistterStream:**
- [Complete User Guide](USER_GUIDE.md) - All features explained with screenshots
- [YouTube OAuth Setup](working_documents/oauth/YOUTUBE_OAUTH_SETUP.md) - Configure YouTube API integration

**Troubleshooting:**
- [OAuth Connection Fix](working_documents/oauth/OAUTH_CONNECTION_FIX.md) - Fix YouTube OAuth issues
- Status notes in `status_notes/` directory for historical troubleshooting

### For Developers & Contributors

**Technical Specifications:**
- [Product Requirements (PRD)](specifications/PRD.md) - Original product vision and requirements
- [Software Architecture (SAD)](specifications/SAD.md) - System architecture and design
- [UX Design (UXD)](specifications/UXD.md) - User experience specifications
- [Streaming Pipeline Technical Spec](specifications/StreamingPipeline-TechnicalSpec.md) - Detailed implementation
- [Scheduler Design](specifications/Scheduler.md) - Scheduling system architecture

**Advanced Features:**
- [Preview System Specification](specifications/PreviewSystem-Specification.md) - Preview system design (future)
- [Preview System Quick Start](PreviewSystem-QuickStart.md) - Preview system setup
- [Preview System Summary](PreviewSystem-Summary.md) - Executive overview
- [Preview System TODO](PreviewSystem-TODO.md) - Implementation tasks

**Integration & Deployment:**
- [Pi Docker PTZ Guide](pi-docker-ptz.md) - PTZ camera setup on Raspberry Pi
- [Settings Location Sync](settings-location-sync.md) - Configuration synchronization
- [Firewall Access Options](FirewallAccessOptions.md) - Network configuration
- [Deployment Workflow](working_documents/deployment/CODEX_DEPLOY_WORKFLOW.md) - Automated deployment

**Working Documents:**
- [OAuth Documentation](working_documents/oauth/) - OAuth setup and troubleshooting
- [Debug Notes](working_documents/debug/) - Debugging guides and fixes
- [Deployment Notes](working_documents/deployment/) - Deployment procedures

### For System Administrators

**Deployment:**
- [Docker Compose Configurations](../docker/) - Various deployment scenarios
- [Systemd Service Examples](../systemd/) - Linux service configuration
- [Deployment Scripts](../scripts/) - Automation scripts

**Monitoring & Maintenance:**
- [YouTube Studio Button](YouTubeStudioButton.md) - YouTube integration features
- [Status Notes](status_notes/) - Historical development and fixes

## 📂 Documentation Structure

```
docs/
├── specifications/              # Technical specifications (PRD, SAD, UXD)
│   ├── PRD.md                   # Product Requirements Document
│   ├── SAD.md                   # Software Architecture Document
│   ├── UXD.md                   # User Experience Design
│   ├── StreamingPipeline-TechnicalSpec.md
│   ├── Scheduler.md
│   ├── VistterStudioIntegration.md (future vision)
│   └── PreviewSystem-Specification.md
├── working_documents/           # Working notes, fixes, deployment
│   ├── oauth/                   # OAuth setup and troubleshooting
│   ├── debug/                   # Debug notes and fixes
│   └── deployment/              # Deployment procedures
├── status_notes/                # Historical development notes
├── screenshots/                 # UI reference images
├── ui-changes/                  # UI change documentation
├── QUICK_START_GUIDE.md         # ⭐ START HERE
├── USER_GUIDE.md                # Complete feature guide
├── RaspberryPi-Docker.md        # Pi deployment
├── Docker-Testing-Complete.md   # Docker guide
└── README.md                    # This file
```

## 📖 Key Documents by Topic

### Camera Management
- [User Guide - Camera Section](USER_GUIDE.md#cameras)
- [Local Test Cameras](Local%20Test%20Cameras.md)
- [Pi Docker PTZ](pi-docker-ptz.md)

### Streaming & Broadcasting
- [User Guide - Streaming Section](USER_GUIDE.md#streaming)
- [Streaming Pipeline Spec](specifications/StreamingPipeline-TechnicalSpec.md)
- [YouTube OAuth Setup](working_documents/oauth/YOUTUBE_OAUTH_SETUP.md)

### Timelines & Automation
- [User Guide - Timeline Section](USER_GUIDE.md#timelines)
- [Scheduler Design](specifications/Scheduler.md)
- [Streaming Pipeline Spec](specifications/StreamingPipeline-TechnicalSpec.md)

### PTZ Cameras & Presets
- [User Guide - PTZ Presets](USER_GUIDE.md#ptz-presets)
- [PRD - PTZ Implementation](specifications/PRD.md#11-ptz-preset-system-implementation-october-2025)
- [SAD - PTZ Architecture](specifications/SAD.md#42-ptz-preset-system-architecture)

### Assets & Overlays
- [User Guide - Assets Section](USER_GUIDE.md#assets)
- [Streaming Pipeline Spec](specifications/StreamingPipeline-TechnicalSpec.md)

### Scheduling
- [User Guide - Scheduler](USER_GUIDE.md#scheduler)
- [Scheduler Design](specifications/Scheduler.md)

### YouTube Integration
- [YouTube OAuth Setup](working_documents/oauth/YOUTUBE_OAUTH_SETUP.md)
- [OAuth Connection Fix](working_documents/oauth/OAUTH_CONNECTION_FIX.md)
- [YouTube Watchdog](status_notes/YOUTUBE_WATCHDOG_README.md)
- [YouTube Studio Button](YouTubeStudioButton.md)

## 🔍 Finding Specific Information

### Feature Implementation Status
See the **README.md** in the project root for current implementation status.

### Historical Context
Check `status_notes/` for development history, decisions, and evolution of features.

### Troubleshooting
1. Check the [User Guide](USER_GUIDE.md) troubleshooting sections
2. Review `working_documents/debug/` for known issues and fixes
3. Check `working_documents/oauth/` for YouTube/OAuth issues
4. Search `status_notes/` for historical solutions

### API & Integration
- [SAD](specifications/SAD.md) - API architecture
- [Streaming Pipeline Spec](specifications/StreamingPipeline-TechnicalSpec.md) - Implementation details
- [VistterStudio Integration](specifications/VistterStudioIntegration.md) - Future cloud integration (not implemented)

## 📝 Understanding the Documentation

### Specification Documents (specs/)
These documents represent the **original vision** developed during the design phase. They include:
- ✅ Features that were implemented
- ⏳ Features planned for the future (like VistterStudio cloud integration)

Each specification now includes a status section clarifying what was built vs. what remains future work.

### Working Documents (working_documents/)
Real-world fixes, debugging notes, and deployment procedures discovered during development and operation.

### Status Notes (status_notes/)
Historical development logs showing how features evolved, problems encountered, and solutions applied.

## 🎯 Quick Reference

| I want to... | Read this |
|--------------|-----------|
| Set up VistterStream for the first time | [Quick Start Guide](QUICK_START_GUIDE.md) |
| Deploy on Raspberry Pi | [Raspberry Pi Setup](RaspberryPi-Docker.md) |
| Learn all features | [Complete User Guide](USER_GUIDE.md) |
| Set up YouTube streaming | [YouTube OAuth Setup](working_documents/oauth/YOUTUBE_OAUTH_SETUP.md) |
| Understand the architecture | [Software Architecture (SAD)](specifications/SAD.md) |
| Configure PTZ cameras | [User Guide - PTZ](USER_GUIDE.md#ptz-presets) |
| Create automated shows | [User Guide - Timelines](USER_GUIDE.md#timelines) |
| Schedule content | [User Guide - Scheduler](USER_GUIDE.md#scheduler) |
| Add overlays | [User Guide - Assets](USER_GUIDE.md#assets) |
| Fix OAuth issues | [OAuth Connection Fix](working_documents/oauth/OAUTH_CONNECTION_FIX.md) |
| Understand what was built vs. planned | [PRD](specifications/PRD.md) or [SAD](specifications/SAD.md) status sections |

## 📊 Documentation Quality

All user-facing documentation includes:
- ✅ Step-by-step instructions
- ✅ Screenshots where applicable
- ✅ Troubleshooting sections
- ✅ Prerequisites and requirements
- ✅ Expected outcomes

Technical specifications include:
- ✅ Implementation status (built vs. future)
- ✅ Architecture diagrams
- ✅ Data models and schemas
- ✅ API contracts
- ✅ Deployment considerations

## 🤝 Contributing to Documentation

Found an error or want to improve documentation?

1. User guides live in `docs/`
2. Specifications live in `docs/specifications/`
3. Working notes live in `docs/working_documents/`
4. Screenshots go in `docs/screenshots/`

Keep documentation:
- **Accurate** - Reflects current implementation
- **Clear** - Written for the intended audience
- **Complete** - Includes all necessary context
- **Current** - Updated when features change

## 📞 Getting Help

1. **Start with:** [Quick Start Guide](QUICK_START_GUIDE.md)
2. **Then try:** [User Guide](USER_GUIDE.md) troubleshooting sections
3. **For OAuth issues:** [OAuth docs](working_documents/oauth/)
4. **For deployment:** [Docker guides](Docker-Testing-Complete.md)
5. **For architecture questions:** [Technical specs](specifications/)

---

**Ready to get started?** → **[Quick Start Guide](QUICK_START_GUIDE.md)** 🚀
