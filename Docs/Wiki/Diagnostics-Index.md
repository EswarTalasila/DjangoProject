# Diagnostics -- Index

| Field | Value |
|-------|-------|
| **Status** | DRAFT |
| **Scope** | Runtime diagnostics code contract and traceability |
| **Applies To** | ENV profile/runtime checks, Task startup diagnostics |
| **Related FRs** | FR-12 |

---

## 1) Purpose

Define a single registry for diagnostics codes emitted by:
- Django management command: `manage.py env_report`
- Task startup guard: `scripts/runtime/profile_guard.py`

This registry is the lookup contract for:
- code meaning
- severity by profile
- fix hints
- FR/NFR/test traceability

---

## 2) Namespace Rules

| Prefix | Meaning | Primary Source |
|---|---|---|
| `ENV-*` | Environment configuration diagnostics | `env_report.py` |
| `ENV-P*` | Profile startup orchestration diagnostics | `profile_guard.py` |
| `MIG-*` | Migration/bootstrap diagnostics (reserved) | Entry-point/runtime orchestration |
| `SVC-*` | Service dependency diagnostics (reserved) | Runtime orchestration/health checks |
| `SEC-*` | Security posture diagnostics (reserved) | Runtime security checks |

Rules:
- Existing codes are immutable once published (no repurposing).
- New codes must be additive and documented here before release.
- Every new code must map to at least one FR constraint and one NFR entry.

---

## 3) Severity Model by Profile

| Rule | development | testing | production |
|---|---|---|---|
| `strict_in_production=True` checks | `WARN` | `WARN` | `ERROR` |
| Non-strict checks | `WARN` | `WARN` | `WARN` |
| Startup guard failures (`ENV-P*`) | `ERROR` | `ERROR` | `ERROR` |

Notes:
- Production startup must fail when any `ERROR` code is emitted.
- Development/testing warnings are actionable but non-blocking.

---

## 4) Code Registry

| Code | Trigger (short) | Dev | Test | Prod | Hint (short) | Source | Implementation Status |
|---|---|---|---|---|---|---|---|
| `ENV-W001` | Requested profile differs from runtime `ENVIRONMENT` | WARN | WARN | WARN | Run check with matching profile/env | `env_report` | Implemented |
| `ENV-W002` | `DJANGO_DEBUG` override set outside development | WARN | WARN | WARN | Remove `DJANGO_DEBUG` override for test/prod | `env_report` | Implemented |
| `ENV-S001` | `DJANGO_SECRET_KEY` default/insecure | WARN | WARN | ERROR | Set unique random secret | `env_report` | Implemented |
| `ENV-A001` | `ADMIN_EMAIL` default identity | WARN | WARN | ERROR | Use non-default admin email | `env_report` | Implemented |
| `ENV-A002` | `ADMIN_PASSWORD` weak/default | WARN | WARN | ERROR | Use strong non-default password (>=12) | `env_report` | Implemented |
| `ENV-D001` | `DATABASE_URL` appears default/insecure | WARN | WARN | ERROR | Use non-default DB credentials/host | `env_report` | Implemented |
| `ENV-O001` | Missing Google OAuth backend credentials | WARN | WARN | ERROR | Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` | `env_report` | Implemented |
| `ENV-N001` | Production `DJANGO_ALLOWED_HOSTS` includes localhost | N/A | N/A | ERROR | Use production hostnames only | `env_report` | Implemented |
| `ENV-N002` | Production CORS includes wildcard/localhost | N/A | N/A | ERROR | Use explicit trusted origins only | `env_report` | Implemented |
| `ENV-T001` | Production OTEL enabled without OTLP endpoint | N/A | N/A | ERROR | Set OTLP endpoint or disable OTEL | `env_report` | Implemented |
| `ENV-T002` | Production `OTEL_TRACE_FILE` set | N/A | N/A | ERROR | Clear file exporter in production | `env_report` | Implemented |
| `ENV-P001` | Backend failed startup validation | ERROR | ERROR | ERROR | Fix reported reason in `.env`/profile config | `profile_guard` | Implemented |
| `ENV-P002` | Diagnostics execution failed unexpectedly | ERROR | ERROR | ERROR | Inspect backend logs and env diagnostics wiring | `profile_guard` | Implemented |

---

## 5) Traceability Matrix

| Code(s) | FR Trace | NFR Trace | Test Trace |
|---|---|---|---|
| `ENV-W001` | `ENV-UC-01`, `ENV-CN-01`, `ENV-CN-12` | `NFR-OPS-01` | `test_ENV_UC_01`, `test_ENV_CN_01` |
| `ENV-W002` | `ENV-UC-02`, `ENV-CN-02` | `NFR-OPS-02` | `test_ENV_UC_02`, `test_ENV_UC_02_E2` |
| `ENV-S001`, `ENV-D001` | `ENV-UC-02`, `ENV-CN-02`, `ENV-CN-09` | `NFR-OPS-02`, `NFR-SEC-06` | `test_ENV_UC_02_E1`, `test_ENV_CN_02` |
| `ENV-A001`, `ENV-A002` | `ENV-UC-03`, `ENV-CN-04`, `ENV-CN-09` | `NFR-SEC-04`, `NFR-SEC-06` | `test_ENV_UC_03_E1`, `test_ENV_UC_03_E2`, `test_ENV_CN_04` |
| `ENV-O001` | `ENV-UC-06`, `ENV-CN-10` | `NFR-OPS-02` | `test_ENV_UC_06_E1`, `test_ENV_CN_10` |
| `ENV-N001`, `ENV-N002` | `ENV-UC-02`, `ENV-CN-02` | `NFR-OPS-02` | `test_ENV_UC_02_E2` |
| `ENV-T001`, `ENV-T002` | `ENV-UC-06`, `ENV-CN-11` | `NFR-OPS-05` | `test_ENV_UC_06_tracing_mode_by_profile`, `test_ENV_CN_11` |
| `ENV-P001`, `ENV-P002` | `ENV-UC-02`, `ENV-CN-12` | `NFR-OPS-01`, `NFR-OPS-02` | `ST-ENV-UC-02-E1`, `ST-ENV-UC-02-E2` |

---

## 6) Governance

- `FR-12-Environment.md` is the parent requirement for this registry.
- `Task-Runner.md` references this file as output contract for startup diagnostics.
- `Testing-Index.md` references this file for diagnostic code assertions in automated/system tests.
