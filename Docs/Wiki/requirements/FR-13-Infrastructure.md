# FR-13 Infrastructure (INFRA) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | INFRA |
| **Applies To** | ADMIN (deployment configuration), ALL (development tooling) |
| **Related Issues** | #30 (environment profile system) |
| **Dependencies** | FR-12 ENV (profile-driven service behavior, `ENVIRONMENT` passthrough) |

---

## 1) Scope

### In Scope
- Docker Compose orchestration for the shared proxy plus profile-specific app stacks
- Split Compose files for proxy, dev, test, and prod
- Backend multi-stage Dockerfile (development hot reload, production Gunicorn)
- Frontend development Dockerfile with hot reload
- Taskfile task runner providing standardized development workflows
- Pre-commit hooks for code quality enforcement (Ruff lint/format, file hygiene, branch guard)
- Environment materialization from root `.env` into generated runtime env files
- Service dependency ordering and health checks
- Deployment templates for production/staging environments

### Out of Scope
- GitHub Actions CI/CD pipeline configuration (documented as future work, not yet implemented)
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
| Developer | Human operator | Runs `task up:*`, `task down:*`, `task test*`, and runtime tasks; uses Docker Compose and Taskfile for local development workflows. |
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
---

## 4) Use Cases

### INFRA-UC-01 — Orchestrate Local Development Stack

**Roles:** Developer
**Trigger:** Developer runs `task up:dev`, `task up:test`, or `task up:prod`.

**Preconditions:**
- Docker Desktop or Docker daemon is running.
- `.env` file exists (copied from `.env.template` and configured).

**Main Flow:**
1. Taskfile verifies preconditions (Docker running, `.env` present).
2. Taskfile prepares and validates the generated profile env file.
3. Docker Compose reads the profile-specific compose file and generated env.
4. Database service starts; healthcheck polls `pg_isready` until ready.
5. Backend and frontend wait for dependency healthchecks and become routable through the shared proxy.
6. Proxy remains the only public entrypoint for browser and SSR traffic.
7. All services running; developer can access the selected profile through the proxy ports.

**Postconditions:**
- All core services running and accessible.
- Database volume preserved; backend and frontend reachable through the proxy.

**Role Coverage:**
> **INFRA-UC-01-ALL**
> - Infrastructure-level; identical behavior for all developer roles.

**Errors:**
**INFRA-UC-01-E1** — Docker not running
- Trigger: Docker daemon unavailable
- Behavior: Taskfile precondition fails with "Docker is not running" message

**INFRA-UC-01-E2** — Missing or uninitialized `.env` file
- Trigger: `.env` file not found in project root or not yet initialized from `.env.template`
- Behavior: `task env:local` / `task env:server` creates `.env`; `task env:init` then materializes runtime env files

**INFRA-UC-01-E3** — Port conflict
- Trigger: Ports 5432, 8000, 3000, or 5050 already in use
- Behavior: Docker Compose service fails to bind; error in `docker compose logs`

**INFRA-UC-01-E4** — Environment policy validation failure
- Trigger: Generated runtime env fails policy checks for the selected profile
- Behavior: `_check:env:<profile>` fails before startup and lists the invalid keys or topology mismatch

**Tests:**
**Backend Unit:**
- test_INFRA_UC_01_startup_sequence (startup command sequence executes in correct order)
- test_INFRA_UC_01_E4_env_policy_failure (env validation detects insecure or malformed runtime values)

**Backend Integration:**
- test_INFRA_UC_01_stack_boot (database, backend, frontend accessible after startup)

**System Tests (Black Box):**
- ST-INFRA-UC-01 (full stack boots with `task up:dev`)
- ST-INFRA-UC-01-E1 (graceful failure when Docker not running)

---

### INFRA-UC-02 — Run Automated CI Pipeline

**Roles:** CI Pipeline
**Trigger:** PR opened or updated (future: GitHub Actions workflow trigger).

**Preconditions:**
- Code checked out.
- Python 3.12 and Node.js environments available.
- Database service available (postgres:17).

**Main Flow:**
1. CI sets `ENVIRONMENT=testing`.
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
1. Developer runs `task <name>` (e.g., `task up:dev`, `task test:backend`, `task status:test`).
2. Taskfile evaluates preconditions (Docker running, backend container up, correct profile, etc.).
3. Taskfile executes command inside appropriate container via `docker compose exec`.
4. Output displayed to developer.

