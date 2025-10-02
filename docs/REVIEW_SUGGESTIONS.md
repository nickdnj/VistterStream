# Review Notes & Recommended Follow-up PRs

The review covers the current implementation, documentation set (PRD, SAD, UXD, technical spec), and backend code. Suggested pull requests below focus on tightening gaps between specifications and the shipped code, improving security posture, and making roadmap expectations clearer.

## 1. Harden Credential & Secret Handling
- Replace base64 "encryption" for camera passwords with proper secret storage (e.g., Fernet with appliance-specific key) and stop returning encoded credentials over the API. Camera creation and updates currently rely on reversible base64 encoding, which does not meet the PRD/SAD security requirements around encrypted credentials at rest.【F:backend/services/camera_service.py†L78-L118】【F:docs/SAD.md†L40-L58】【F:docs/PRD.md†L118-L118】
- Remove plain-text stream keys from database responses and enforce encryption-at-rest for RTMP credentials. The `StreamingDestination` model stores and exposes raw stream keys, contradicting the "encrypted secrets vault" described in the architecture doc and the README security claims.【F:backend/models/destination.py†L10-L33】【F:docs/SAD.md†L40-L59】【F:README.md†L128-L137】
- Externalize JWT `SECRET_KEY` configuration and rotate tokens via environment/config management instead of hardcoding a placeholder string in the auth router.【F:backend/routers/auth.py†L21-L43】

**Suggested PR scope:** Introduce a secrets manager helper, migrate existing records, adjust API serializers to mask sensitive values, and document rotation procedures in the README.

## 2. Ship the Observability Stack Promised in the Specs
- The architecture and TODO backlog call for Prometheus-style metrics, stream quality telemetry, and diagnostic bundles, but no metrics endpoint or structured logging exists in the backend yet.【F:docs/SAD.md†L24-L45】【F:docs/SAD.md†L184-L188】【F:TODO.md†L250-L260】 Implementing these will unblock health dashboards and support workflows described in the UXD/PRD.
- Add health/metrics aggregation for the camera health monitor and FFmpeg workers so the UI can surface CPU/network alerts described in the UX plan.【F:docs/UXD.md†L24-L63】【F:docs/PRD.md†L96-L145】

**Suggested PR scope:** Add FastAPI instrumentation (e.g., `prometheus_client`), structured JSON logging, and a diagnostics bundle generator, then document the scrape endpoints and alerting hooks.

## 3. Clarify Overlay System Status vs. Roadmap
- The README markets fully functional overlay and multi-track timelines, yet the technical spec and TODO list mark the overlay system as "in progress."【F:README.md†L114-L152】【F:docs/StreamingPipeline-TechnicalSpec.md†L12-L52】【F:TODO.md†L205-L227】 Either deliver the overlay MVP (text/image cues, scheduling, telemetry) or update docs to avoid overselling unfinished capabilities.
- Align UXD/TODO expectations with implementation by tagging missing overlay UI elements (overlay track editor, cue inspector) as open issues once the backend is ready.【F:docs/UXD.md†L52-L109】【F:TODO.md†L205-L227】

**Suggested PR scope:** Decide whether to accelerate overlay implementation or adjust documentation/marketing copy, then create tracking issues for outstanding UX components.

## 4. Expand Operational Documentation & Testing Strategy
- The TODO highlights missing operator guides, API docs, and deployment instructions, which are critical for the "local operator" persona in the PRD.【F:TODO.md†L292-L297】【F:docs/PRD.md†L3-L71】 A documentation PR covering setup, backup, and troubleshooting would unlock the workflow described in UXD §3.5 incident response.【F:docs/UXD.md†L37-L63】
- Codify the testing plan promised in the specs (unit, integration, hardware-in-the-loop) so Cursor/CI can run them overnight. No automated tests are hooked up to validate the ambitious reliability goals yet.【F:docs/SAD.md†L190-L196】【F:TODO.md†L285-L291】

**Suggested PR scope:** Author deployment/operations docs, scaffold pytest suites for core services, and integrate them into CI to catch regressions before manual timeline tests.

---

Addressing these areas will bring the implementation back in line with the published specs, reduce security risk, and make it easier for Cursor/ClaudeCode to deliver production-ready enhancements overnight.
