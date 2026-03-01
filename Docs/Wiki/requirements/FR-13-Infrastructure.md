# FR-13 Infrastructure (INFRA) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | INFRA |
| **Applies To** | ADMIN (deployment configuration), ALL (development tooling) |
| **Related Issues** | #30 (environment profile system), #32 (OTel instrumentation and collector infrastructure) |
| **Dependencies** | FR-12 ENV (profile-driven service behavior, `ENVIRONMENT` passthrough), FR-11 OBS (OTel Collector and Jaeger service specs) |

---

## 1) Scope

### In Scope
- Docker Compose orchestration for local development stack (database, backend, frontend, pgadmin)
- Compose profile-based optional services (E2E testing, Nginx reverse proxy)
- Backend multi-stage Dockerfile (development hot reload, production Gunicorn)
- Frontend development Dockerfile with hot reload
- Taskfile task runner providing standardized development workflows (~60 tasks)
- Pre-commit hooks for code quality enforcement (Ruff lint/format, file hygiene, branch guard)
- Environment variable passthrough from `.env` to Docker services
- Service dependency ordering and health checks
- OTel Collector and Jaeger services for observability infrastructure (FR-11 OBS)
- Deployment templates for production/staging environments

### Out of Scope
- Production hosting infrastructure (cloud provider, VPS, Kubernetes)
- Certificate automation (certbot/letsencrypt)
- Container registry and image publishing
- Multi-region or multi-node deployment
- CDN configuration
- Database backup and restore automation

---

## 2) Actors

| Role | Type | INFRA domain notes |
|------|------|-------------------|
| Developer | Human operator | Runs `task up`, `task test`, `task lint`; uses Docker Compose and Taskfile for local development workflows. |
| CI Pipeline | Automated agent | Executes lint, format, type check, and test tasks. Currently manual via Taskfile; GitHub Actions planned (INFRA-UC-02). |
| ADMIN | System role | Owns deployment configuration decisions; manages production Docker Compose and `.env` setup. |

**Actor ordering:** Not applicable (infrastructure-level).

> **Note:** INFRA has no user-facing REST endpoints. All behavior is developer tooling and deployment configuration.

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| INFRA-US-01 | Developer | As a developer I can start the full application stack with one command so that I can develop and test without manual service configuration. |
| INFRA-US-02 | CI Pipeline | As a CI pipeline I can run automated tests, linting, and type checking so that code quality is enforced before merging. |
| INFRA-US-03 | Developer | As a developer I can use Taskfile tasks for standardized workflows so that common operations have consistent, documented entry points. |
| INFRA-US-04 | Developer | As a developer I can rely on pre-commit hooks to catch quality issues before commit so that CI failures and review cycles are reduced. |
| INFRA-US-05 | Developer | As a developer I can start observability infrastructure alongside the stack so that I can view distributed traces in Jaeger UI. |

---

## 4) Use Cases

### INFRA-UC-01 — Orchestrate Local Development Stack

**Roles:** Developer
**Trigger:** Developer runs `task up` (or `task up:dev`, `task up:test`, `task up:prod`).

**Preconditions:**
- Docker Desktop or Docker daemon is running.
- `.env` file exists (copied from `.env.template` and configured).

**Main Flow:**
1. Taskfile verifies preconditions (Docker running, `.env` present).
2. Taskfile sets `ENVIRONMENT` variable to the selected profile (`development`, `testing`, or `production`).
3. Docker Compose reads `docker-compose.yml` and `.env`.
4. Database service starts; healthcheck polls `pg_isready` until ready.
5. Backend service waits for database healthcheck to pass (`depends_on` with `condition: service_healthy`).
6. Backend runs startup command sequence: `migrate` → `collectstatic` (production only) → `ensure_admin` → `seed_e2e` (testing only) → `runserver`.
7. Frontend service starts: checks for required binaries, runs `npm ci` if missing, then `npm run dev`.
8. pgAdmin starts and auto-registers database server via `servers.json` and `pgpass`.
9. Taskfile runs `profile_guard.py` to verify backend started with expected profile.
10. All services running; developer can access frontend (port 3000) and backend API (port 8000).

