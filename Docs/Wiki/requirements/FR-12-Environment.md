# FR-12 Environment Profiles (ENV) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | DRAFT |
| **Date** | 2026-02-11 |
| **Domain** | ENV |
| **Applies To** | ADMIN (bootstrap/deployment), ALL (runtime behavior) |
| **Related Issues** | #30 (environment profile system), #29 (auth/registration integration), #32 (observability controls) |

---

## 1) Scope

### In Scope
- Single authoritative runtime profile (`ENVIRONMENT`) with exactly: `development`, `testing`, `production`
- Default profile behavior (`development`)
- Profile-aware startup validation and fail-fast production checks
- Profile-aware admin bootstrap behavior (`ensure_admin`)
- Profile-aware test data seeding behavior (`seed_e2e`)
- Profile-aware API documentation and debug tooling exposure
- Profile-aware OpenTelemetry behavior
- Profile-aware OAuth configuration validation
- Docker/Task runner profile passthrough and explicit environment selection

### Out of Scope
- CI pipeline policy and branch protection rules
- Certificate automation (certbot/letsencrypt) rollout
- Multi-region deployment strategy
- Service mesh and advanced traffic routing

---

## 2) Actors

| Role | Type | Notes |
|------|------|-------|
| ADMIN | System role | Owns deployment/runtime configuration decisions and bootstrap credentials |
| ALL | System-wide impact | Runtime profile affects behavior visible to every role |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| ENV-US-01 | ADMIN | As an admin I can run the system with explicit environment profiles so that development, testing, and production behavior stay predictable. |
| ENV-US-02 | ADMIN | As an admin I can fail startup in insecure production configurations so that unsafe deployments never serve traffic. |
| ENV-US-03 | ADMIN | As an admin I can bootstrap admin credentials safely in every profile so that initial access is reliable and secure. |
| ENV-US-04 | ALL | As a team member I can rely on profile-based gates for seeding, API docs, OAuth validation, and tracing so that tools are available in dev/test but locked in production. |

---

## 4) Use Cases

### ENV-UC-01 — Configure Runtime Profile

**Roles:** ALL  
**Preconditions:** Application process starts with environment variables loaded.  
**Trigger:** Runtime configuration initializes.

**Main Flow:**
1. System reads `ENVIRONMENT` from the configuration source (`env.py`).
2. If missing, system defaults to `development`.
3. System validates value is exactly one of `development`, `testing`, `production`.
4. System exposes normalized profile to dependent modules (settings, commands, task wrappers).

**Postcondition:** A single, validated runtime profile is available to all environment-dependent behavior.

**Role Coverage:**
> **ENV-UC-01-ALL**  
> - Infrastructure-level behavior; identical for all roles.

**Errors:**
**ENV-UC-01-E1** — Invalid profile value  
- Trigger: Unsupported `ENVIRONMENT` value  
- Behavior: Startup rejected with clear error showing valid values

**Tests:**
**Backend Unit:**
- test_ENV_UC_01
- test_ENV_UC_01_E1
- test_ENV_CN_01

**Backend Integration:**
- test_ENV_UC_01_runtime_profile_wiring

**System Tests (Black Box):**
- ST-ENV-UC-01
- ST-ENV-UC-01-E1

---

### ENV-UC-02 — Validate Production Configuration (Fail Fast)

**Roles:** ALL  
**Preconditions:** `ENVIRONMENT=production`.  
**Trigger:** Startup validator runs before app serves requests.

**Main Flow:**
1. System evaluates production checks in one pass.
2. System aggregates all detected violations.
3. If any violation exists, startup fails with a single consolidated error report.
4. If no violations exist, startup continues.

**Postcondition:** Production either starts securely or does not start at all.

**Role Coverage:**
> **ENV-UC-02-ALL**  
> - Infrastructure-level behavior; identical for all roles.

**Errors:**
**ENV-UC-02-E1** — Insecure production secrets/config  
- Trigger: Weak/default secret key, debug enabled, unsafe DB defaults, missing required OAuth values  
- Behavior: Startup blocked with violation list

**ENV-UC-02-E2** — Missing production hardening setting  
- Trigger: Required production safety flags absent  
- Behavior: Startup blocked with explicit missing-key report

**Tests:**
**Backend Unit:**
- test_ENV_UC_02
- test_ENV_UC_02_E1
- test_ENV_UC_02_E2
- test_ENV_CN_02
- test_ENV_CN_10

**Backend Integration:**
- test_ENV_UC_02_production_boot_guard

**System Tests (Black Box):**
- ST-ENV-UC-02
- ST-ENV-UC-02-E1
- ST-ENV-UC-02-E2

---