**Task Categories:**
- **Env:** `env:local`, `env:server`, `env:init`
- **Profiles:** `up:dev`, `up:test`, `up:prod`, `down:dev`, `down:test`, `down:prod`
- **Runtime:** `status:*`, `logs:*`, `restart:*`, `rebuild:*`
- **Testing:** `test`, `test:backend`, `test:frontend`
- **Dangerous:** `CONFIRM_DESTROY_EELAB=EELAB task destroy:all`

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
**Backend Unit:** _(no backend unit test for precondition checks — covered by system tests)_

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

### INFRA-UC-05 — Deferred Optional Tooling

**Roles:** Developer
**Trigger:** Team chooses to reintroduce additional runtime tooling in the future.

**Current State:** OTEL, Jaeger, and browser E2E containers were removed from the active runtime model. They remain deferred until rebuilt intentionally against the new task and compose contract.

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
- Current target: `postgres:17-alpine`.
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
- CI must set `ENVIRONMENT=testing`.
- CI must use `postgres:17` for database service.
- All checks must pass before PR merge is allowed.
- Coverage threshold: warning at <80%.
- **Applies to:** INFRA-UC-02
- **Implements:** NFR-MAINT-02 (Automated Quality Gates)

### INFRA-CN-07 — Docker Image Pinning
- Core services must pin explicit image tags; `:latest` is prohibited for core runtime images.
- Current pins: `postgres:17-alpine`, `nginx:1.27-alpine`, and the repo Dockerfiles for backend/frontend.
- **Applies to:** INFRA-UC-01, INFRA-UC-05
- **Implements:** NFR-OPS-07 (Reproducible Builds)

### INFRA-CN-08 — Multi-stage Build
- Backend Dockerfile uses a production-ready image with explicit dev/test overrides in compose.
- Production image runs with production settings; development overrides to Django `runserver` via `compose.dev.yml`.
- Static files are served behind the shared proxy and routed explicitly.
- **Applies to:** INFRA-UC-01
- **Implements:** NFR-SEC-07 (Container Security)

### INFRA-CN-09 — Separate Compose Stacks By Profile
- Runtime stacks use separate compose files for `proxy`, `dev`, `test`, and `prod`.
- Optional tooling is not started by default and must be reintroduced intentionally in future work.
- Core services for app profiles are `db`, `backend`, and `frontend`; the shared `proxy` stack owns public ingress.
- **Applies to:** INFRA-UC-01

### INFRA-CN-10 — Taskfile Precondition Checks
- All Taskfile tasks that require Docker must verify Docker daemon is running (`_check:docker`).
- Env-sensitive tasks must prepare and validate generated runtime env files before startup.
- Test tasks must ensure the testing stack is up and healthy before execution.
- Precondition failures must produce clear, actionable error messages.
- **Applies to:** INFRA-UC-03
- **Implements:** NFR-MAINT-03 (Developer Experience)

---

## 6) Infrastructure Contract

INFRA has no user-facing REST API endpoints. All behavior is Docker Compose orchestration, Taskfile tasks, and pre-commit hooks.

### Docker Compose Services

| Service | Image | Ports | Profile | Purpose |
|---------|-------|-------|---------|---------|
| `proxy` | `nginx:1.27-alpine` | `80`, `443`, `8080`, `8443`, `9080`, `9443` | proxy | Shared ingress and routing for dev/test/prod |
| `db` | `postgres:17-alpine` | (internal) | dev/test/prod | PostgreSQL database with healthcheck |
| `backend` | Built from `backend/Dockerfile` | `8000` | dev/test/prod | Django REST API |
| `frontend` | Built from `frontend/Dockerfile*` | `3000` | dev/test/prod | Next.js frontend |

### Docker Volumes

| Volume | Purpose |
|--------|---------|
| `eelab-*-db-data` | Persistent profile-scoped database storage |
| `eelab-*-media-data` | Persistent profile-scoped media storage |
| `eelab-*-artifact-data` | Persistent profile-scoped artifact storage |
| `frontend_node_modules` | Persistent node_modules across container restarts |
| `frontend_npm_cache` | Persistent npm cache to reduce download time |

### Network

Shared proxy network: `eelab-proxy`. Each profile stack also owns a private app network (`eelab-dev-app`, `eelab-test-app`, `eelab-prod-app`) so services remain isolated while still being routable through the shared proxy.

### Taskfile Task Summary

| Category | Count | Key Tasks |
|----------|-------|-----------|
| Profiles | 6 | `up:*`, `down:*` |
| Runtime | 12 | `status:*`, `logs:*`, `restart:*`, `rebuild:*` |
| Testing | 3 | `test`, `test:backend`, `test:frontend` |
| Env | 3 | `env:local`, `env:server`, `env:init` |
| Docs | 0 | Documentation is maintained directly in the repo; no public docs tasks are part of the retained task surface |
| Safety | 1 | `destroy:all` |