**Postconditions:**
- All core services running and accessible.
- Database migrated; admin user exists; test fixtures seeded (testing profile only).

**Role Coverage:**
> **INFRA-UC-01-ALL**
> - Infrastructure-level; identical behavior for all developer roles.

**Errors:**
**INFRA-UC-01-E1** — Docker not running
- Trigger: Docker daemon unavailable
- Behavior: Taskfile precondition fails with "Docker is not running" message

**INFRA-UC-01-E2** — Missing `.env` file
- Trigger: `.env` file not found in project root
- Behavior: Taskfile precondition fails with "Copy .env.template to .env" message

**INFRA-UC-01-E3** — Port conflict
- Trigger: Ports 5432, 8000, 3000, or 5050 already in use
- Behavior: Docker Compose service fails to bind; error in `docker compose logs`

**INFRA-UC-01-E4** — Profile guard mismatch
- Trigger: Backend started with unexpected `ENVIRONMENT` value
- Behavior: `profile_guard.py` exits with error listing expected vs. actual profile

**Tests:**
**Backend Unit:**
- test_INFRA_UC_01 (startup command sequence executes in correct order)
- test_INFRA_UC_01_E4 (profile guard detects mismatched profile)

**Backend Integration:**
- test_INFRA_UC_01_stack_boot (database, backend, frontend accessible after startup)

**System Tests (Black Box):**
- ST-INFRA-UC-01 (full stack boots with `task up:dev`)
- ST-INFRA-UC-01-E1 (graceful failure when Docker not running)

---

### INFRA-UC-02 — Run Automated CI Pipeline (Deferred)

**Roles:** CI Pipeline
**Trigger:** PR opened or updated via GitHub Actions workflow (target-state; not yet implemented).

**Preconditions:**
- Code checked out.
- Python 3.12 and Node.js environments available.
- Database service available (postgres:17).

**Main Flow:**
1. CI sets `ENVIRONMENT=testing` and `OTEL_ENABLED=false`.
2. CI installs backend dependencies (`pip install -e ".[dev]"`).
3. CI runs `ruff check src tests` (linting).
4. CI runs `ruff format src tests --check` (format verification).
5. CI runs `mypy src` (type checking — when enabled).
6. CI starts database service and sets `DATABASE_URL`.
7. CI runs `pytest tests/ --cov=src` (unit and integration tests with coverage).
8. CI uploads coverage report.
9. If all checks pass, CI reports success; otherwise blocks merge.

**Postconditions:**
- PR status updated with pass/fail for each check.

**Role Coverage:**
> **INFRA-UC-02-ALL**
> - Automated pipeline; no role-specific behavior.

**Errors:**
**INFRA-UC-02-E1** — Lint/format/test failure
- Trigger: Any quality check or test fails
- Behavior: CI exits non-zero; GitHub marks check as failed; merge blocked

**Tests:**
**System Tests (Black Box):**
- ST-INFRA-UC-02 (CI pipeline runs all checks successfully on clean codebase)
- ST-INFRA-UC-02-E1 (CI correctly blocks on lint failure)

---

### INFRA-UC-03 — Execute Development Tasks via Taskfile

**Roles:** Developer
**Trigger:** Developer runs a `task` command.

**Preconditions:**
- Taskfile v3 installed.
- Required services running (task-specific; checked by internal precondition tasks).

**Main Flow:**
1. Developer runs `task <name>` (e.g., `task test:unit:backend`, `task lint`, `task migrate`).
2. Taskfile evaluates preconditions (Docker running, backend container up, correct profile, etc.).
3. Taskfile executes command inside appropriate container via `docker compose exec`.
4. Output displayed to developer.

