# FR-02 Registration (REG) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-10 |
| **Domain** | REG |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER, STUDENT |
| **Related Issues** | #29 (code-gated auth/registration), #28 (role hierarchy/sudo) |

---

## 1) Scope

### In Scope
- Code-gated registration for RESEARCHER, TEACHER, STUDENT
- Local registration (email + password + name)
- OAuth registration (Google) with in-app name capture
- Access code validation (status, expiry, uses remaining)
- Code generation (count + uses per code, expiration, optional metadata)
- Code lifecycle management (list, detail, state transitions, archive visibility)
- Student auto-enrollment when registering with a teacher-issued code

### Out of Scope
- Self-registration without an access code
- Admin self-registration (bootstrapped via environment)
- Email-based invites or SMTP workflows
- Account disabling as a side-effect of code revocation

---

## 2) Actors

| Role | Type | Notes |
|------|------|-------|
| ADMIN | System role | `is_staff=True`; can generate researcher codes and view all codes |
| RESEARCHER | User role | Can generate teacher codes; can view own codes; sudo expands scope |
| TEACHER | User role | Can generate student codes; must link to a course |
| STUDENT | User role | Can self-register with a valid student code |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| REG-US-01 | RESEARCHER, TEACHER, STUDENT | As a researcher, teacher, or student I can register using an access code so that I can access the system. |
| REG-US-02 | ADMIN, RESEARCHER, TEACHER | As an admin, researcher, or teacher I can generate access codes with a count, uses-per-code, and expiration so that new users can register. |

---

## 4) Use Cases

### REG-UC-01 — Code-Gated Registration

**Roles:** RESEARCHER, TEACHER, STUDENT

**Preconditions:** User possesses a valid access code that matches their target role.

**Trigger:** User enters access code on registration page.

**Main Flow:**
1. User enters access code.
2. System validates code (active, not expired, uses remaining).
3. System determines role and any linked course (student codes).
4. User selects registration method: Local or OAuth.
5. Local: user enters name, email, password; system validates and creates account.
6. OAuth: user completes provider flow; system collects display name in-app.
7. System links user to code, decrements uses, and sets code status if exhausted.
8. If student code: auto-enroll user in linked course.
9. User is logged in and redirected to dashboard.

**Postcondition:** Account created; code usage recorded; student auto-enrolled if applicable.

**Role Coverage:**

> **REG-UC-01-RESEARCHER**
> - Researcher self-registration with a researcher code

> **REG-UC-01-TEACHER**
> - Teacher self-registration with a teacher code

> **REG-UC-01-STUDENT**
> - Student self-registration with a teacher-issued student code

**Errors:**

**REG-UC-01-E1** — Access code error
- Trigger: Invalid, expired, exhausted, or revoked code
- Behavior: Generic error; do not reveal code state beyond invalid

**REG-UC-01-E2** — Registration errors
- Trigger: Weak password, password mismatch, email already in use
- Behavior: Field-level validation errors

**REG-UC-01-E3** — Missing required fields
- Trigger: Missing name/email/password in local registration
- Behavior: Required field errors

**REG-UC-01-E4** — OAuth registration error
- Trigger: OAuth cancelled/failed or missing email
- Behavior: OAuth error message; return to registration choice

**Tests:**

**Backend Unit:**
- test_REG_UC_01 (aggregator)
- test_REG_UC_01_RESEARCHER
- test_REG_UC_01_TEACHER
- test_REG_UC_01_STUDENT
- test_REG_UC_01_E1
- test_REG_UC_01_E2
- test_REG_UC_01_E3
- test_REG_UC_01_E4
- test_REG_CN_03 (atomic transaction)
- test_REG_CN_13 (auto-enroll)

**Frontend Unit:**
- test_REG_UC_01_code_validation
- test_REG_UC_01_local_form_validation
- test_REG_UC_01_oauth_entry
- test_REG_UC_01_error_display

**Integration:**
- test_REG_UC_01_local_registration_flow
- test_REG_UC_01_oauth_registration_flow
- test_REG_UC_01_student_auto_enroll

**E2E (Playwright):**
- test_REG_UC_01_e2e_local
- test_REG_UC_01_e2e_oauth

---

### REG-UC-02 — Code Generation

**Roles:** ADMIN, RESEARCHER, TEACHER

**Preconditions:** Authenticated user with permission to generate codes for target role.

**Trigger:** User submits code generation form.

**Main Flow:**
1. User selects target role (admin → researcher, researcher → teacher, teacher → student).
2. User enters **count** and **uses per code**.
3. User selects expiration date+time (required).
4. Teacher flow: select a course (required for student codes).
5. Researcher flow: optional metadata for teacher codes (name, district, etc.).
6. System validates constraints and permissions.
7. System generates codes, stores hashed values, and returns plaintext codes once.

**Postcondition:** Codes created with expiration and usage limits.

