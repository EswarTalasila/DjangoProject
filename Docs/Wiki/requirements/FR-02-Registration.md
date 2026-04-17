# FR-02 Registration (REG) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-28 |
| **Domain** | REG |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER, STUDENT |
| **Related Issues** | #29 (code-gated auth/registration), #28 (role hierarchy/sudo) |
| **Dependencies** | FR-01 AUTH (shared code generator, login after registration), FR-03 SUDO (role hierarchy for code generation scope), FR-05 CRS (course linkage for student codes) |

---

## 1) Scope

### In Scope
- Code-gated registration for RESEARCHER, TEACHER, STUDENT
- Local registration for non-admin roles with managed username generation (first/last name + password; email required for non-students)
- Local registration for students (first/last name + generated immutable username + password; email optional)
- OAuth registration (Google) for non-students
- Access code validation (status, expiry, uses remaining)
- Code generation (count + uses per code, expiration, optional metadata)
- Code lifecycle management (list, detail, revoke, delete, legacy archived visibility)
- Student auto-enrollment when registering with a teacher-issued code
- Student join-course redemption using additional teacher-issued codes after account creation

### Out of Scope
- Self-registration without an access code
- Admin self-registration (bootstrapped via environment)
- Email-based invites or SMTP workflows
- Account disabling as a side-effect of code revocation

### Core Intent
- Gate all user registration behind validated access codes with role-specific policies.
- Automate student enrollment via course-linked registration codes.
- Support both local and OAuth registration paths for non-student roles.

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
   - Local: user enters first name, last name, email, and password; system generates immutable username and creates account
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
- Trigger: Missing first/last name or password for student registration, or missing first/last name/email/password for non-student local registration
- Behavior: Required field errors

**REG-UC-01-E4** — OAuth registration error
- Trigger: OAuth cancelled/failed or missing email (non-student only)
- Behavior: OAuth error message; return to registration choice

**REG-UC-01-E5** — Student OAuth unsupported
- Trigger: Student code flow attempts OAuth registration
- Behavior: Clear unsupported-flow error; prompt student local registration flow

**Tests (representative):**
- test_REG_UC_01, test_REG_UC_01_RESEARCHER, test_REG_UC_01_TEACHER, test_REG_UC_01_STUDENT
- test_REG_UC_01_E1 through test_REG_UC_01_E5
- test_REG_CN_16, test_REG_CN_03, test_REG_CN_13

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

**Tests (representative):**
- test_REG_UC_01a_STUDENT, test_REG_UC_01a_E1, test_REG_UC_01a_E2
- test_REG_CN_03, test_REG_CN_20

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

**Tests (representative):**
- test_REG_UC_02, test_REG_UC_02_ADMIN, test_REG_UC_02_RESEARCHER, test_REG_UC_02_TEACHER
- test_REG_UC_02_E1 through test_REG_UC_02_E5
- test_REG_CN_07, test_REG_CN_11, test_REG_CN_12, test_REG_CN_10

---

### REG-UC-03 — Code Lifecycle (List / State Transitions)

**Roles:** ADMIN, RESEARCHER, TEACHER

**Preconditions:** Authenticated user with access to codes in scope.

**Trigger:** User opens code management view.

**Main Flow:**
1. System lists codes scoped to role/ownership.
2. User views code detail.
3. User may revoke an active code via state update.
4. User may delete a code in scope; active deletion first revokes, then removes the row.
5. System validates the action against current state and permissions.

**Postcondition:** Code is revoked or removed; no changes to existing accounts.

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

**REG-UC-03-E2** — Invalid lifecycle action
- Trigger: Revoke not allowed for current state
- Behavior: Error message; state unchanged

**Tests (representative):**
- test_REG_UC_03, test_REG_UC_03_ADMIN, test_REG_UC_03_RESEARCHER, test_REG_UC_03_TEACHER
- test_REG_UC_03_E1, test_REG_UC_03_E2
- test_REG_CN_04, test_REG_CN_05, test_REG_CN_15

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
- States: ACTIVE, EXHAUSTED, EXPIRED, REVOKED
- Legacy archived rows may still exist for compatibility, but active lifecycle management uses revoke and delete
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

### REG-CN-15 — Revoke/Delete Semantics
- Revoke blocks new registrations only
- Delete permanently removes the code record; deleting an active code first revokes it internally
- Manual lifecycle transitions are requested only as state change `REVOKED`
- `EXPIRED` and `EXHAUSTED` are server-derived states (not client-settable)
- Neither action disables existing accounts
- **Applies to:** REG-UC-03

