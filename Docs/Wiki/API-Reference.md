# API Reference (Endpoint Index)

| Field | Value |
|-------|-------|
| **Status** | DRAFT |
| **Scope** | Canonical endpoint index for active FR domains |
| **Applies To** | FR-01 (AUTH), FR-02 (REG) |
| **Last Updated** | 2026-02-11 |

---

## 1) Purpose

This document is the canonical endpoint index for active requirements domains.
Detailed behavior remains in per-domain FR docs; this page consolidates endpoint shape, auth, state model, and traceability in one place.

Primary sources:
- `requirements/FR-01-Auth.md`
- `requirements/FR-02-Registration.md`

---

## 2) API Style Standard

### Path and Versioning
- Version prefix is required: `/api/v1/...`
- Resource nouns only (plural where applicable): `/codes`, `/reset-requests`

### Method Semantics
- `POST` creates resources or performs non-resource/session workflows
- `GET` retrieves resources
- `PATCH` applies partial updates, including workflow/state transitions on existing resources

### State-Driven Transition Rule
- Lifecycle/workflow transitions are performed via `PATCH /resource/{id}` with a target `status` in payload
- Client-settable statuses must be explicitly constrained per resource
- Server-derived statuses must not be client-settable

Examples:
- `PATCH /api/v1/codes/{id}` with `{ "status": "REVOKED" }`
- `PATCH /api/v1/auth/reset-requests/{id}` with `{ "status": "APPROVED" }`

### Auth Convention
- `None` means unauthenticated endpoint
- `Access token` means authenticated user endpoint
- `Refresh token` is only for refresh workflow
- `Approver` means authenticated user passing role/scope checks for approval chain

### Error Convention (Draft)
- Errors should map to UC error IDs where defined (e.g., `AUTH-UC-05-E1`)
- Use consistent JSON envelope across domains (`code`, `message`, optional `details`)

---

## 3) Endpoint Index (AUTH + REG)

