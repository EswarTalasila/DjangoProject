# Architecture

## High-level components
- Angular SPA (unchanged UI) served as static assets.
- Django REST API (new backend).
- PostgreSQL database.
- Shared nginx proxy for ingress, TLS termination, and profile routing.

## Service boundaries
- Frontend: presentation and routing only; no business logic changes.
- Backend: REST API with service-layer separation for auth, courses, assignment templates, assignments, submissions, visualization, and exports.
- Database: normalized relational schema equivalent to current entities.

## API structure
- Base path: `/api`
- Versioning: `/api/v1` preferred with compatibility routing for existing `/api/*` paths used by the current UI.
- Auth endpoints: `/api/auth/*` (login, OAuth, password setup), mirrored under `/api/v1/auth/*`.

## Module layout (Django)
- `accounts`: auth, user roles, password setup, OAuth validation.
- `courses`: courses and enrollments.
- `assignment templates`: assignment templates, questions, grading modes, rubrics.
- `assignments`: assignment scheduling, open/close windows.
- `submissions`: submission capture, grading, overrides.
- `visualizations`: aggregate queries and filters.
- `exports`: CSV/PDF generation and job management.
- `audit`: audit logs for sensitive actions.

## Repository structure (suggested)
- `backend/`: Django project (API + domain modules).
  - `backend/src/`: project source root (src-layout).
  - `backend/src/config/`: settings, urls, wsgi/asgi.
  - `backend/src/core/`: shared utilities (auth base, permissions, audit, pagination).
  - `backend/src/<domain>/`: domain modules (accounts, courses, assignment templates, assignments, submissions, visualizations, exports, audit).
  - `backend/tests/unit`: unit tests per module.
  - `backend/tests/integration`: API and workflow tests.
  - `backend/tests/security`: auth/authorization and abuse-case tests.
  - `backend/tools/diagrams`: PlantUML generation scripts and config.
- `frontend/`: Angular project (unchanged UI).
  - `frontend/src`: existing UI.
  - `frontend/tests/unit`: Angular unit tests.
- `docs/`: spec sheets and historical diagrams.
  - `docs/diagrams/plantuml`: retained reference outputs; regeneration is currently deferred.

## Backend organization rationale (chosen)
- Use a src-layout with domain modules and a shared core package.
- Avoids import shadowing and keeps Python packaging predictable.
- Domain modules map directly to product workflows without implying separate deployments.
- `core/` isolates cross-cutting concerns (auth, permissions, audit, pagination).
- Works cleanly with Docker + virtualenv + pinned `requirements.txt`.

## Data flow
- UI calls `/api/*` using the same endpoints as current Angular services (no UI changes).
- Django validates, applies access control, and executes queries.
- Responses are DTO-style JSON shaped to match current frontend expectations.

## Proxy agnostic requirements
- Application trusts `X-Forwarded-*` headers and does not hard-code host or scheme.
- TLS termination handled by proxy; app assumes HTTP behind proxy.

## Context from current system
- Backend structure: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-all.wsd`
- Entities and relationships: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-entities.wsd`
- Frontend services -> backend mapping: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-frontend-backend-map.wsd`
- Runtime flows: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/sequence`

These diagrams are the baseline for matching existing flows and structures.

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