### REG-CN-16 — Managed Username Generation + Immutability (All Non-Admin Roles)
- STUDENT, TEACHER, and RESEARCHER usernames are generated by the system from first initial + last name (normalized)
- Managed usernames are fixed width (8 chars) with trailing numeric index for uniqueness (e.g., `zboston0`, `zboston1`)
- Generated usernames are immutable after account creation
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
- RESEARCHER and TEACHER registrations persist both system-managed `username` and provided `email`
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

## 6) Infrastructure Contract

### 6.1 Endpoint Contract

#### Registration

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/registration/code-validations` | None | REG-UC-01 |
| POST | `/api/v1/registration/accounts` | None | REG-UC-01 |
| POST | `/api/v1/enrollments` | Access token (Student) | REG-UC-01a |

Notes:
- `POST /api/v1/registration/accounts` accepts a `method` field: `"LOCAL"` or `"OAUTH"`. OAuth is for RESEARCHER/TEACHER registration flows only.
- STUDENT registration must use `method: "LOCAL"` so username generation and immutability are enforced.

#### Code Generation

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/codes` | Access token | REG-UC-02 |

#### Code Lifecycle

| Method | Path | Auth | UC |
|--------|------|------|----|
| GET | `/api/v1/codes` | Access token | REG-UC-03 |
| GET | `/api/v1/codes/{id}` | Access token | REG-UC-03 |
| PATCH | `/api/v1/codes/{id}` | Access token | REG-UC-03 |
| DELETE | `/api/v1/codes/{id}` | Access token | REG-UC-03 |

**PATCH payload examples (state-driven):**
- `{ "status": "REVOKED", "reason": "manual_stop" }`

> Endpoints are proposed and can be adjusted during implementation.

### 6.2 Code State Machines

#### Code Status States

```
[Generated] → Active → Exhausted (uses = 0)
                 → Expired (time elapsed)
                 → Revoked (manual)

Active / Exhausted / Expired / Revoked → Deleted
```

#### Registration Transaction

```
[Code Validated] → [User Created] → [Code Usage Decremented] → [Enroll Student (if applicable)]
```

#### Student Course Join Redemption

```
[Student Authenticated] → [Code Validated] → [Enroll Student]
                                            → [Already Enrolled (idempotent success)]
```

### 6.3 Wireframe Mapping

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

## 7) Error Model

| Scenario | Behavior | Contract |
|----------|----------|----------|
| Invalid/expired/exhausted/revoked access code | Generic error; no code state revealed | `400` |
| Weak password or mismatch confirm | Field-level validation errors | `400` |
| Missing required fields (name, password, email for non-student) | Required field errors | `400` |
| OAuth cancelled/failed or missing email | OAuth error; return to registration choice | `400` |
| Student code attempts OAuth registration | Unsupported-flow error; prompt local registration | `403` |
| Invalid count or uses per code | Validation error | `400` |
| Missing/invalid expiration | Validation error; expiration required | `400` |
| Teacher generating student code without course | Validation error; course required | `400` |
| Metadata with count > 1 | Error; single code required with metadata | `400` |
| Insufficient permission for target role | Access denied | `403` |
| Access code outside visibility scope | Access denied | `403` |
| Invalid lifecycle action | Error; state unchanged | `409` |
| Non-student attempts course-join endpoint | Access denied | `403` |

---

## 8) Test Strategy by Layer

**Naming Convention:** `test_REG_UC_nn[_ROLE|_En]`, `test_REG_CN_nn`, `ST-REG-UC-nn`

### Backend Unit
- test_REG_UC_01 (aggregator)
- test_REG_UC_01_RESEARCHER
- test_REG_UC_01_TEACHER
- test_REG_UC_01_STUDENT
- test_REG_UC_01_E1
- test_REG_UC_01_E2
- test_REG_UC_01_E3
- test_REG_UC_01_E4
- test_REG_UC_01_E5
- test_REG_UC_01a_STUDENT
- test_REG_UC_01a_E1
- test_REG_UC_01a_E2
- test_REG_UC_02 (aggregator)
- test_REG_UC_02_ADMIN
- test_REG_UC_02_RESEARCHER
- test_REG_UC_02_TEACHER
- test_REG_UC_02_E1
- test_REG_UC_02_E2
- test_REG_UC_02_E3
- test_REG_UC_02_E4
- test_REG_UC_02_E5
- test_REG_UC_03 (aggregator)
- test_REG_UC_03_ADMIN
- test_REG_UC_03_RESEARCHER
- test_REG_UC_03_TEACHER
- test_REG_UC_03_E1
- test_REG_UC_03_E2
- REG-CN-01 code entropy _(no backend unit test yet)_
- test_REG_CN_03 (atomic transaction)
- test_REG_CN_04 (scope)
- test_REG_CN_05 (lifecycle states)
- test_REG_CN_07 (count + uses)
- test_REG_CN_10 (role hierarchy + sudo scope)
- test_REG_CN_11 (metadata -> single code)
- test_REG_CN_12 (expiry required)
- test_REG_CN_13 (auto-enroll)
- test_REG_CN_15 (revoke/delete semantics)
- test_REG_CN_16 (username generation + collision suffix)
- test_REG_CN_20 (idempotent already-enrolled semantics)