---

## 7) Error Model

INFRA errors are operational. They manifest as Docker Compose failures, Taskfile precondition errors, or pre-commit hook rejections — not HTTP responses.

| Scenario | Behavior | Source |
|----------|----------|--------|
| Docker daemon not running | Taskfile precondition fails with "Docker is not running" | INFRA-UC-01-E1 |
| `.env` file missing | `task env:local` / `task env:server` creates `.env`, then `task env:init` materializes runtime envs | INFRA-UC-01-E2 |
| Port already in use | Docker Compose service fails to bind; visible in logs | INFRA-UC-01-E3 |
| Environment policy mismatch | `_check:env:<profile>` fails before startup and lists invalid values | INFRA-UC-01-E4 |
| CI check failure | CI exits non-zero; PR merge blocked | INFRA-UC-02-E1 |
| Taskfile precondition failure | Clear error message (service not running, wrong profile) | INFRA-UC-03-E1 |
| Pre-commit hook modifies files | Commit aborted; developer re-stages and commits | INFRA-UC-04-E1 |
| Direct commit to master/main | Commit rejected by branch guard | INFRA-UC-04-E2 |
---

## 8) Test Strategy by Layer

### Naming Convention

- Domain aggregator: `test_INFRA_UC_nn`
- Role test: `test_INFRA_UC_nn_ALL` (infrastructure-level; no role-specific variants)
- Error test: `test_INFRA_UC_nn_En`
- Constraint test: `test_INFRA_CN_nn`
- System tests: `ST-INFRA-UC-##` and `ST-INFRA-UC-##-E#`

### Backend Unit

- Startup command sequence remains non-destructive and profile-scoped.
- Precondition checks: internal Taskfile validation tasks detect missing services and wrong profiles.
- Constraint coverage: INFRA-CN-01 (dependency ordering), INFRA-CN-03 (env passthrough), INFRA-CN-10 (precondition checks).

### Backend Integration

- Stack boot: full `task up:dev` produces accessible database, backend, and frontend.
- Profile-aware startup: `task up:test` and `task up:dev` remain isolated but non-destructive.
- Hot reload: backend code changes reflected without container restart.

### System Tests (Black Box)

- ST-INFRA-UC-01 (full stack boots with `task up:dev`)
- ST-INFRA-UC-01-E1 (graceful failure when Docker not running)
- ST-INFRA-UC-02 (CI pipeline runs all checks on clean codebase)
- ST-INFRA-UC-03 (task commands execute against running stack)
- ST-INFRA-UC-04 (pre-commit hooks catch lint errors on commit)
- ST-INFRA-UC-04-E2 (branch guard blocks commit to master)

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
| FR-12 ENV | `ENVIRONMENT` passthrough and profile tasks | FR-12 defines the profile system; FR-13 passes `ENVIRONMENT` via generated runtime env files and Taskfile. Profile tasks (`up:dev/test/prod`) and `_check:env:<profile>` enforce explicit profile selection and policy validation. |

---

## 11) Current Implementation Alignment Notes

All FR-13 infrastructure contracts are implemented. Status by area:

1. **Docker Compose — DONE.** Runtime is split into `docker/compose.proxy.yml`, `docker/compose.dev.yml`, `docker/compose.test.yml`, and `docker/compose.prod.yml`. Named volumes and networks are explicit and profile-scoped.
2. **Taskfile — DONE.** Public tasks are limited to env bootstrap, profile up/down, runtime inspection, testing, and one destructive reset command.
3. **Pre-commit hooks — DONE.** `.pre-commit-config.yaml` configures Ruff lint/format (scoped to `^backend/`), file hygiene (large file guard, trailing whitespace, EOF newline, YAML/TOML check), and branch guard (`master`/`main`). mypy disabled pending DTO work (issues #3, #4).
4. **Postgres version consistency — DONE.** All compose files and deployment templates use `postgres:17-alpine` (INFRA-CN-02).
5. **GitHub Actions CI — DEFERRED.** `.github/workflows/` does not exist. CI is manual via Taskfile. GitHub Actions is documented as future work per INFRA-UC-02 scope note. No blocker for current development workflow.
6. **Deployment templates — DONE.** `Deployment/templates/` mirror the shared proxy plus split dev/test/prod compose model. Traefik-era templates were removed.
7. **Infrastructure contract tests — DONE.** FR-traceable tests in `backend/tests/unit/test_infrastructure_contracts.py` validate the rebuilt task and compose surface.
