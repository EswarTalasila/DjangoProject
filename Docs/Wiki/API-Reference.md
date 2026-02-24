# API Reference (Endpoint Index)

| Field | Value |
|-------|-------|
| **Status** | DRAFT |
| **Scope** | Canonical endpoint index for active FR domains |
| **Applies To** | FR-01 (AUTH), FR-02 (REG), FR-04 (USER) |
| **Last Updated** | 2026-02-24 |

---

## 1) Purpose

This document is the canonical endpoint index for active requirements domains.
Detailed behavior remains in per-domain FR docs; this page consolidates endpoint shape, auth, state model, and traceability in one place.

Primary sources:
- `requirements/FR-01-Auth.md`
- `requirements/FR-02-Registration.md`
- `requirements/FR-04-User.md`

---

## 2) API Style Standard

### Path and Versioning
- Version prefix is required: `/api/v1/...`
- Resource nouns only (plural where applicable): `/codes`, `/password-reset-codes`

### Method Semantics
- `POST` creates resources or performs non-resource/session workflows
- `GET` retrieves resources
- `PATCH` applies partial updates, including workflow/state transitions on existing resources

### State-Driven Transition Rule
- Lifecycle/workflow transitions are performed via `PATCH /resource/{id}` with a target `status` in payload
- Client-settable statuses must be explicitly constrained per resource
- Server-derived statuses must not be client-settable

Example:
- `PATCH /api/v1/codes/{id}` with `{ "status": "REVOKED" }`

### Auth Convention
- `None` means unauthenticated endpoint
- `Access token` means authenticated user endpoint
- `Refresh token` is only for refresh workflow
- `Issuer` means authenticated user passing role/scope checks for reset-code issuance

### Error Convention (Draft)
- Errors should map to UC error IDs where defined (e.g., `AUTH-UC-05-E1`)
- Use consistent JSON envelope across domains (`code`, `message`, optional `details`)

---

## 3) Endpoint Index (AUTH + REG + USER)

