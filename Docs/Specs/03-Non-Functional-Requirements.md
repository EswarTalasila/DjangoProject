# Non-Functional Requirements

## Security
- All sensitive endpoints require authentication and role checks.
- No public endpoint returns user existence or userId details.
- Use httpOnly cookies or short-lived tokens with refresh; avoid localStorage for auth tokens.
- Enforce strong password policy and account lockout/rate limiting.
- CORS must be environment-specific and not default to wildcard.
- Secrets must be stored in environment variables or a local secrets file ignored by git.

## Privacy and data protection
- Student data must be protected by role-based access and scoping.
- All data access is restricted to ownership (teacher/course/student).
- Audit logs should record sensitive actions (role changes, score overrides, deletions).

## Performance
- All list endpoints must be paginated.
- Avoid N+1 query patterns; use ORM prefetch/select_related.
- Add indexes for high-traffic queries (assignment_id, student_id, course_id, submitted_at).
- Export endpoints should stream data where possible.

## Reliability
- Graceful error handling with consistent JSON error format.
- Database migrations must be versioned and reversible.
- No schema destructive actions on startup (no auto-drop/create).

## Observability
- Structured logs for auth, admin actions, and export jobs.
- Runtime tracing and request IDs for debugging.
- PlantUML-first diagrams generated from code and traces must be available on demand for development and documentation.

## Availability and ops
- Dockerized deployment with pinned versions.
- Health endpoints for backend and database.
- Backup and restore procedures documented (daily DB dumps).

## Documentation and diagrams
- Diagram automation is deferred until the architecture/documentation workflow is revisited.
- Existing diagrams may be retained as historical references, but regeneration is not part of the active delivery contract.

## Proxy agnosticism
- Backend must accept standard reverse proxy headers.
- No dependency on nginx-specific behaviors.

## Compliance readiness
- Provide data export for users upon request.
- Provide data deletion/archival procedures for policy compliance.

## Diagram references
- Backend layers: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-all.wsd`
- Current runtime coverage: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/sequence`

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
