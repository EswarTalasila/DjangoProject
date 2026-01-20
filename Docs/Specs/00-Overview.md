# Overview

## Purpose
Provide a complete rewrite specification for the EEL Data Dashboard using a Python/Django backend and the existing Angular frontend, with PostgreSQL as the only required external service. The rewrite targets stability, security, and maintainability while preserving existing UI, workflows, and API behavior.

## Goals
- Preserve current user workflows, UI behavior, and observable functionality (no new features).
- Apply targeted fixes needed to safely operate and maintain the system; not all known issues are in scope for the initial rewrite.
- Make hosting proxy-agnostic (Traefik, Nginx, or other reverse proxies).
- Support a fully self-hosted deployment with Docker and PostgreSQL.
- Make PlantUML-first architecture documentation a built-in part of development (class, ER, and runtime sequence diagrams on demand).

## Non-goals
- No new user-facing features or UI changes beyond bug fixes.
- No reliance on cloud-managed services (auth, storage, DB).
- No UI redesign, layout changes, or new UX flows unless required to close a defect.

## Target stack
- Backend: Python 3.12, Django + Django REST Framework (DRF).
- Frontend: Angular (TypeScript) with existing routes, guards, and API calls preserved (same screens and behaviors).
- Database: PostgreSQL 15+.
- Proxy/TLS: Traefik for TLS/Let's Encrypt and reverse proxy, but app must remain proxy-agnostic.
- Containers: Docker Compose for local and self-hosted deployment.

## Known constraints
- Sponsor is non-technical; technical ownership and production environment are unknown.
- No current production environment; only dev usage exists.
- Security and data privacy are high priority.

## Architecture context references
- Current backend structure: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-all.wsd`
- Current entity model: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-entities.wsd`
- Current runtime flows: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/sequence`

These diagrams provide the baseline for matching current behavior.

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
