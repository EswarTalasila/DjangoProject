# Task Runner

| Field | Value |
|-------|-------|
| **Status** | DRAFT |
| **Scope** | Task command contract and environment-aware testing interface |
| **Applies To** | Development workflow, test orchestration, environment profiles |
| **Related FRs** | FR-01, FR-02, FR-12 |

---

## 1) Purpose

Define a clean Task command interface that:
- maps to environment profile behavior (`development`, `testing`, `production`)
- supports granular test execution by layer and role
- avoids command bloat by composing commands from a small stable set

This is a contract/spec page for cleanup work; it is not a line-by-line mirror of current `Taskfile.yml`.

---

## 2) Environment-Aware Command Groups

### Profile startup

| Command | Profile | Intent |
|---|---|---|
| `task up:dev` | development | Start local developer stack with debug-friendly defaults |
| `task up:test` | testing | Start test profile stack with deterministic testing behavior |
| `task up:prod` | production | Start production-like stack with strict guards |

Rules:
- Each profile command must explicitly set `ENVIRONMENT`.
- Implicit profile startup without `ENVIRONMENT` is non-compliant with FR-12.

### Profile teardown

| Command | Intent |
|---|---|
| `task down` | Stop running services for current profile |
| `task down:proxy` | Stop services including proxy profile containers |

---

## 3) Testing Interface Contract

### Unit test commands

| Command | Scope |
|---|---|
| `task test:unit` | Run frontend + backend unit tests |
| `task test:unit:backend` | Backend unit only |
| `task test:unit:frontend` | Frontend unit only |

### Integration test commands

| Command | Scope |
|---|---|
| `task test:integration` | Run all integration suites |
| `task test:integration:backend` | Backend integration only |
| `task test:integration:frontend` | Frontend integration only |
| `task test:integration:role -- <role>` | Role-filtered integration tests (`admin`, `researcher`, `teacher`, `student`) |

### Security, E2E, and system tests

| Command | Scope |
|---|---|
| `task test:security` | Security tests (authz, abuse, validation) |
| `task test:e2e` | Playwright full-flow tests |
| `task test:system` | Black-box scripted system tests (ST-* tracing) |
| `task test:all` | Full pipeline (unit + integration + security + e2e + system where applicable) |

### Testing behavior policy

- Frontend unit and frontend integration tests may use API mocking.
- Backend unit and backend integration tests must run against real backend logic.
- Role-filtered integration commands should map directly to requirement role stand-ins.
- E2E seeding should default to deterministic seed values; env overrides are optional.

---

## 4) Database Policy for Testing

Testing environment must differentiate between developer data and test data.

| Context | Database policy |
|---|---|
| development | Persistent local dev DB (manual reset) |
| testing | Isolated test DB instance/namespace with deterministic seed baseline |
| production | Production data only; seed commands blocked |

Requirements:
- `task up:test` must not reuse development DB state.
- Integration and E2E runs must be reproducible from a known baseline.
- Test teardown/reset command should be explicit (`task test:reset-db` or equivalent).

---

## 5) Command Naming and Stability Rules

- Keep command names explicit and composable; avoid aliases that hide profile or layer.
- Prefer depth `group:subgroup[:filter]` rather than ad-hoc names.
- New task commands must map to at least one requirement/testing artifact (FR/UC/CN/ST).
- Deprecate commands by documenting replacement and removal timeline.

---

## 6) Minimum Command Set (Target)

This set is the baseline to keep as stable public interface:

- `up:dev`, `up:test`, `up:prod`, `down`, `down:proxy`
- `test:unit`, `test:unit:backend`, `test:unit:frontend`
- `test:integration`, `test:integration:backend`, `test:integration:frontend`, `test:integration:role`
- `test:security`, `test:e2e`, `test:system`, `test:all`
- `test:reset-db`

Everything else is optional/internal and should not be part of the core developer contract.

---

## 7) Traceability Notes

- FR-12 governs profile selection, startup guards, and tooling gates.
- FR-01 and FR-02 govern auth/registration test scenarios that these commands execute.
- `Testing-Index.md` remains source of truth for layer definitions and naming conventions.
- `Diagnostics-Index.md` is the source of truth for startup diagnostics code meanings, severities, and FR/NFR trace mappings (`ENV-*`, `ENV-P*`).
