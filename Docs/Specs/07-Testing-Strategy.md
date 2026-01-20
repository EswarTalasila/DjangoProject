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

## End-to-end tests
- Admin creates assessments and users.
- Teacher creates course, enrolls students, assigns assessments.
- Student submits assignment; teacher grades; admin exports data.
- Browser E2E tests run with Playwright (multi-role workflow coverage).

## Playwright E2E setup
### Prereqs
- Backend and frontend running (or use `E2E_START_SERVER=true` to auto-start the frontend).
- Seed an admin account for UI login tests.

### Seed baseline users
```bash
./scripts/e2e/seed_e2e.sh
```

### Seeded user fixtures
- Frontend: `frontend/tests/e2e/fixtures/seeded-users.json`
- Backend: `backend/tests/fixtures/seeded-users.json`
- Override defaults via `E2E_*` env vars when seeding.

### Run E2E tests
```bash
cd frontend
E2E_BASE_URL=http://localhost:4200 \
E2E_API_URL=http://localhost:8000/api/v1 \
npm run e2e
```

### Optional env vars
- `E2E_ADMIN_USERNAME`, `E2E_ADMIN_PASSWORD`, `E2E_ADMIN_NAME`
- `E2E_TEACHER_PASSWORD`, `E2E_STUDENT_PASSWORD`
- `E2E_START_SERVER=true` (starts `npm start` during tests)
- `E2E_USE_DOCKER=false` (runs seed command without docker)

## TODO / open testing gaps
- TODO: Add full workflow integration tests that go from account creation -> login -> course -> assessment -> assignment -> submission -> grading for teacher and student roles.
- TODO: Add spec-first tests for known audit items (first-login tokenization, check-email privacy, stricter access pre-checks) before changing behavior.
- TODO: Expand Playwright coverage for all CRUD screens and error cases.

## Automated frontend tests
- Angular unit tests for guards, services, and shared components.
- E2E tests for critical workflows (login, assignment flow, grading, exports).
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
