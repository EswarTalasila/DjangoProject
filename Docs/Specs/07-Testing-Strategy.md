# Testing Strategy

## Unit tests
- Auth logic (token validation, role guards, password reset).
- DTO validation rules.
- Service-layer business rules (assignment creation, grading, overrides).

## Integration tests
- API flows for login, assignment creation, submission, grading.
- Role-based access control for all endpoints.
- Archive vs delete behavior and data retention.
- API compatibility tests to ensure `/api/*` and `/api/v1/*` return identical payload shapes.

## TODO / open testing gaps
- TODO: Add full workflow integration tests that go from account creation -> login -> course -> assessment -> assignment -> submission -> grading for teacher and student roles.
- TODO: Add spec-first tests for known audit items (first-login tokenization, check-email privacy, stricter access pre-checks) before changing behavior.
- TODO: Reintroduce browser-driven end-to-end coverage only after a dedicated testing harness is rebuilt intentionally.

## Automated frontend tests
- Angular unit tests for guards, services, and shared components.
- Visual regression tests for key screens (optional, if stable snapshots can be maintained).

## Security tests
- User enumeration checks on auth endpoints.
- Role escalation attempts (self-assign admin/teacher).
- Token expiration and revocation behavior.
- Dependency scanning (pip-audit, npm audit).
- SAST checks (bandit/semgrep) for backend.
- DAST baseline scans for API (OWASP ZAP) in dev/staging.

## Performance tests
- Visualization endpoint with large datasets (pagination and indexing).
- Export jobs with large data (streaming, bounded memory).

## Observability checks
- Audit log entries for sensitive actions.
- Tracing for critical flows.

## Diagram references
- Runtime sequences: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/sequence`

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
