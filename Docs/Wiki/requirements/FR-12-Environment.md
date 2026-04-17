# FR-12 Environment Profiles (ENV) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | ENV |
| **Applies To** | ADMIN (bootstrap/deployment), ALL (runtime behavior) |
| **Related Issues** | #30 (environment profile system), #29 (auth/registration integration) |
| **Dependencies** | FR-13 INFRA (Docker Compose and Taskfile pass `ENVIRONMENT` to backend service) |

---

## 1) Scope

### In Scope
- Single authoritative runtime profile (`ENVIRONMENT`) with exactly: `development`, `testing`, `production`
- Default profile behavior (`development`)
- Profile-aware startup validation and fail-fast production checks
- Profile-aware admin bootstrap behavior (`ensure_admin`)
- Profile-aware API documentation and debug tooling exposure
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
| ENV-US-04 | ALL | As a team member I can rely on profile-based gates for API docs and OAuth validation so that tools are available in dev/test but locked in production. |

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
- test_ENV_UC_01_accepts_valid_profiles
- test_ENV_UC_01_default_profile_is_development
- test_ENV_UC_01_E1_rejects_invalid_profile
- test_ENV_CN_01_environment_controls_profile_properties

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
- test_ENV_UC_02_dev_testing_skip_validation
- test_ENV_UC_02_production_passes_with_valid_config
- test_ENV_UC_02_E1_debug_enabled
- test_ENV_UC_02_E1_weak_secret_key
- test_ENV_UC_02_E2_aggregates_all_violations
- test_ENV_CN_02_all_violations_aggregated_in_one_pass
- test_ENV_CN_10_missing_client_id_blocks_production

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
- test_ENV_UC_03_ADMIN_creates_admin_with_django_flags
- test_ENV_UC_03_E1_production_default_credentials_rejected
- test_ENV_UC_03_E2_password_policy_failure
- test_ENV_CN_04_production_password_denylist
- test_ENV_CN_05_idempotent_ensure_admin

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
- test_ENV_UC_04_ADMIN_seed_runs_in_dev
- test_ENV_UC_04_E1_production_seed_blocked
- test_ENV_CN_06_weak_secret_blocked_in_production

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
- test_ENV_UC_05_api_docs_enabled_in_development
- test_ENV_UC_05_debug_toolbar_only_in_development
- test_ENV_UC_05_E1_api_docs_disabled_in_production
- test_ENV_CN_07_seed_production_blocked

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
- test_ENV_UC_06_E1_missing_oauth_blocks_production
- test_ENV_CN_08_production_session_security
- test_ENV_CN_09_default_admin_email_blocked

**Backend Integration:**
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

## 6) Infrastructure Contract

### 6.1 Behavior by Environment (Reference)

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

### 6.2 Environment Variable Contract (`.env.template`)

This section defines the canonical environment key contract to freeze before implementation cleanup.

#### Core profile keys (required)

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `ENVIRONMENT` | required | required | required | Values: `development`, `testing`, `production` |
| `DJANGO_SECRET_KEY` | required | required | required | Production must reject weak/default values |
| `DATABASE_URL` | required | required | required | Use profile-appropriate DB target |
| `DJANGO_ALLOWED_HOSTS` | required | required | required | Comma-separated |
| `DJANGO_CORS_ALLOWED_ORIGINS` | required | required | required | Comma-separated |

#### OAuth keys (required by policy)

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `GOOGLE_CLIENT_ID` | required | required | required | Backend/server-side OAuth validation |
| `GOOGLE_CLIENT_SECRET` | required | required | required | Backend/server-side OAuth validation |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | required | required | required | Frontend Google SDK |
| `NEXT_PUBLIC_API_URL` | required | required | required | Frontend API base URL |

#### Admin bootstrap keys

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `ADMIN_USERNAME` | required | required | required | Used by `ensure_admin` |
| `ADMIN_EMAIL` | required | required | required | Used by `ensure_admin` |
| `ADMIN_PASSWORD` | required | required | required | Production strict policy |

#### Docker/compose support keys