**Task Categories:**
- **Profiles:** `up`, `up:dev`, `up:test`, `up:prod`, `down`
- **Overlays:** `otel`, `otel:off`, `proxy`, `proxy:off`, `debug`
- **Testing:** `test`, `test:unit:backend`, `test:unit:frontend`, `test:integration:backend`, `test:integration:role`, `test:security`, `test:coverage`, `test:coverage:fr`, `test:e2e`
- **Quality:** `check`, `lint`, `lint:fix`, `format`, `format:check`, `typecheck`, `check:env`
- **Docker:** `docker:logs`, `docker:shell`, `docker:db-shell`, `docker:rebuild`, `docker:clean`
- **Django:** `migrate`, `makemigrations`, `django:shell`, `seed:account`
- **Docs:** `docs`, `docs:schema`, `diagrams:generate`
- **Local:** `local:venv`, `local:sync`

**Postconditions:**
- Requested task executed; output visible to developer.

**Role Coverage:**
> **INFRA-UC-03-ALL**
> - Developer tooling; no role-specific behavior.

**Errors:**
**INFRA-UC-03-E1** — Precondition failure
- Trigger: Required service not running, `.env` missing, or wrong profile
- Behavior: Taskfile exits with descriptive precondition error message

**Tests:**
**Backend Unit:**
- test_INFRA_UC_03 (precondition checks detect missing services)

**System Tests (Black Box):**
- ST-INFRA-UC-03 (task commands execute correctly against running stack)
- ST-INFRA-UC-03-E1 (precondition failures produce clear messages)

---

### INFRA-UC-04 — Enforce Code Quality via Pre-commit Hooks

**Roles:** Developer
**Trigger:** Developer runs `git commit`.

**Preconditions:**
- pre-commit installed (`pip install pre-commit`).
- Hooks installed (`pre-commit install` or `task hooks:install`).

**Main Flow:**
1. Developer stages files and runs `git commit`.
2. Pre-commit runs configured hooks against staged files.
3. Ruff linter checks for errors and applies safe fixes (import sorting, formatting).
4. Ruff formatter enforces consistent code style.
5. File hygiene hooks check for large files (>500KB), trailing whitespace, missing EOF newlines, YAML/TOML syntax.
6. Branch guard prevents direct commits to `master` or `main`.
7. If all hooks pass, commit proceeds.
8. If any hook modifies files, commit is aborted; developer reviews changes, re-stages, and commits again.

**Postconditions:**
- Committed code passes all configured quality checks.

**Role Coverage:**
> **INFRA-UC-04-ALL**
> - Developer tooling; identical for all roles.

**Errors:**
**INFRA-UC-04-E1** — Hook modifies files
- Trigger: Ruff formatter or linter applies fixes
- Behavior: Commit aborted; developer must review, re-stage, and commit

**INFRA-UC-04-E2** — Branch guard triggered
- Trigger: Direct commit to `master` or `main`
- Behavior: Commit rejected with branch protection message

**Tests:**
**System Tests (Black Box):**
- ST-INFRA-UC-04 (hooks run on commit and catch lint errors)
- ST-INFRA-UC-04-E2 (branch guard blocks commit to master)

---

### INFRA-UC-05 — Provision Observability Infrastructure

**Roles:** Developer
**Trigger:** Developer runs `task otel` to enable tracing on a running stack.

**Preconditions:**
- Stack running (`task up:dev` or `task up:test`).
- Backend container accessible.

**Main Flow:**
1. Taskfile resolves current profile from running backend container.
2. Taskfile creates trace output directory (`Docs/diagrams/otel/`).
3. Taskfile restarts backend with `OTEL_ENABLED=true`, preserving current profile.
4. Backend `configure_tracing()` activates OTel instrumentation (FR-11 OBS-UC-01).
5. OTel Collector receives spans from backend via OTLP/HTTP.
6. Collector forwards traces to Jaeger.
7. `profile_guard.py` verifies backend restarted with expected profile.
8. Traces visible in Jaeger UI at `http://localhost:16686`.

**Postconditions:**
- Backend exporting spans to collector and/or JSONL trace file.
- Jaeger UI available for trace visualization.

**Role Coverage:**
> **INFRA-UC-05-ALL**
> - Developer tooling; identical for all roles.

**Errors:**
**INFRA-UC-05-E1** — Collector service not running
- Trigger: OTel Collector container not started or unhealthy
- Behavior: Backend starts but OTLP export fails silently; file export continues (FR-11 OBS-CN-03)