### ENV-UC-03 — Bootstrap Admin in All Profiles

**Roles:** ADMIN  
**Preconditions:** Admin bootstrap command available.  
**Trigger:** `ensure_admin` runs on startup or by explicit command.

**Main Flow:**
1. System checks whether a bootstrap admin already exists.
2. If present, system exits safely (idempotent).
3. If absent, system validates credentials per profile:
   a. `development` and `testing`: convenience defaults allowed.
   b. `production`: strict validation enforced (non-default, strong password).
4. System creates admin with Django admin flags.

**Postcondition:** Exactly one bootstrap admin exists; creation is idempotent and profile-safe.

**Role Coverage:**
> **ENV-UC-03-ADMIN**  
> - Admin-only operational flow.

**Errors:**
**ENV-UC-03-E1** — Production default credential rejection  
- Trigger: Placeholder/default bootstrap credentials in production  
- Behavior: Command exits with explicit rejection

**ENV-UC-03-E2** — Bootstrap password policy failure  
- Trigger: Password fails required policy  
- Behavior: Command exits with policy error details

**Tests:**
**Backend Unit:**
- test_ENV_UC_03_ADMIN
- test_ENV_UC_03_E1
- test_ENV_UC_03_E2
- test_ENV_CN_04
- test_ENV_CN_05

**Backend Integration:**
- test_ENV_UC_03_idempotent_bootstrap
- test_ENV_UC_03_profile_aware_bootstrap

**System Tests (Black Box):**
- ST-ENV-UC-03
- ST-ENV-UC-03-E1
- ST-ENV-UC-03-E2

---

### ENV-UC-04 — Control Seed Data by Profile

**Roles:** ADMIN  
**Preconditions:** Seed command exists and database reachable.  
**Trigger:** Seed operation requested.

**Main Flow:**
1. System reads active profile.
2. If `testing`, seed runs automatically for test setup.
3. If `development`, seed runs only on explicit manual command.
4. If `production`, seed is blocked.

**Postcondition:** Seed behavior follows profile policy; no accidental production seed.

**Role Coverage:**
> **ENV-UC-04-ADMIN**  
> - Admin/developer operational command flow.

**Errors:**
**ENV-UC-04-E1** — Production seed blocked  
- Trigger: Seed command invoked in production  
- Behavior: Command rejects operation with guard message

**Tests:**
**Backend Unit:**
- test_ENV_UC_04_ADMIN
- test_ENV_UC_04_E1
- test_ENV_CN_06

**Backend Integration:**
- test_ENV_UC_04_testing_auto_seed
- test_ENV_UC_04_development_manual_seed

**System Tests (Black Box):**
- ST-ENV-UC-04
- ST-ENV-UC-04-E1

---

### ENV-UC-05 — Gate API Docs and Debug Tooling by Profile

**Roles:** ALL  
**Preconditions:** URL/router configuration loads at startup.  
**Trigger:** Runtime URL map builds.

**Main Flow:**
1. System evaluates active profile.
2. If `development` or `testing`, API docs endpoints are registered.
3. If `production`, API docs endpoints are not registered.
4. Debug tooling follows profile guard policy.

**Postcondition:** API docs/debug exposure matches profile security posture.

**Role Coverage:**
> **ENV-UC-05-ALL**  
> - Infrastructure-level behavior; identical for all roles.

**Errors:**
**ENV-UC-05-E1** — Production docs/debug exposure detected  
- Trigger: Protected docs/debug route available in production  
- Behavior: Startup/config validation fails

**Tests:**
**Backend Unit:**
- test_ENV_UC_05
- test_ENV_UC_05_E1
- test_ENV_CN_07

**Backend Integration:**
- test_ENV_UC_05_route_gating_by_profile

**System Tests (Black Box):**
- ST-ENV-UC-05
- ST-ENV-UC-05-E1

---

### ENV-UC-06 — Manage Secrets and Tracing by Profile

**Roles:** ADMIN  
**Preconditions:** Secret and telemetry settings are configured.  
**Trigger:** Runtime initialization and deployment setup.

**Main Flow:**
1. System enforces production secret management policy (encrypted-at-rest workflow).
2. System validates OAuth config presence for active runtime.
3. System applies tracing mode by profile:
   a. `testing`: tracing enabled by default.
   b. `development`: tracing configurable.
   c. `production`: tracing allowed but off by default unless explicitly enabled.

**Postcondition:** Secrets, OAuth, and tracing policies are profile-correct and explicit.

**Role Coverage:**
> **ENV-UC-06-ADMIN**  
> - Admin/deployment operational flow.

