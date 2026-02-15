# FR-02 Registration (REG) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-13 |
| **Domain** | REG |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER, STUDENT |
| **Related Issues** | #29 (code-gated auth/registration), #28 (role hierarchy/sudo) |

---

## 1) Scope

### In Scope
- Code-gated registration for RESEARCHER, TEACHER, STUDENT
- Local registration for non-students (username + email + password + name)
- Local registration for students (first/last name + generated immutable username + password; email optional)
- OAuth registration (Google) for non-students
- Access code validation (status, expiry, uses remaining)
- Code generation (count + uses per code, expiration, optional metadata)
- Code lifecycle management (list, detail, state transitions, archive visibility)
- Student auto-enrollment when registering with a teacher-issued code
- Student join-course redemption using additional teacher-issued codes after account creation

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
| STUDENT | User role | Can self-register with a valid student code and join additional courses via code redemption |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| REG-US-01 | RESEARCHER, TEACHER | As a researcher or teacher I can register using an access code so that I can access the system. |
| REG-US-01a-STUDENT | STUDENT | As a student I can register using a teacher-issued course code so that I get a generated username and immediate course enrollment. |
| REG-US-02 | ADMIN, RESEARCHER, TEACHER | As an admin, researcher, or teacher I can generate access codes with a count, uses-per-code, and expiration so that new users can register. |
| REG-US-03-STUDENT | STUDENT | As a student with an existing account I can redeem another course code so that I can join additional courses without creating a new account. |

---

## 4) Use Cases

### REG-UC-01 — Code-Gated Registration

**Roles:** RESEARCHER, TEACHER, STUDENT

**Preconditions:** User is unauthenticated and possesses a valid access code that matches their target role.

**Trigger:** User enters access code on registration page.

**Main Flow:**
1. User enters access code.
2. System validates code (active, not expired, uses remaining).
3. System determines role and any linked course (student codes).
4. If target role is STUDENT:
   - user enters first name, last name, and password
   - system generates immutable username (`first initial + last name`) and resolves collisions with numeric suffixes
   - username is displayed in locked state before final submit
   - optional student email may be stored but is not used for login
5. If target role is RESEARCHER or TEACHER:
   - user selects registration method: Local or OAuth
   - Local: user enters name, username, email, password; system validates and creates account
   - OAuth: user completes provider flow; system collects display name in-app
6. System links user to code, decrements uses, and sets code status if exhausted.
7. If student code: auto-enroll user in linked course.
8. User is logged in and redirected to dashboard.

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
- Trigger: Weak password, password mismatch, or duplicate username/email identifier for non-student registration
- Behavior: Field-level validation errors

**REG-UC-01-E3** — Missing required fields
- Trigger: Missing name/password for student registration, or missing name/username/email/password for non-student local registration
- Behavior: Required field errors

**REG-UC-01-E4** — OAuth registration error
- Trigger: OAuth cancelled/failed or missing email (non-student only)
- Behavior: OAuth error message; return to registration choice

**REG-UC-01-E5** — Student OAuth unsupported
- Trigger: Student code flow attempts OAuth registration
- Behavior: Clear unsupported-flow error; prompt student local registration flow

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
- test_REG_UC_01_E5
- test_REG_CN_16 (username generation + collision suffix)
- test_REG_CN_03 (atomic transaction)
- test_REG_CN_13 (auto-enroll)

**Frontend Unit:**
- test_REG_UC_01_code_validation
- test_REG_UC_01_local_form_validation
- test_REG_UC_01_student_username_preview
- test_REG_UC_01_oauth_entry
- test_REG_UC_01_error_display

**Backend Integration:**
- test_REG_UC_01_local_registration_flow
- test_REG_UC_01_oauth_registration_flow
- test_REG_UC_01_student_auto_enroll
- test_REG_UC_01_student_username_collision_suffix

**Frontend Integration:**
- N/A (covered by E2E registration flows)

**Security:**
- N/A (covered by backend code validation and constraint tests)

**E2E (Playwright):**
- test_REG_UC_01_e2e_local
- test_REG_UC_01_e2e_oauth

**System Tests (Black Box):**
- ST-REG-UC-01
- ST-REG-UC-01-E1

---

### REG-UC-01a — Student Course Join via Code Redemption

**Roles:** STUDENT

**Preconditions:** Authenticated student account exists.

**Trigger:** Student submits a teacher-issued student code from join-course UI.

**Main Flow:**
1. Student enters code while authenticated.
2. System validates code (active, not expired, uses remaining) and resolves linked course.
3. System checks if student is already enrolled in linked course.
4. If not enrolled, enrollment is created and code usage is decremented atomically.
5. If already enrolled, return idempotent `already_enrolled` response and do not decrement usage.
6. Student remains logged in and sees updated course list.

**Postcondition:** Student is enrolled in the linked course or receives idempotent already-enrolled confirmation.

**Errors:**

**REG-UC-01a-E1** — Access code error
- Trigger: Invalid, expired, exhausted, or revoked student code
- Behavior: Generic invalid-code style error

**REG-UC-01a-E2** — Non-student access blocked
- Trigger: Non-student role attempts course-join redemption endpoint
- Behavior: Access denied

**Tests:**

**Backend Unit:**
- test_REG_UC_01a_STUDENT
- test_REG_UC_01a_E1
- test_REG_UC_01a_E2
- test_REG_CN_03 (atomic transaction)
- test_REG_CN_20 (idempotent already-enrolled semantics)

**Frontend Unit:**
- test_REG_UC_01a_join_code_form
- test_REG_UC_01a_already_enrolled_message

**Backend Integration:**
- test_REG_UC_01a_join_course_flow
- test_REG_UC_01a_already_enrolled_no_usage_decrement