| Domain | UC | Method | Path | Auth | Roles | State Model | Request (summary) | Error IDs | Constraints | Tests | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AUTH | AUTH-UC-01 | POST | `/api/v1/auth/sessions` | None | ALL | N/A | identifier + password | AUTH-UC-01-E1/E2/E3 | AUTH-CN-01, AUTH-CN-03, AUTH-CN-04, AUTH-CN-12 | `test_AUTH_UC_01_*` | Proposed |
| AUTH | AUTH-UC-02 | POST | `/api/v1/auth/sessions/oauth` | None | ALL | N/A | oauth token/authorization callback payload | AUTH-UC-02-E1/E2 | AUTH-CN-04 | `test_AUTH_UC_02_*` | Proposed |
| AUTH | AUTH-UC-03 | POST | `/api/v1/auth/token-exchanges` | Refresh token | ALL | N/A | refresh token | (standard auth error) | AUTH-CN-02 | `test_AUTH_UC_03_*` | Proposed |
| AUTH | AUTH-UC-08 | POST | `/api/v1/auth/session-revocations` | Access token | ALL | N/A | refresh token | (none) | AUTH-CN-11 | `test_AUTH_UC_08_*` | Proposed |
| AUTH | AUTH-UC-04 | PATCH | `/api/v1/auth/password` | Access token | ALL | N/A | current password + new password + confirm | AUTH-UC-04-E1/E2 | AUTH-CN-01, AUTH-CN-11 | `test_AUTH_UC_04_*` | Proposed |
| AUTH | AUTH-UC-07 | POST | `/api/v1/auth/password-reset-codes` | Issuer | ADMIN, RESEARCHER, TEACHER | Issuer-generated reset code profile | targetUserId | AUTH-UC-07-E1/E2 | AUTH-CN-05, AUTH-CN-06, AUTH-CN-10 | `test_AUTH_UC_07_*` | Proposed |
| AUTH | AUTH-UC-05 | POST | `/api/v1/auth/reset-code-validations` | None | RESEARCHER, TEACHER, STUDENT | N/A | identifier + reset code | AUTH-UC-05-E1 | AUTH-CN-07 | `test_AUTH_UC_05_*` | Proposed |
| AUTH | AUTH-UC-05 | POST | `/api/v1/auth/password-resets` | None | RESEARCHER, TEACHER, STUDENT | Consumes reset code | identifier + reset code + new password + confirm | AUTH-UC-05-E2 | AUTH-CN-01, AUTH-CN-07, AUTH-CN-11 | `test_AUTH_UC_05_*` | Proposed |
| REG | REG-UC-01 | POST | `/api/v1/registration/code-validations` | None | RESEARCHER, TEACHER, STUDENT | N/A | access code | REG-UC-01-E1 | REG-CN-01, REG-CN-02, REG-CN-22 | `test_REG_UC_01_*` | Proposed |
| REG | REG-UC-01 | POST | `/api/v1/registration/accounts` | None | RESEARCHER, TEACHER, STUDENT | N/A | method (LOCAL) + code + firstName + lastName + password + confirmPassword (+ email for non-student flows) | REG-UC-01-E2/E3 | REG-CN-03, REG-CN-13, REG-CN-22 | `test_REG_UC_01_*` | Proposed |
| REG | REG-UC-01 | POST | `/api/v1/registration/accounts` | None | RESEARCHER, TEACHER | N/A | method (OAUTH) + code + accessToken + firstName + lastName | REG-UC-01-E4 | REG-CN-03, REG-CN-13, REG-CN-22 | `test_REG_UC_01_*` | Proposed |
| REG | REG-UC-02 | POST | `/api/v1/codes` | Access token | ADMIN, RESEARCHER, TEACHER | Creates ACTIVE codes | count + uses_per_code + expires_at + target role (+ optional metadata/course) | REG-UC-02-E1/E2/E3/E4/E5 | REG-CN-06, REG-CN-07, REG-CN-11, REG-CN-12, REG-CN-22 | `test_REG_UC_02_*` | Proposed |
| REG | REG-UC-03 | GET | `/api/v1/codes` | Access token | ADMIN, RESEARCHER, TEACHER | List | filters/pagination (draft) | REG-UC-03-E1 | REG-CN-04, REG-CN-05, REG-CN-22 | `test_REG_UC_03_*` | Proposed |
| REG | REG-UC-03 | GET | `/api/v1/codes/{id}` | Access token | ADMIN, RESEARCHER, TEACHER | Detail | none | REG-UC-03-E1 | REG-CN-04, REG-CN-22 | `test_REG_UC_03_*` | Proposed |
| REG | REG-UC-03 | PATCH | `/api/v1/codes/{id}` | Access token | ADMIN, RESEARCHER, TEACHER | `ACTIVE -> REVOKED`; `REVOKED|EXPIRED|EXHAUSTED -> ARCHIVED` | status + optional reason | REG-UC-03-E1/E2 | REG-CN-05, REG-CN-15, REG-CN-22 | `test_REG_UC_03_*` | Proposed |
| USER | USER-UC-01 | POST | `/api/v1/users` | Access token | ADMIN, RESEARCHER, TEACHER | Creates user + role + profile | name + optional role/password/email (username rejected) | USER-UC-01-E1/E2/E3/E4/E5 | USER-CN-01, USER-CN-02, USER-CN-03, USER-CN-06, USER-CN-07 | `test_USER_UC_01_*` | Proposed |
| USER | USER-UC-02 | PATCH | `/api/v1/users/{user_id}` | Access token | ADMIN, RESEARCHER, TEACHER | Updates user fields + optional role transition | name/email/password/role (username immutable) | USER-UC-02-E1/E2/E3/E4/E5 | USER-CN-01, USER-CN-02, USER-CN-03, USER-CN-04, USER-CN-05, USER-CN-06, USER-CN-08 | `test_USER_UC_02_*` | Proposed |
| USER | USER-UC-03 | DELETE | `/api/v1/users/{user_id}` | Access token | ADMIN, RESEARCHER, TEACHER | Deletes user by ID | none | USER-UC-03-E1/E2 | USER-CN-01, USER-CN-05, USER-CN-08 | `test_USER_UC_03_*` | Proposed |
| USER | USER-UC-04 | GET | `/api/v1/users/staff` | Access token | ADMIN, RESEARCHER | Paginated staff directory (teachers/researchers) | filters/pagination | USER-UC-04-E1 | USER-CN-09 | `test_USER_UC_04_*` | Proposed |