**Tests:**
**Backend Integration:**
- test_INFRA_UC_05_otel_toggle (tracing activates/deactivates via `task otel`/`task otel:off`)

**System Tests (Black Box):**
- ST-INFRA-UC-05 (traces appear in Jaeger after `task otel` and API requests)
- ST-INFRA-UC-05-E1 (backend starts gracefully without collector)

---

## 5) Constraints

### INFRA-CN-01 — Service Dependency Ordering
- Backend must wait for database healthcheck (`pg_isready`) to pass before starting.
- Database healthcheck: `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`, interval 10s, timeout 5s, 5 retries.
- Backend uses `depends_on` with `condition: service_healthy`.
- Frontend depends on backend (start ordering only; no healthcheck on backend).
- **Applies to:** INFRA-UC-01
- **Implements:** NFR-REL-01 (Service Startup Reliability)

### INFRA-CN-02 — Postgres Version Consistency
- All Docker Compose files and deployment templates must use the same Postgres major version.
- Current: `docker-compose.yml` uses `postgres:17-alpine`; deployment templates use `postgres:15`.
- Target: sync all to `postgres:17-alpine`.
- **Applies to:** INFRA-UC-01, INFRA-UC-02
- **Implements:** NFR-OPS-06 (Infrastructure Version Consistency)

### INFRA-CN-03 — Environment Variable Passthrough
- Docker Compose backend service must pass `ENVIRONMENT` from host `.env` to container.
- Taskfile profile tasks (`up:dev`, `up:test`, `up:prod`) must explicitly set `ENVIRONMENT` to avoid ambiguous runtime mode.
- All env vars listed in FR-12 section 6.2 must be passed through to the backend container.
- **Applies to:** INFRA-UC-01, INFRA-UC-03
- **Implements:** NFR-OPS-01 (Environment Profile System)

### INFRA-CN-04 — Hot Reload Support
- Backend: source directory mounted as volume (`./backend/src:/app/src:cached`); Django `runserver` detects file changes.
- Frontend: project directory mounted as volume (`./frontend:/app:cached`); named volume for `node_modules` to avoid platform conflicts; Next.js dev server detects file changes.
- Hot reload must work without container restart for both backend and frontend code changes.
- **Applies to:** INFRA-UC-01

