# Diagnostics -- Index

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Scope** | Generated env validation output and runtime security diagnostics |
| **Applies To** | `task env:init`, `_check:env:*`, `task up:*` |
| **Related FRs** | FR-12, FR-13 |

---

## 1) Purpose

Define the diagnostics emitted by the rebuilt env validation flow:

- env generation from root `.env`
- profile-specific validation via `scripts/tasks/check-env.sh`
- backend runtime environment checks where still applicable

This file is the lookup contract for:

- code meaning
- profile severity
- fix hints
- task/startup traceability

---

## 2) Namespace Rules

| Prefix | Meaning | Primary Source |
|---|---|---|
| `ENV-*` | Generated env validation diagnostics | `check-env.sh`, `env_tools.py`, `env_report.py` |
| `SVC-*` | Service dependency diagnostics (reserved) | Task/runtime orchestration |
| `SEC-*` | Security posture diagnostics (reserved) | Runtime security checks |

---

## 3) Severity Model by Profile

| Rule | development | testing | production |
|---|---|---|---|
| Placeholder/default checks | WARN | WARN | ERROR |
| Topology derivation drift | WARN | WARN | ERROR |
| Security criteria failures | WARN | WARN | ERROR |

Notes:

- Production startup must fail when any `ERROR` code is emitted.
- Development/testing warnings are actionable but non-blocking.

---

## 4) Code Registry

| Code | Trigger (short) | Dev | Test | Prod | Hint (short) | Source |
|---|---|---|---|---|---|---|
| `ENV-DERIVE` | Generated profile env drifted from derived topology values | WARN | WARN | ERROR | Rerun `task env:init` after fixing root `.env` | `check-env.sh` |
| `ENV-DEFAULT` | Dev/test profile is still using policy-defined weak defaults | WARN | WARN | N/A | Replace root `.env` value only if you need a stronger local override | `check-env.sh` |
| `ENV-PLACEHOLDER` | Production value still matches a placeholder token | N/A | N/A | ERROR | Set a real value in root `.env` and rerun `task env:init` | `check-env.sh` |
| `ENV-WEAK` | Production value fails minimum-strength rules | N/A | N/A | ERROR | Replace with a stronger value in root `.env` | `check-env.sh` |
| `ENV-EMAIL` | Production email field is malformed | N/A | N/A | ERROR | Set a valid email address in root `.env` | `check-env.sh` |
| `ENV-HOSTS` | Production allowed hosts include localhost or internal aliases | N/A | N/A | ERROR | Set only the public hostname via root `.env` target values | `check-env.sh` |
| `ENV-ORIGINS` | Production CORS/CSRF origins include localhost or wildcard values | N/A | N/A | ERROR | Derive exact public origins from the server target and rerun `task env:init` | `check-env.sh` |

---

## 5) Traceability Notes

- `Task-Runner.md` references this file as the env validation output contract.
- `task up:*` runs env validation before attempting startup.
- `task env:init` materializes the generated env files that this validation checks.