| Key | development | testing | production | Notes |
|---|---|---|---|---|
| `POSTGRES_DB` | required (compose) | required (compose) | required (compose) | Compose database service |
| `POSTGRES_USER` | required (compose) | required (compose) | required (compose) | Compose database service |
| `POSTGRES_PASSWORD` | required (compose) | required (compose) | required (compose) | Compose database service |

#### Keys to deprecate from template

- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` (use `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)
- `JWT_SECRET_KEY`, `JWT_EXPIRATION_HOURS`, `JWT_REFRESH_EXPIRATION_DAYS` (not currently used by Django settings)
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` as env keys (currently controlled by profile/settings logic, not env ingestion)

### 6.3 Diagnostics Code Contract

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
- `_check:env:<profile>` and `check-env.sh` own `ENV-P*` diagnostics.

This contract is required so Task output, CI logs, and requirements tracing stay consistent as checks expand.

---

## 7) Error Model

ENV errors are configuration-level. They manifest as startup failures or command rejections, not HTTP error responses to end users.

| Scenario | Behavior | Source |
|----------|----------|--------|
| Invalid `ENVIRONMENT` value | Startup rejected; valid values listed in error | ENV-UC-01-E1 |
| Weak/default secret key, debug enabled, unsafe DB defaults | Startup blocked with consolidated violation list | ENV-UC-02-E1 |
| Required production safety flags absent | Startup blocked with explicit missing-key report | ENV-UC-02-E2 |
| Placeholder/default bootstrap credentials in production | `ensure_admin` exits with explicit rejection | ENV-UC-03-E1 |
| Bootstrap password fails policy (length, denylist) | `ensure_admin` exits with policy error details | ENV-UC-03-E2 |
| Seed command invoked in production | Command rejects operation with guard message | ENV-UC-04-E1 |
| Protected docs/debug route available in production | Startup/config validation fails | ENV-UC-05-E1 |
| Required OAuth env values absent | Startup/config validation error | ENV-UC-06-E1 |
| Production secret handling not meeting policy | Startup/deploy validation error | ENV-UC-06-E2 |

All ENV errors are deterministic configuration violations detected before the application serves traffic. No ENV error is transient or retryable — resolution requires changing the environment configuration.

---

## 8) Test Strategy by Layer

### Naming Convention

Use v5 naming from `Requirements-Index.md` and `Testing-Index.md`:

- Domain aggregator: `test_ENV_UC_nn`
- Role test: `test_ENV_UC_nn_ADMIN` (or `_ALL` split by relevant role in implementation)
- Error test: `test_ENV_UC_nn_En`
- Constraint test: `test_ENV_CN_nn`
- System tests: `ST-ENV-UC-##` and `ST-ENV-UC-##-E#`

### Backend Unit

- Profile configuration: `ENVIRONMENT` enum validation, default fallback to `development`, rejection of invalid values (ENV-UC-01).
- Production fail-fast: aggregated violation detection for weak secrets, debug mode, unsafe DB defaults, missing OAuth values (ENV-UC-02).
- Bootstrap admin: idempotent creation, profile-aware credential validation, password policy enforcement, denylist checks (ENV-UC-03).
- Seed guards: profile-based seed gating — testing auto, development manual, production blocked (ENV-UC-04).
- Route gating: API docs/debug endpoint registration by profile (ENV-UC-05).
- Secret/tracing policy: OAuth config presence validation, profile-aware tracing defaults (ENV-UC-06).
- Constraint coverage: all 12 constraints (ENV-CN-01 through ENV-CN-12) have dedicated unit tests.

### Backend Integration

- Runtime profile wiring: settings, commands, and task wrappers consume the validated profile consistently.
- Production boot guard: startup sequence rejects insecure configurations end-to-end.
- Idempotent bootstrap: repeated `ensure_admin` invocations produce no side effects.
- Profile-aware bootstrap: credential validation differs correctly across profiles.
- Route gating by profile: URL map includes/excludes docs endpoints based on active profile.
- OAuth validation: required OAuth env values checked at startup in production.

### System Tests (Black Box)