### INFRA-CN-05 — Pre-commit Hook Coverage
- Ruff linter with safe auto-fixes (import sorting, formatting).
- Ruff formatter (consistent code style).
- File hygiene: large file guard (500KB), trailing whitespace fix, EOF newline fix, YAML/TOML syntax check.
- Branch protection: block direct commits to `master` and `main`.
- Hooks scope to `^backend/` for Ruff to avoid false positives on frontend files.
- mypy hook disabled until DTO work completes (issues #3, #4).
- **Applies to:** INFRA-UC-04
- **Implements:** NFR-MAINT-01 (Code Quality Enforcement)

### INFRA-CN-06 — CI Required Checks
- CI pipeline must run: `ruff check` (lint), `ruff format --check` (format), `pytest --cov` (tests with coverage).
- CI must set `ENVIRONMENT=testing` and `OTEL_ENABLED=false`.
- CI must use `postgres:17` for database service.
- All checks must pass before PR merge is allowed.
- Coverage threshold: warning at <80%.
- **Applies to:** INFRA-UC-02
- **Implements:** NFR-MAINT-02 (Automated Quality Gates)

### INFRA-CN-07 — Docker Image Pinning
- Core services must pin explicit image tags; `:latest` is prohibited for database and E2E images.
- Current pins: `postgres:17-alpine`, `mcr.microsoft.com/playwright:v1.57.0-jammy`, `python:3.12-slim`.
- pgAdmin uses `dpage/pgadmin4:latest` (acceptable for development-only tooling).
- Nginx uses `nginx:latest` (acceptable for development proxy; production must pin).
- OTel Collector and Jaeger images must be pinned to specific versions (FR-11 OBS-CN-09 specifies `otel/opentelemetry-collector-contrib:0.120.0` and `jaegertracing/all-in-one:1.65`).
- **Applies to:** INFRA-UC-01, INFRA-UC-05
- **Implements:** NFR-OPS-07 (Reproducible Builds)

### INFRA-CN-08 — Multi-stage Build
- Backend Dockerfile uses multi-stage build: builder stage installs all dependencies; production stage copies only runtime artifacts.
- Production image runs as non-root user (`django:django`).
- Production uses Gunicorn WSGI server; development overrides to Django `runserver` via docker-compose.yml command.
- Static files collected only in production (`collectstatic --noinput`).
- **Applies to:** INFRA-UC-01
- **Implements:** NFR-SEC-07 (Container Security)

### INFRA-CN-09 — Compose Profile-based Service Activation
- Optional services use Docker Compose profiles to avoid starting by default.
- `e2e` profile: `frontend-e2e` (Playwright) container for E2E testing.
- `proxy` profile: Nginx reverse proxy for production-like routing.
- Core services (database, backend, frontend, pgadmin) start without profile flags.
- **Applies to:** INFRA-UC-01

### INFRA-CN-10 — Taskfile Precondition Checks
- All Taskfile tasks that require Docker must verify Docker daemon is running (`_check:docker`).
- Tasks requiring running services must verify container status (`_check:backend-running`, `_check:frontend-running`).
- Integration and E2E tests must verify `ENVIRONMENT=testing` (`_check:testing-profile`).
- OTel overlay tasks must verify profile is resolvable from running backend (`_check:profile-resolvable`).
- Precondition failures must produce clear, actionable error messages.
- **Applies to:** INFRA-UC-03
- **Implements:** NFR-MAINT-03 (Developer Experience)

---

## 6) Infrastructure Contract

INFRA has no user-facing REST API endpoints. All behavior is Docker Compose orchestration, Taskfile tasks, and pre-commit hooks.

### Docker Compose Services

| Service | Image | Ports | Profile | Purpose |
|---------|-------|-------|---------|---------|
| `database` | `postgres:17-alpine` | (internal) | default | PostgreSQL database with healthcheck |
| `backend` | Built from `backend/Dockerfile` | `8000` | default | Django REST API with hot reload |
| `frontend` | Built from `frontend/Dockerfile.dev` | `3000` | default | Next.js dev server with hot reload |
| `pgadmin` | `dpage/pgadmin4:latest` | `5050` | default | Database management UI |
| `frontend-e2e` | `mcr.microsoft.com/playwright:v1.57.0-jammy` | (none) | `e2e` | Playwright E2E test runner |
| `nginx` | `nginx:latest` | `80` | `proxy` | Reverse proxy |
| `otel-collector` | `otel/opentelemetry-collector-contrib:0.120.0` | `4317`, `4318` | default | OTel span receiver (to be added) |
| `jaeger` | `jaegertracing/all-in-one:1.65` | `16686` | default | Trace visualization UI (to be added) |

### Docker Volumes

| Volume | Purpose |
|--------|---------|
| `postgres_data` | Persistent database storage |
| `frontend_node_modules` | Persistent node_modules across container restarts |
| `frontend_npm_cache` | Persistent npm cache to reduce download time |
| `playwright_node_modules` | Persistent node_modules for E2E container |

### Network

Single bridge network: `eel-network`. All services communicate via service names as DNS hostnames.

### Backend Startup Command Sequence

```
migrate → collectstatic (production only) → ensure_admin → seed_e2e (testing only) → runserver
```

### Taskfile Task Summary

| Category | Count | Key Tasks |
|----------|-------|-----------|
| Profiles | 5 | `up`, `up:dev`, `up:test`, `up:prod`, `down` |
| Overlays | 5 | `otel`, `otel:off`, `proxy`, `proxy:off`, `debug` |
| Testing | ~18 | `test`, `test:unit:*`, `test:integration:*`, `test:security`, `test:coverage:*`, `test:e2e` |
| Quality | 7 | `check`, `lint`, `lint:fix`, `format`, `format:check`, `typecheck`, `check:env` |
| Docker | ~10 | `docker:logs`, `docker:shell`, `docker:rebuild`, `docker:clean` |
| Django | ~7 | `migrate`, `makemigrations`, `django:shell`, `seed:account` |
| Docs | 4 | `docs`, `docs:schema`, `diagrams:generate`, `diagrams:index` |
| Local | 2 | `local:venv`, `local:sync` |

---

## 7) Error Model

INFRA errors are operational. They manifest as Docker Compose failures, Taskfile precondition errors, or pre-commit hook rejections — not HTTP responses.

| Scenario | Behavior | Source |
|----------|----------|--------|
| Docker daemon not running | Taskfile precondition fails with "Docker is not running" | INFRA-UC-01-E1 |
| `.env` file missing | Taskfile precondition fails with "Copy .env.template" | INFRA-UC-01-E2 |
| Port already in use | Docker Compose service fails to bind; visible in logs | INFRA-UC-01-E3 |
| Profile guard mismatch | `profile_guard.py` exits with expected vs. actual profile | INFRA-UC-01-E4 |
| CI check failure | CI exits non-zero; PR merge blocked | INFRA-UC-02-E1 |
| Taskfile precondition failure | Clear error message (service not running, wrong profile) | INFRA-UC-03-E1 |
| Pre-commit hook modifies files | Commit aborted; developer re-stages and commits | INFRA-UC-04-E1 |
| Direct commit to master/main | Commit rejected by branch guard | INFRA-UC-04-E2 |
| OTel Collector not running | Backend starts; OTLP export fails silently; file export continues | INFRA-UC-05-E1 |

---

## 8) Test Strategy by Layer

### Naming Convention

- Domain aggregator: `test_INFRA_UC_##`
- Role test: `test_INFRA_UC_##_ALL` (infrastructure-level; no role-specific variants)
- Error test: `test_INFRA_UC_##_E#`
- Constraint test: `test_INFRA_CN_##`
- System tests: `ST-INFRA-UC-##` and `ST-INFRA-UC-##-E#`

### Backend Unit

- Startup command sequence: `migrate`, `ensure_admin`, `seed_e2e` execute in correct order with correct profile guards.
- Profile guard: detects mismatched `ENVIRONMENT` between Taskfile expectation and running backend.
- Precondition checks: internal Taskfile validation tasks detect missing services and wrong profiles.
- Constraint coverage: INFRA-CN-01 (dependency ordering), INFRA-CN-03 (env passthrough), INFRA-CN-10 (precondition checks).

### Backend Integration

- Stack boot: full `task up:dev` produces accessible database, backend, and frontend.
- OTel toggle: `task otel` activates tracing; `task otel:off` deactivates; profile preserved across toggle.
- Profile-aware startup: `task up:test` seeds E2E fixtures; `task up:dev` does not.
- Hot reload: backend code changes reflected without container restart.

### System Tests (Black Box)

- ST-INFRA-UC-01 (full stack boots with `task up:dev`)
- ST-INFRA-UC-01-E1 (graceful failure when Docker not running)
- ST-INFRA-UC-02 (CI pipeline runs all checks on clean codebase)
- ST-INFRA-UC-03 (task commands execute against running stack)
- ST-INFRA-UC-04 (pre-commit hooks catch lint errors on commit)
- ST-INFRA-UC-04-E2 (branch guard blocks commit to master)
- ST-INFRA-UC-05 (traces visible in Jaeger after `task otel`)

---

## 9) NFR Cross-References

- **NFR-REL-01** (Service Startup Reliability)
  - Database healthcheck prevents backend from starting before DB is ready (INFRA-CN-01).
  - Backend startup command sequence is ordered and idempotent.
- **NFR-OPS-01** (Environment Profile System)
  - Docker Compose and Taskfile pass `ENVIRONMENT` explicitly to backend (INFRA-CN-03).
  - Profile tasks (`up:dev`, `up:test`, `up:prod`) enforce explicit profile selection.
- **NFR-OPS-06** (Infrastructure Version Consistency)
  - Postgres version must match across compose files and deployment templates (INFRA-CN-02).
- **NFR-OPS-07** (Reproducible Builds)
  - Docker images pinned to specific tags for core services (INFRA-CN-07).
- **NFR-SEC-07** (Container Security)
  - Production backend image runs as non-root user; multi-stage build minimizes attack surface (INFRA-CN-08).
- **NFR-MAINT-01** (Code Quality Enforcement)
  - Pre-commit hooks enforce lint, format, and file hygiene before commit (INFRA-CN-05).
- **NFR-MAINT-02** (Automated Quality Gates)
  - CI pipeline blocks merge on lint, format, or test failure (INFRA-CN-06).
- **NFR-MAINT-03** (Developer Experience)
  - Taskfile precondition checks produce clear, actionable error messages (INFRA-CN-10).

---

## 10) Cross-Domain References

| FR | Reference | Notes |
|----|-----------|-------|
| FR-01 AUTH | OAuth env vars passed to backend and frontend | Docker Compose passes `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID` to backend and frontend services. |
| FR-04 USER | `seed_e2e` creates test users | Backend startup command runs `seed_e2e` in testing profile to create deterministic test users (ENV-UC-04). |
| FR-11 OBS | OTel Collector and Jaeger services | FR-11 defines service specs (`otel-collector:0.120.0`, `jaeger:1.65`) and collector config. FR-13 hosts them in `docker-compose.yml`. `task otel` overlay enables tracing on running backend. |
| FR-12 ENV | `ENVIRONMENT` passthrough and profile tasks | FR-12 defines the profile system; FR-13 passes `ENVIRONMENT` via Docker Compose and Taskfile. Profile tasks (`up:dev/test/prod`) and `profile_guard.py` enforce explicit profile selection (ENV-CN-12). |

---

## 11) Current Implementation Alignment Notes

This spec defines the target FR-13 contract. Current codebase has substantial infrastructure already implemented:

1. **Docker Compose implemented.** `docker-compose.yml` (231 lines) defines 5 services: database, backend, frontend, pgadmin, nginx. Frontends use named volumes for `node_modules`. Backend uses multi-stage Dockerfile with non-root production user. `ENVIRONMENT` passthrough already wired (`ENVIRONMENT=${ENVIRONMENT:-development}`).
2. **OTel services not yet added.** `otel-collector` and `jaeger` services defined in FR-11 OBS-CN-09 but not yet in `docker-compose.yml`. Collector config file (`otel-collector-config.yaml`) does not exist yet. `task otel` overlay is implemented but relies on backend-level `OTEL_ENABLED` toggle only.
3. **Taskfile implemented.** `Taskfile.yml` (921 lines) provides ~60 tasks across 8 categories. Profile tasks (`up:dev/test/prod`), overlay tasks (`otel`, `proxy`), testing tasks (unit/integration/security/E2E/coverage), quality tasks, Docker management, Django management, diagrams, and local dev support all operational.
4. **Pre-commit hooks implemented.** `.pre-commit-config.yaml` (79 lines) configures Ruff lint/format, file hygiene hooks, and branch guard. mypy hook commented out pending DTO work. All hooks scope to `^backend/` for Ruff.
5. **Postgres version mismatch exists.** `docker-compose.yml` uses `postgres:17-alpine`; `Deployment/templates/docker-compose.template.yml` and `docker-compose.dev.template.yml` use `postgres:15`. Must sync to `postgres:17-alpine`.
6. **No GitHub Actions CI.** `.github/workflows/` directory does not exist. CI is currently manual via Taskfile tasks. GitHub Actions workflow configuration is documented as future work (INFRA-UC-02).
7. **E2E infrastructure implemented.** `frontend-e2e` service uses Playwright `v1.57.0-jammy` image under `e2e` compose profile. E2E seeding script, recording scripts, and role-filtered test execution all operational via Taskfile.
8. **Deployment templates exist but are stale.** `Deployment/templates/` contains 12 template files (compose, pytest, pre-commit, Playwright config, security tools). Need postgres version sync and `ENVIRONMENT` variable alignment.
