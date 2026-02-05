# Frontend E2E Tests

Playwright suite for Angular workflows and API/UI validation.

## Prerequisites
- Backend and frontend running (see root `README.md`).
- Seed test users: `./scripts/e2e/seed_e2e.sh` from repo root.

## Run
```bash
# From repo root (Docker)
E2E_BASE_URL=http://eel-frontend:4200 \
E2E_API_URL=http://eel-backend:8000/api/v1 \
scripts/e2e/run_playwright.sh

# Single spec
docker compose --profile e2e run --rm frontend-e2e sh -c "npm ci && npm run e2e -- tests/e2e/workflows/teacher-grading.spec.ts"
```

## Structure
- `api/`: API-level checks.
- `crud/`: Create/update/delete flows.
- `smoke/`: Login and basic navigation.
- `workflows/`: End-to-end user workflows.
- `helpers/`: Shared Playwright helpers.
- `fixtures/`: Seed data and test inputs.
- `global-setup.ts`: One-time setup before tests run.

## Index
- `api/auth.spec.ts`
- `crud/admin-account-delete.spec.ts`
- `crud/admin-assessment-delete.spec.ts`
- `crud/admin-assessment-update.spec.ts`
- `crud/teacher-course-crud.spec.ts`
- `smoke/login-ui.spec.ts`
- `workflows/admin-account-flow.spec.ts`
- `workflows/admin-assessment.spec.ts`
- `workflows/error-paths.spec.ts`
- `workflows/student-submission.spec.ts`
- `workflows/teacher-grading.spec.ts`
- `workflows/teacher-student-workflow.spec.ts`