**Role Coverage:**

> **REG-UC-02-ADMIN**
> - Generate researcher codes

> **REG-UC-02-RESEARCHER**
> - Generate teacher codes (optional metadata)

> **REG-UC-02-TEACHER**
> - Generate student codes (course required)

**Errors:**

**REG-UC-02-E1** — Invalid counts/uses
- Trigger: count or uses per code invalid
- Behavior: Validation error

**REG-UC-02-E2** — Missing/invalid expiration
- Trigger: No expiration or invalid timestamp
- Behavior: Validation error; expiration required

**REG-UC-02-E3** — Missing required course (teacher)
- Trigger: Teacher generating student code without course
- Behavior: Validation error; course required

**REG-UC-02-E4** — Metadata + multiple codes (researcher)
- Trigger: Metadata attached with count > 1
- Behavior: Error; must generate 1 code when metadata attached

**REG-UC-02-E5** — Insufficient permission
- Trigger: User lacks permission for target role
- Behavior: Access denied

**Tests:**

**Backend Unit:**
- test_REG_UC_02 (aggregator)
- test_REG_UC_02_ADMIN
- test_REG_UC_02_RESEARCHER
- test_REG_UC_02_TEACHER
- test_REG_UC_02_E1
- test_REG_UC_02_E2
- test_REG_UC_02_E3
- test_REG_UC_02_E4
- test_REG_UC_02_E5
- test_REG_CN_07 (count + uses)
- test_REG_CN_11 (metadata -> single code)
- test_REG_CN_12 (expiry required)

**Frontend Unit:**
- test_REG_UC_02_form_validation
- test_REG_UC_02_expiry_picker
- test_REG_UC_02_metadata_toggle

**Integration:**
- test_REG_UC_02_generate_codes_admin
- test_REG_UC_02_generate_codes_researcher
- test_REG_UC_02_generate_codes_teacher

**E2E (Playwright):**
- test_REG_UC_02_e2e_generate_teacher_codes
- test_REG_UC_02_e2e_generate_student_codes

---

### REG-UC-03 — Code Lifecycle (List / State Transitions)

**Roles:** ADMIN, RESEARCHER, TEACHER

**Preconditions:** Authenticated user with access to codes in scope.

**Trigger:** User opens code management view.

**Main Flow:**
1. System lists codes scoped to role/ownership.
2. User views code detail.
3. User may request a lifecycle transition via state update (REVOKED or ARCHIVED).
4. System validates transition against current state and permissions.
5. System updates code status accordingly.

**Postcondition:** Code lifecycle state updated; no changes to existing accounts.

**Role Coverage:**

> **REG-UC-03-ADMIN**
> - View and manage all codes

> **REG-UC-03-RESEARCHER**
> - View and manage own generated teacher codes

> **REG-UC-03-TEACHER**
> - View and manage own generated student codes

**Errors:**

**REG-UC-03-E1** — Insufficient permission/scope
- Trigger: User attempts to access code outside scope
- Behavior: Access denied

**REG-UC-03-E2** — Invalid state transition
- Trigger: Revoke or archive not allowed for current state
- Behavior: Error message; state unchanged

**Tests:**

**Backend Unit:**
- test_REG_UC_03 (aggregator)
- test_REG_UC_03_ADMIN
- test_REG_UC_03_RESEARCHER
- test_REG_UC_03_TEACHER
- test_REG_UC_03_E1
- test_REG_UC_03_E2
- test_REG_CN_04 (scope)
- test_REG_CN_05 (lifecycle states)
- test_REG_CN_15 (revoke/archive semantics)

**Frontend Unit:**
- test_REG_UC_03_list_view
- test_REG_UC_03_detail_view
- test_REG_UC_03_revoke_confirm
- test_REG_UC_03_archive_action

**Integration:**
- test_REG_UC_03_list_scope
- test_REG_UC_03_revoke_flow
- test_REG_UC_03_archive_flow

**E2E (Playwright):**
- test_REG_UC_03_e2e_revoke
- test_REG_UC_03_e2e_archive

---

## 5) Constraints

### REG-CN-01 — Code Entropy Requirements
- Codes must be non-guessable and high entropy
- Format and length can be standardized during implementation
- **Applies to:** REG-UC-01, REG-UC-02
- **Implements:** NFR-SEC-02 (Registration Code Entropy)

### REG-CN-02 — Code Expiration Enforcement
- Expired codes cannot be used for registration
- **Applies to:** REG-UC-01, REG-UC-03

### REG-CN-03 — Atomic Registration Transaction
- Registration + code usage decrement + enrollment must be atomic
- **Applies to:** REG-UC-01
- **Implements:** NFR-REL-01 (Transaction Atomicity for Multi-Record Operations)

### REG-CN-04 — Code Visibility Scope
- Admin: all codes
- Researcher: teacher codes they generated
- Teacher: student codes they generated
- Sudo expands scope
- **Applies to:** REG-UC-02, REG-UC-03