### Backend Integration
- test_REG_UC_01_local_registration_flow
- test_REG_UC_01_oauth_registration_flow
- test_REG_UC_01_student_auto_enroll
- test_REG_UC_01_student_username_collision_suffix
- test_REG_UC_01a_join_course_flow
- test_REG_UC_01a_already_enrolled_no_usage_decrement
- test_REG_UC_02_generate_codes_admin
- test_REG_UC_02_generate_codes_researcher
- test_REG_UC_02_generate_codes_teacher
- test_REG_UC_03_list_scope
- test_REG_UC_03_revoke_flow
- test_REG_UC_03_delete_flow

### Frontend Unit
- test_REG_UC_01_code_validation
- test_REG_UC_01_local_form_validation
- test_REG_UC_01_student_username_preview
- test_REG_UC_01_oauth_entry
- test_REG_UC_01_error_display
- test_REG_UC_01a_join_code_form
- test_REG_UC_01a_already_enrolled_message
- test_REG_UC_02_form_validation
- test_REG_UC_02_expiry_picker
- test_REG_UC_02_metadata_toggle
- test_REG_UC_03_list_view
- test_REG_UC_03_detail_view
- test_REG_UC_03_revoke_confirm
- test_REG_UC_03_delete_action

### System Tests (Black Box)
- ST-REG-UC-01
- ST-REG-UC-01-E1
- ST-REG-UC-01a
- ST-REG-UC-01a-E1
- ST-REG-UC-02
- ST-REG-UC-02-E5
- ST-REG-UC-03
- ST-REG-UC-03-E2

---

## 9) NFR Cross-References

- **Security**
  - REG-CN-01 code entropy (NFR-SEC-02)
  - REG-CN-22 hash-at-rest (NFR-SEC-07)
- **Privacy**
  - REG-CN-10 role hierarchy (NFR-PRIV-01)
- **Reliability**
  - REG-CN-03 atomic registration (NFR-REL-01)

---

## 10) Cross-Domain References

| Domain | REG dependency | Integration note |
|--------|----------------|------------------|
| FR-01 AUTH | Shared code generator with different policy profiles | Registration codes use same core generator as reset codes |
| FR-03 SUDO | Role hierarchy + sudo for code generation scope | CREATE_STUDENT/CREATE_RESEARCHER_CODES sudo expand researcher code generation |
| FR-05 CRS | Course linkage for student codes | Student codes require course FK; registration auto-enrolls |
| FR-12 ENV | Admin bootstrap; no admin self-registration | Admin accounts created via ensure_admin only |

---

## 11) Current Implementation Alignment Notes

Registration codes use the same **core code generator** as password reset codes (AUTH), with a **registration-specific policy**.

- **Registration policy:** persistent storage, usage counts, revocation + archival states, course linkage for student codes
- **Reset policy:** short-lived, single-use, target-bound, issuer-generated (no request-token queue)

This is an implementation detail; requirements remain scoped under REG and AUTH.

**Implementation notes:**
1. **Code generator reuse.** The shared code generator in AUTH produces high-entropy codes. REG wraps it with registration-specific storage, usage tracking, and lifecycle states. Both domains share entropy and format but diverge on persistence and state management.
2. **Username generation service.** A shared `generate_managed_username(first_name, last_name)` function is needed. It normalizes to `first_initial + last_name`, truncates/pads to 8 chars, and appends a trailing numeric index. Collision resolution queries existing usernames with the same prefix and increments the index.
3. **OAuth integration.** Non-student OAuth registration reuses the same Google OAuth provider configured for AUTH login. The registration flow collects the display name in-app after the OAuth callback returns.
4. **Student course enrollment.** Registration auto-enrollment and join-course redemption both use the same `Enrollment.objects.get_or_create()` pattern from FR-05 CRS, ensuring idempotent enrollment semantics.
5. **HMAC code storage.** Code validation hashes the incoming plaintext with the same deterministic salt used at generation time and compares against the stored digest. The salt is per-deployment (not per-code) to enable O(1) lookup by hash.
