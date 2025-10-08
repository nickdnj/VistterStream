- 2025-10-08 Scheduler & Timeline Updates
  - Added Scheduler (backend models, API, background loop)
  - Frontend Scheduler page with overlap warnings and delete
  - Segment-based timeline execution (overlays can change mid-cue)
  - Removed local preview window; replaced with YouTube Live Studio link
  - Added Asset copy action in Settings → Assets
# Changelog

All notable changes to the VistterStream project will be documented in this file.

## [Milestone 1] - 2025-09-26 - Foundation & Local Camera Integration ✅

### Added
- **Complete FastAPI Backend**
  - REST API with authentication endpoints
  - Camera management CRUD operations
  - Real-time status monitoring
  - SQLite database with comprehensive schema
  - Pydantic models for data validation
  - JWT authentication with bcrypt password hashing
  - CORS configuration for frontend communication

- **Beautiful React Frontend**
  - Modern dark-themed UI with Tailwind CSS
  - Responsive design for all screen sizes
  - Professional dashboard with system metrics
  - Camera management interface with real-time status
  - Login system with password visibility toggle
  - Navigation with sidebar and top bar
  - Loading states and error handling

- **Camera Integration**
  - Full support for Reolink cameras (stationary)
  - Full support for Sunba PTZ cameras with ONVIF
  - RTSP connection testing with OpenCV
  - Snapshot capture and preview functionality
  - Real-time camera health monitoring
  - Camera configuration management (add/edit/delete)

- **Database & Models**
  - SQLite database with proper relationships
  - User management with authentication
  - Camera configurations with encryption
  - PTZ preset storage and management
  - Stream configuration and status tracking

- **Development Environment**
  - Python virtual environment with FastAPI
  - React development server with hot reload
  - Tailwind CSS configuration
  - Development documentation and TODO tracking
  - Cursor.rules for development guidelines

### Technical Details
- **Backend**: FastAPI, SQLAlchemy, Pydantic, JWT, bcrypt, OpenCV, httpx
- **Frontend**: React 18, TypeScript, Tailwind CSS, React Router, Axios
- **Database**: SQLite with comprehensive schema
- **API**: RESTful design with proper error handling
- **Security**: Password hashing, JWT tokens, CORS
- **UI/UX**: Professional dark theme, responsive design

### Known Issues
- Minor authentication flow issue in frontend (bypass implemented for demo)
- Docker configuration pending for next milestone

## [Initial Setup] - 2025-09-26 - Project Reset

### Added
- Project repository reset to clean state
- Comprehensive documentation (PRD, SAD, UXD)
- Test camera configurations
- Development roadmap with 9 milestones
- Cursor development rules and guidelines
- Basic project structure

### Documentation
- Product Requirements Document (PRD.md)
- Software Architecture Document (SAD.md)
- User Experience Design Document (UXD.md)
- Local Test Cameras configuration
- Development TODO list with detailed milestones