**Errors:**
**ENV-UC-06-E1** — Missing required OAuth config  
- Trigger: Required OAuth env values absent  
- Behavior: startup/config validation error

**ENV-UC-06-E2** — Secret management policy violation  
- Trigger: Production secret handling not meeting policy requirements  
- Behavior: startup/deploy validation error

**Tests:**
**Backend Unit:**
- test_ENV_UC_06_ADMIN
- test_ENV_UC_06_E1
- test_ENV_UC_06_E2
- test_ENV_CN_08
- test_ENV_CN_09

**Backend Integration:**
- test_ENV_UC_06_tracing_mode_by_profile
- test_ENV_UC_06_oauth_required_validation

**System Tests (Black Box):**
- ST-ENV-UC-06
- ST-ENV-UC-06-E1
- ST-ENV-UC-06-E2

---

## 5) Constraints

### ENV-CN-01 — Single Environment Signal
- `ENVIRONMENT` is the only authoritative runtime profile selector.
- Valid values: `development`, `testing`, `production`.
- Default: `development`.
- **Applies to:** ENV-UC-01, ENV-UC-02, ENV-UC-04, ENV-UC-05, ENV-UC-06
- **Implements:** NFR-OPS-01 (Environment Profile System)

### ENV-CN-02 — Production Fail-Fast Validation
- Production startup must reject insecure or incomplete configuration before serving traffic.
- Validation output must aggregate all violations in one pass.
- **Applies to:** ENV-UC-02
- **Implements:** NFR-OPS-02 (Startup Validation)

### ENV-CN-03 — Development Workflow Preservation
- Development profile keeps fast local defaults and does not require production-hardening overrides.
- **Applies to:** ENV-UC-01, ENV-UC-03, ENV-UC-04

### ENV-CN-04 — Bootstrap Admin Password Policy
- Production bootstrap admin password must meet strict policy and denylist checks.
- Bootstrap admin creation uses Django admin flag model.
- **Applies to:** ENV-UC-03
- **Implements:** NFR-SEC-04 (Password Strength Policy) - (bootstrap admin password strength; user password policy covered in AUTH-CN-01)

### ENV-CN-05 — Idempotent Bootstrap
- `ensure_admin` must be safe to run repeatedly; no duplicate admin creation.
- **Applies to:** ENV-UC-03
- **Implements:** NFR-REL-02 (Idempotent Bootstrap Operations)

### ENV-CN-06 — Production Secret Encryption
- Production secrets must follow encrypted-at-rest handling and key separation policy.
- **Applies to:** ENV-UC-06
- **Implements:** NFR-OPS-03 (Secret Management)

### ENV-CN-07 — Deployment Guard by Profile
- Testing: auto-seed enabled.
- Development: manual seed only.
- Production: seeding blocked.
- API docs/debug tooling enabled in development/testing and blocked in production.
- **Applies to:** ENV-UC-04, ENV-UC-05
- **Implements:** NFR-OPS-04 (Deployment Guards)

### ENV-CN-08 — Session/Transport Security by Environment
- Security-sensitive cookie and transport settings must be enforced for production runtime.
- **Applies to:** ENV-UC-02
- **Implements:** NFR-SEC-05 (Session Security) - (production transport/cookie enforcement)

### ENV-CN-09 — Credential Exposure Guard
- Production startup must reject placeholder/default secrets and unsafe defaults.
- **Applies to:** ENV-UC-02, ENV-UC-03
- **Implements:** NFR-SEC-06 (Credential Exposure Prevention)

### ENV-CN-10 — OAuth Configuration Required
- OAuth configuration values are required runtime inputs and must be present for configured auth flows.
- Production validation must fail if required OAuth values are missing.
- **Applies to:** ENV-UC-02, ENV-UC-06
- **Implements:** NFR-OPS-02 (Startup Validation) - (required config completeness)

### ENV-CN-11 — Profile-Aware Tracing Policy
- Testing profile enables tracing by default.
- Development profile supports opt-in/out tracing.
- Production tracing is opt-in and defaults to disabled unless explicitly enabled.
- **Applies to:** ENV-UC-06
- **Implements:** NFR-OPS-05 (Observability Instrumentation) - (environment-controlled enablement policy)

### ENV-CN-12 — Task and Compose Profile Explicitness
- Task and compose entry points must explicitly set `ENVIRONMENT` (`development`, `testing`, or `production`) to avoid ambiguous runtime mode.
- **Applies to:** ENV-UC-01
- **Implements:** NFR-OPS-01 (Environment Profile System)

---

## 6) Behavior by Environment (Reference)