---

## 4) State Transition Constraints

### Reset Codes (`AUTH-UC-07`)
- Issuer-generated only (no request queue/status state machine)
- Code profile is fixed and system-enforced:
  - single-use
  - target-bound
  - 30-minute expiry
- New issuance for the same target invalidates prior active reset code

### Registration Codes (`REG-UC-03`)
- Allowed client transitions:
  - `ACTIVE -> REVOKED`
  - `REVOKED|EXPIRED|EXHAUSTED -> ARCHIVED`
- Server-derived only (not client-settable):
  - `EXPIRED`
  - `EXHAUSTED`

Example payloads:
```json
{ "status": "REVOKED", "reason": "manual_stop" }
```
```json
{ "status": "ARCHIVED" }
```

---

## 5) Traceability and Source of Truth

- Requirement source for AUTH endpoints:
  - `requirements/FR-01-Auth.md`
- Requirement source for REG endpoints:
  - `requirements/FR-02-Registration.md`
- Requirement source for USER endpoints:
  - `requirements/FR-04-User.md`
- Testing policy and naming:
  - `Testing-Index.md`
- Cross-cutting API policy:
  - `nfr/NFR-Reliability.md` (REST + error-format constraints)

When endpoint definitions conflict, update FR docs first, then synchronize this index.

---

## 6) Changelog

### 2026-02-13
- REG registration codes now use hash-at-rest persistence. Plaintext invite codes are returned only at `POST /api/v1/codes` creation time.
- `GET /api/v1/codes` and `GET /api/v1/codes/{id}` expose `codePrefix` and do not expose plaintext `code`.
- Endpoint constraints for all REG code-related routes now include `REG-CN-22` (Registration Code Hash-At-Rest).
- `POST /api/v1/registration/accounts` now supports non-student local registration for invite flows (requires `email`; username is system-generated).
- `POST /api/v1/codes` now persists optional `metadata` for teacher-code generation (researcher flow), with `count=1` enforcement.

### 2026-02-14
- **Endpoint Standardization v1 (FR-01/FR-02/FR-03):** Renamed verb-based paths to noun-based resource paths.
- AUTH: `login` → `sessions`, `oauth/google` → `sessions/oauth`, `refresh` → `token-exchanges`, `logout` → `session-revocations`, `password/change` → `password` (PATCH), `reset-codes/verify` → `reset-code-validations`, `reset-codes/complete` → `password-resets`.
- REG: `validate-code` → `code-validations`, `local`/`oauth` merged into `accounts` (dispatched by `method` field: LOCAL or OAUTH), `student/join-course` → top-level `/enrollments`.
- SUDO routes moved to top-level resources (`/sudo-grants`).
- User delete switched from username-based to ID-based: `DELETE /users/{user_id}`.
- ID-based CRUD for resources; token/body-based for sensitive reset workflows.

### 2026-02-19
- AUTH reset contract updated to issuer-based flow:
  - Added `POST /api/v1/auth/password-reset-codes`
  - Retired reset-request and status-lookup queue from active index
  - Kept `POST /api/v1/auth/reset-code-validations` and `POST /api/v1/auth/password-resets` for code consumption

### 2026-02-24
- Added FR-04 USER endpoint index entries:
  - `POST /api/v1/users`
  - `PATCH /api/v1/users/{user_id}`
  - `DELETE /api/v1/users/{user_id}`
  - `GET /api/v1/users/staff`
- Removed `POST /api/v1/user-batches` from active contract and backend routes; registration code flows (FR-02) are the supported bulk onboarding path.
- Updated active scope from AUTH+REG to AUTH+REG+USER.