### REG-CN-05 — Code Lifecycle States
- States: ACTIVE, EXHAUSTED, EXPIRED, REVOKED, ARCHIVED
- Archival hides from default list; does not delete
- **Applies to:** REG-UC-03

### REG-CN-06 — Researcher Codes Admin-Only
- Only ADMIN can generate researcher registration codes
- **Applies to:** REG-UC-02

### REG-CN-07 — Count + Uses Required
- Generation requires count and uses per code
- No fixed limits; class vs individual differs only by usage count
- **Applies to:** REG-UC-02

### REG-CN-08 — Codes Returned Once
- Generated codes are shown in plaintext once for sharing
- **Applies to:** REG-UC-02

### REG-CN-09 — Optional Teacher Metadata
- Metadata fields are optional
- **Applies to:** REG-UC-02

### REG-CN-10 — Permissions Follow Role Hierarchy + Sudo
- Only allowed roles can generate codes for the next level
- **Applies to:** REG-UC-02, REG-UC-03
- **Implements:** NFR-PRIV-01 (FERPA-Compliant Data Access Controls) - (code generation permission hierarchy)

### REG-CN-11 — Metadata Locks Count to 1
- If metadata is attached, only one code may be generated
- **Applies to:** REG-UC-02

### REG-CN-12 — Expiration Required
- Expiration required for all generated codes
- Date+time picker used in UI
- **Applies to:** REG-UC-02

### REG-CN-13 — Student Codes Require Course
- Teacher student codes must link to a course
- Registration auto-enrolls student into linked course
- **Applies to:** REG-UC-01, REG-UC-02

### REG-CN-14 — Admin Bootstrap Only
- Admin accounts are bootstrapped via environment
- No admin self-registration
- **Applies to:** REG-UC-01

### REG-CN-15 — Revoke/Archive Semantics
- Revoke blocks new registrations only
- Archive hides from default lists (visibility-only)
- Manual lifecycle transitions are requested as state changes (`REVOKED`, `ARCHIVED`)
- `EXPIRED` and `EXHAUSTED` are server-derived states (not client-settable)
- Neither action disables existing accounts
- **Applies to:** REG-UC-03

---

## 6) Code State Machines

### Code Status States

```
[Generated] → Active → Exhausted (uses = 0)
                 → Expired (time elapsed)
                 → Revoked (manual)

Exhausted / Expired / Revoked → Archived (visibility-only)
```

### Registration Transaction

```
[Code Validated] → [User Created] → [Code Usage Decremented] → [Enroll Student (if applicable)]
```

---

## 7) Endpoints (Draft)

### Registration

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/registration/validate-code` | None | REG-UC-01 |
| POST | `/api/v1/registration/local` | None | REG-UC-01 |
| POST | `/api/v1/registration/oauth` | None | REG-UC-01 |

### Code Generation

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/codes` | Access token | REG-UC-02 |

### Code Lifecycle

| Method | Path | Auth | UC |
|--------|------|------|----|
| GET | `/api/v1/codes` | Access token | REG-UC-03 |
| GET | `/api/v1/codes/{id}` | Access token | REG-UC-03 |
| PATCH | `/api/v1/codes/{id}` | Access token | REG-UC-03 |

**PATCH payload examples (state-driven):**
- `{ "status": "REVOKED", "reason": "manual_stop" }`
- `{ "status": "ARCHIVED" }`

> Endpoints are proposed and can be adjusted during implementation.

---

## 8) Wireframe Mapping

| UC / Error | Wireframe Screens |
|------------|-------------------|
| REG-UC-01 | C1, C1 (load), C1c, C2, C3, C4, C5, C5b |
| REG-UC-01-E1 | C1b |
| REG-UC-01-E2/E3 | C3b |
| REG-UC-01-E4 | C4b |
| REG-UC-02-ADMIN | D1, D1b |
| REG-UC-02-RESEARCHER | D2, D2b, D2c, D2d |
| REG-UC-02-TEACHER | D3, D3b |
| REG-UC-02-E1/E2/E3/E5 | (annotation on D1–D3) |
| REG-UC-02-E4 | D2c |
| REG-UC-03 | E1, E2, E2b |
| REG-UC-03-E1/E2 | (annotation on E1/E2b) |

> Screen IDs reference the Figma Make wireframes. Verify via official Figma MCP against file `WGyIhW6EpOwfvVH3idkEtG`.

---

## 9) Shared Code Generation (Implementation Note)

Registration codes use the same **core code generator** as password reset codes (AUTH), with a **registration-specific policy**.

- **Registration policy:** persistent storage, usage counts, revocation + archival states, course linkage for student codes
- **Reset policy:** short-lived, single-use, not archived, request-token based lookup

This is an implementation detail; requirements remain scoped under REG and AUTH.