| Domain | UC | Method | Path | Auth | Roles | State Model | Request (summary) | Error IDs | Constraints | Tests | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AUTH | AUTH-UC-01 | POST | `/api/v1/auth/login` | None | ALL | N/A | email + password | AUTH-UC-01-E1/E2/E3 | AUTH-CN-01, AUTH-CN-03, AUTH-CN-04 | `test_AUTH_UC_01_*` | Proposed |
| AUTH | AUTH-UC-02 | POST | `/api/v1/auth/oauth/google` | None | ALL | N/A | oauth token/authorization callback payload | AUTH-UC-02-E1/E2 | AUTH-CN-04 | `test_AUTH_UC_02_*` | Proposed |
| AUTH | AUTH-UC-03 | POST | `/api/v1/auth/refresh` | Refresh token | ALL | N/A | refresh token | (standard auth error) | AUTH-CN-02 | `test_AUTH_UC_03_*` | Proposed |
| AUTH | AUTH-UC-08 | POST | `/api/v1/auth/logout` | Access token | ALL | N/A | none | (none) | AUTH-CN-11 | `test_AUTH_UC_08_*` | Proposed |
| AUTH | AUTH-UC-04 | POST | `/api/v1/auth/password/change` | Access token | ALL | N/A | current password + new password + confirm | AUTH-UC-04-E1/E2 | AUTH-CN-01, AUTH-CN-11 | `test_AUTH_UC_04_*` | Proposed |
| AUTH | AUTH-UC-05 | POST | `/api/v1/auth/reset-requests` | None | RESEARCHER, TEACHER, STUDENT | Creates `PENDING` request | requester identity fields | AUTH-UC-05-E1/E2/E3 | AUTH-CN-06, AUTH-CN-10 | `test_AUTH_UC_05_*` | Proposed |
| AUTH | AUTH-UC-06 | POST | `/api/v1/auth/reset-requests/status` | None | RESEARCHER, TEACHER, STUDENT | Reads request status | email + request token | AUTH-UC-06-E1/E2 | AUTH-CN-10 | `test_AUTH_UC_06_*` | Proposed |
| AUTH | AUTH-UC-07 | PATCH | `/api/v1/auth/reset-requests/{id}` | Approver | ADMIN, RESEARCHER, TEACHER | `PENDING -> APPROVED|DENIED` | status + optional expires_at/reason | AUTH-UC-07-E1 | AUTH-CN-06 | `test_AUTH_UC_07_*` | Proposed |
| AUTH | AUTH-UC-05 | POST | `/api/v1/auth/reset-codes/verify` | None | RESEARCHER, TEACHER, STUDENT | N/A | reset code + requester fields | AUTH-UC-05-E4 | AUTH-CN-07 | `test_AUTH_UC_05_*` | Proposed |
| AUTH | AUTH-UC-05 | POST | `/api/v1/auth/reset-codes/complete` | None | RESEARCHER, TEACHER, STUDENT | Consumes reset code | reset code + new password + confirm | AUTH-UC-05-E5 | AUTH-CN-07, AUTH-CN-11 | `test_AUTH_UC_05_*` | Proposed |
| REG | REG-UC-01 | POST | `/api/v1/registration/validate-code` | None | RESEARCHER, TEACHER, STUDENT | N/A | access code | REG-UC-01-E1 | REG-CN-01, REG-CN-02 | `test_REG_UC_01_*` | Proposed |
| REG | REG-UC-01 | POST | `/api/v1/registration/local` | None | RESEARCHER, TEACHER, STUDENT | N/A | code + name + email + password | REG-UC-01-E2/E3 | REG-CN-03, REG-CN-13 | `test_REG_UC_01_*` | Proposed |
| REG | REG-UC-01 | POST | `/api/v1/registration/oauth` | None | RESEARCHER, TEACHER, STUDENT | N/A | code + oauth payload + in-app name | REG-UC-01-E4 | REG-CN-03, REG-CN-13 | `test_REG_UC_01_*` | Proposed |
| REG | REG-UC-02 | POST | `/api/v1/codes` | Access token | ADMIN, RESEARCHER, TEACHER | Creates ACTIVE codes | count + uses_per_code + expires_at + target role (+ optional metadata/course) | REG-UC-02-E1/E2/E3/E4/E5 | REG-CN-06, REG-CN-07, REG-CN-11, REG-CN-12 | `test_REG_UC_02_*` | Proposed |
| REG | REG-UC-03 | GET | `/api/v1/codes` | Access token | ADMIN, RESEARCHER, TEACHER | List | filters/pagination (draft) | REG-UC-03-E1 | REG-CN-04, REG-CN-05 | `test_REG_UC_03_*` | Proposed |
| REG | REG-UC-03 | GET | `/api/v1/codes/{id}` | Access token | ADMIN, RESEARCHER, TEACHER | Detail | none | REG-UC-03-E1 | REG-CN-04 | `test_REG_UC_03_*` | Proposed |
| REG | REG-UC-03 | PATCH | `/api/v1/codes/{id}` | Access token | ADMIN, RESEARCHER, TEACHER | `ACTIVE -> REVOKED`; `REVOKED|EXPIRED|EXHAUSTED -> ARCHIVED` | status + optional reason | REG-UC-03-E1/E2 | REG-CN-05, REG-CN-15 | `test_REG_UC_03_*` | Proposed |

---

## 4) State Transition Constraints

### Reset Requests (`AUTH-UC-07`)
- Allowed client transitions:
  - `PENDING -> APPROVED`
  - `PENDING -> DENIED`
- Disallowed:
  - Any transition from `APPROVED`, `DENIED`, or `EXPIRED`
- Role/expiry rules:
  - Teacher approving student request: fixed 30-minute reset code expiry (no picker)
  - Researcher/Admin approvals: optional `expires_at`; default 30 minutes

Example payloads:
```json
{ "status": "APPROVED", "expires_at": "2026-02-12T14:30:00Z" }
```
```json
{ "status": "DENIED", "reason": "request_not_verified" }
```

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
- Testing policy and naming:
  - `Testing-Index.md`
- Cross-cutting API policy:
  - `nfr/NFR-Reliability.md` (REST + error-format constraints)

When endpoint definitions conflict, update FR docs first, then synchronize this index.