- ST-ENV-UC-01 through ST-ENV-UC-06 and their error variants (ST-ENV-UC-01-E1, ST-ENV-UC-02-E1, ST-ENV-UC-02-E2, ST-ENV-UC-03-E1, ST-ENV-UC-03-E2, ST-ENV-UC-04-E1, ST-ENV-UC-05-E1, ST-ENV-UC-06-E1, ST-ENV-UC-06-E2).

---

## 9) NFR Cross-References

- **NFR-OPS-01** (Environment Profile System)
  - `ENVIRONMENT` as single authoritative runtime profile selector (ENV-CN-01).
  - Task/compose entry points explicitly set profile (ENV-CN-12).
- **NFR-OPS-02** (Startup Validation)
  - Production fail-fast rejects insecure/incomplete configuration before serving traffic (ENV-CN-02).
  - OAuth config completeness enforced at startup (ENV-CN-10).
- **NFR-OPS-03** (Secret Management)
  - Production secrets follow encrypted-at-rest handling and key separation policy (ENV-CN-06).
- **NFR-OPS-04** (Deployment Guards)
  - Seed data and API docs/debug tooling gated by profile (ENV-CN-07).
- **NFR-SEC-04** (Password Strength Policy)
  - Bootstrap admin password meets strict policy and denylist in production (ENV-CN-04).
- **NFR-SEC-05** (Session Security)
  - Production cookie and transport settings enforced (ENV-CN-08).
- **NFR-SEC-06** (Credential Exposure Prevention)
  - Production startup rejects placeholder/default secrets and unsafe defaults (ENV-CN-09).
- **NFR-REL-02** (Idempotent Bootstrap Operations)
  - `ensure_admin` safe for repeated execution; no duplicate admin creation (ENV-CN-05).

---

## 10) Cross-Domain References

| FR | Reference | Notes |
|----|-----------|-------|
| FR-01 AUTH | OAuth config validation at startup | Production startup enforces presence of `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` for configured auth flows (ENV-UC-02, ENV-UC-06, ENV-CN-10). |
| FR-13 INFRA | Docker Compose and Taskfile `ENVIRONMENT` passthrough | FR-13 owns `docker-compose.yml` and `Taskfile.yml`; must explicitly set `ENVIRONMENT` per ENV-CN-12. Backend service environment block must include `ENVIRONMENT` variable. |

---

## 11) Current Implementation Alignment Notes

All FR-12 items are implemented. Final state as of 2026-03-03:

1. **`ENVIRONMENT` field in `config/env.py`.** DONE. `Literal["development", "testing", "production"]` with default `"development"`. Profile convenience properties (`is_development`, `is_testing`, `is_production`) derive from this single field (ENV-CN-01).
2. **Production startup validation (aggregated).** DONE. `@model_validator` `validate_runtime_contract` collects all violations in one pass (ENV-CN-02) and raises a single consolidated error. Checks: debug override, secret key, admin bootstrap, allowed hosts, CORS, database URL, and OAuth.
3. **`ensure_admin` profile-aware validation.** DONE. Reads `env.is_production`; rejects default/placeholder emails, enforces 12+ char password with denylist, validates email format, calls Django `validate_password` (ENV-CN-04, ENV-CN-05, ENV-CN-09).
4. **API docs gated by profile.** DONE. `config/urls.py` registers Swagger/ReDoc/schema only when `settings.ENVIRONMENT != "production"` (ENV-UC-05).
5. **Diagnostics.** DONE. `env_report` management command remains operational.
6. **`.env.template` cleanup.** DONE. Template aligned with section 6.2 contract; legacy keys (`GOOGLE_OAUTH_*`, `JWT_*`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`) removed.

### Deferred / Out of FR-12 Scope
- **ENV-CN-12 Taskfile/Compose passthrough**: `docker-compose.yml` and `Taskfile.yml` already set `ENVIRONMENT` explicitly. FR-13 INFRA owns further deployment template changes.
- **System tests (ST-ENV-*)**: Black-box system tests require a running Docker stack and remain separate from the current unit/integration harness.