**Frontend Integration:**
- N/A (covered by E2E join-course flow)

**Security:**
- N/A (covered by backend role and code-state enforcement tests)

**E2E (Playwright):**
- test_REG_UC_01a_e2e_join_course

**System Tests (Black Box):**
- ST-REG-UC-01a
- ST-REG-UC-01a-E1

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
7. System generates codes, stores deterministic salted HMAC hashes (not plaintext), and returns plaintext codes once.

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
- test_REG_CN_10 (role hierarchy + sudo scope)

**Frontend Unit:**
- test_REG_UC_02_form_validation
- test_REG_UC_02_expiry_picker
- test_REG_UC_02_metadata_toggle

**Backend Integration:**
- test_REG_UC_02_generate_codes_admin
- test_REG_UC_02_generate_codes_researcher
- test_REG_UC_02_generate_codes_teacher

**Frontend Integration:**
- N/A (covered by E2E code-generation flows)

**Security:**
- N/A (covered by backend permission and lifecycle constraint tests)

**E2E (Playwright):**
- test_REG_UC_02_e2e_generate_teacher_codes
- test_REG_UC_02_e2e_generate_student_codes

**System Tests (Black Box):**
- ST-REG-UC-02
- ST-REG-UC-02-E5

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

**Backend Integration:**
- test_REG_UC_03_list_scope
- test_REG_UC_03_revoke_flow
- test_REG_UC_03_archive_flow

**Frontend Integration:**
- N/A (covered by E2E lifecycle flows)

**Security:**
- N/A (covered by backend scope and transition gate tests)

**E2E (Playwright):**
- test_REG_UC_03_e2e_revoke
- test_REG_UC_03_e2e_archive

**System Tests (Black Box):**
- ST-REG-UC-03
- ST-REG-UC-03-E2

---

## 5) Constraints

### REG-CN-01 — Code Entropy Requirements
- Codes must be non-guessable and high entropy
- Format and length can be standardized during implementation
- **Applies to:** REG-UC-01, REG-UC-02
- **Implements:** NFR-SEC-02 (Registration Code Entropy)

### REG-CN-02 — Code Expiration Enforcement
- Expired codes cannot be used for registration or join-course redemption
- **Applies to:** REG-UC-01, REG-UC-01a, REG-UC-03

### REG-CN-03 — Atomic Registration Transaction
- Registration/redeem + code usage decrement + enrollment must be atomic
- **Applies to:** REG-UC-01, REG-UC-01a
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
- Stored code material must never expose plaintext at rest
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
- Authenticated student redemption also enrolls into linked course
- **Applies to:** REG-UC-01, REG-UC-01a, REG-UC-02

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

### REG-CN-16 — Student Username Generation + Immutability
- Student username is generated from first initial + last name (normalized)
- Username collisions must resolve by deterministic numeric suffixing (e.g., `jsmith`, `jsmith2`)
- Generated username is immutable after account creation
- **Applies to:** REG-UC-01

### REG-CN-17 — Student Identifier Policy
- Student authentication identifier is username, not email
- Student username must be displayed in locked state before submit during registration
- **Applies to:** REG-UC-01

### REG-CN-18 — Student Email Optional and Non-Auth
- Student email may be null or optional metadata only
- Student email is never used as login identifier
- **Applies to:** REG-UC-01

### REG-CN-21 — Non-Student Dual Identifier Account Fields
- RESEARCHER and TEACHER registrations must persist both `username` and `email`
- Non-student authentication may use either `username` or `email` as identifier
- Identifier values must be globally unique across both fields to avoid login ambiguity
- **Applies to:** REG-UC-01

### REG-CN-19 — Student OAuth Registration Disabled
- Student registration does not support OAuth until role-identifier mapping is explicitly redesigned
- Student code flows must enforce local registration only
- **Applies to:** REG-UC-01

### REG-CN-20 — Existing Student Code Redemption Idempotency
- Redeeming a course code for a course where the student is already enrolled must return success (`already_enrolled`) without duplicate enrollment
- Already-enrolled redemptions must not consume a code use
- **Applies to:** REG-UC-01a

### REG-CN-22 — Registration Code Hash-At-Rest
- Registration codes must be persisted as deterministic salted HMAC digests; plaintext code values must not be stored
- Validation and redemption must hash incoming plaintext and compare against persisted digest
- Code list/detail responses must expose a non-sensitive prefix only; plaintext is returned only at generation time
- **Applies to:** REG-UC-01, REG-UC-01a, REG-UC-02, REG-UC-03
- **Implements:** NFR-SEC-07 (Registration Code Storage Hardening)

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

### Student Course Join Redemption

```
[Student Authenticated] → [Code Validated] → [Enroll Student]
                                            → [Already Enrolled (idempotent success)]
```

---

## 7) Endpoints (Draft)

### Registration

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/registration/code-validations` | None | REG-UC-01 |
| POST | `/api/v1/registration/accounts` | None | REG-UC-01 |
| POST | `/api/v1/enrollments` | Access token (Student) | REG-UC-01a |

Notes:
- `POST /api/v1/registration/accounts` accepts a `method` field: `"LOCAL"` or `"OAUTH"`. OAuth is for RESEARCHER/TEACHER registration flows only.
- STUDENT registration must use `method: "LOCAL"` so username generation and immutability are enforced.

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
| REG-UC-01a | C6, C6b |
| REG-UC-01-E1 | C1b |
| REG-UC-01-E2/E3 | C3b |
| REG-UC-01-E4 | C4b |
| REG-UC-01-E5 | C4c |
| REG-UC-01a-E1/E2 | C6c |
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