| Capability | Development | Testing | Production |
|---|---|---|---|
| `ENVIRONMENT` value | `development` (default) | `testing` | `production` |
| Startup fail-fast security checks | Relaxed | Relaxed | Strict (block on violations) |
| Admin bootstrap | Enabled | Enabled | Enabled with strict validation |
| Seed data | Manual only | Auto | Blocked |
| API docs | Enabled | Enabled | Disabled |
| Debug tooling | Enabled | Limited/allowed | Disabled |
| OAuth required config | Required by config policy | Required by config policy | Required and startup-enforced |
| Tracing default | Configurable | Enabled | Disabled (opt-in) |
| Secret management hardening | Optional local flow | Optional test flow | Required hardened flow |

---

## 7) Environment Variable Contract (`.env.template`)

This section defines the canonical environment key contract to freeze before implementation cleanup.

### Core profile keys (required)

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `ENVIRONMENT` | required | required | required | Values: `development`, `testing`, `production` |
| `DJANGO_SECRET_KEY` | required | required | required | Production must reject weak/default values |
| `DATABASE_URL` | required | required | required | Use profile-appropriate DB target |
| `DJANGO_ALLOWED_HOSTS` | required | required | required | Comma-separated |
| `DJANGO_CORS_ALLOWED_ORIGINS` | required | required | required | Comma-separated |

### OAuth keys (required by policy)

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `GOOGLE_CLIENT_ID` | required | required | required | Backend/server-side OAuth validation |
| `GOOGLE_CLIENT_SECRET` | required | required | required | Backend/server-side OAuth validation |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | required | required | required | Frontend Google SDK |
| `NEXT_PUBLIC_API_URL` | required | required | required | Frontend API base URL |

### Admin bootstrap keys

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `ADMIN_USERNAME` | required | required | required | Used by `ensure_admin` |
| `ADMIN_EMAIL` | required | required | required | Used by `ensure_admin` |
| `ADMIN_PASSWORD` | required | required | required | Production strict policy |

### Observability keys

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `OTEL_ENABLED` | optional | optional (default true in policy) | optional (default false) | Runtime tracing toggle |
| `OTEL_SERVICE_NAME` | optional | optional | optional | Service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | optional | optional | optional | Collector endpoint |
| `OTEL_EXPORTER_OTLP_HEADERS` | optional | optional | optional | Export headers |
| `OTEL_TRACE_FILE` | optional | optional | optional | Local trace export file |

### Docker/compose support keys

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `POSTGRES_DB` | required (compose) | required (compose) | required (compose) | Compose database service |
| `POSTGRES_USER` | required (compose) | required (compose) | required (compose) | Compose database service |
| `POSTGRES_PASSWORD` | required (compose) | required (compose) | required (compose) | Compose database service |

### E2E/testing keys

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `E2E_BASE_URL` | optional | optional | n/a | Playwright target |
| `E2E_API_URL` | optional | optional | n/a | Playwright API target |
| `E2E_USE_DOCKER` | optional | optional | n/a | Script toggle |

E2E identity keys (`E2E_ADMIN_*`, `E2E_TEACHER_*`, `E2E_STUDENT_*`) are supported as overrides but are not required in `.env.template`; deterministic seed defaults remain the baseline path.

### Keys to deprecate from template

- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` (use `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)
- `JWT_SECRET_KEY`, `JWT_EXPIRATION_HOURS`, `JWT_REFRESH_EXPIRATION_DAYS` (not currently used by Django settings)
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` as env keys (currently controlled by profile/settings logic, not env ingestion)

---

## 8) Test Naming Summary

Use v5 naming from `Requirements-Index.md` and `Testing-Index.md`:

- Domain aggregator: `test_ENV_UC_##`
- Role test: `test_ENV_UC_##_ADMIN` (or `_ALL` split by relevant role in implementation)
- Error test: `test_ENV_UC_##_E#`
- Constraint test: `test_ENV_CN_##`
- System tests: `ST-ENV-UC-##` and `ST-ENV-UC-##-E#`

---

## 9) Diagnostics Code Contract

Environment diagnostics are part of FR-12 acceptance behavior.

- Registry location: `../Diagnostics-Index.md`
- Current namespaces: `ENV-*` (configuration diagnostics), `ENV-P*` (profile guard/startup orchestration)
- Every diagnostics code must include:
  - profile-aware severity behavior
  - explicit fix hint
  - FR trace (UC/CN mapping)
  - NFR trace (OPS/SEC/REL mapping where applicable)
  - test trace (unit/integration/system assertion target)

Code ownership:
- `env_report` (`manage.py env_report`) owns `ENV-*` diagnostics.
- `profile_guard.py` owns `ENV-P*` diagnostics.

This contract is required so Task output, CI logs, and requirements tracing stay consistent as checks expand.
