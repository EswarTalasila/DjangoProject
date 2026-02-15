# FR-01 Authentication (AUTH) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-13 |
| **Domain** | AUTH |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER, STUDENT |
| **Related Issues** | #29 (code-gated auth/registration), #28 (role hierarchy/sudo) |

---

## 1) Scope

### In Scope
- Password login for all roles with role-based identifiers (student username; non-student username or email)
- OAuth login for code-gated non-student accounts
- Token refresh (backend-only)
- Self-service password change
- Approval-based password reset for non-student roles (no SMTP)
- Teacher-initiated student password reset (direct code generation from course roster)
- Reset request status lookup (request token, non-student only)
- Reset request state transitions (approve/deny by researcher/admin; teacher generates directly)
- Django admin login for ADMIN (system role)
- Logout

### Out of Scope
- Email-based password reset (SMTP)
- Self-registration (handled in FR-02 REG)
- First-time login / onboarding tokens (removed)

---

## 2) Actors

| Role | Type | Notes |
|------|------|-------|
| ADMIN | System role | `is_staff=True`; can use Django admin panel |
| RESEARCHER | User role | Highest user role; can approve teacher resets |
| TEACHER | User role | Can generate student reset codes directly from course roster |
| STUDENT | User role | Receives reset code from teacher; cannot self-request or approve |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| AUTH-US-01 | ADMIN, RESEARCHER, TEACHER | As an admin, researcher, or teacher I can log in with my username or email and password so that I can access the application. |
| AUTH-US-01b-STUDENT | STUDENT | As a student I can log in with my generated username and password so that I can access the application without email. |
| AUTH-US-01a-ADMIN | ADMIN | As an admin I can log in to the Django admin panel so that I can manage the system. |
| AUTH-US-02 | ADMIN, RESEARCHER, TEACHER | As an admin, researcher, or teacher I can log in with Google OAuth so that I can access the application without a password. |
| AUTH-US-03 | ALL | As an admin, researcher, teacher, or student I can have my session tokens refreshed so that I stay authenticated during active use. |
| AUTH-US-04 | ALL | As an admin, researcher, teacher, or student I can change my password so that I can keep my account secure. |
| AUTH-US-05 | RESEARCHER, TEACHER | As a researcher or teacher I can request an approval-based password reset so that I can regain access to my account using my role identifier. |
| AUTH-US-05b-STUDENT | STUDENT | As a student I can use a reset code provided by my teacher to set a new password so that I can regain access to my account. |
| AUTH-US-06 | RESEARCHER, TEACHER | As a researcher or teacher I can look up the status of my reset request so that I know whether it has been approved, denied, or is still pending. |
| AUTH-US-07 | ADMIN, RESEARCHER, TEACHER | As an admin or researcher I can approve or deny password reset requests, and as a teacher I can generate reset codes directly for students in my courses, so that users under my scope can regain account access. |
| AUTH-US-08 | ALL | As an admin, researcher, teacher, or student I can log out so that my session is securely terminated. |

---

## 4) Use Cases

### Core Authentication

#### AUTH-UC-01 — Password Login

**Roles:** ALL

**Preconditions:** User account exists; account not disabled/suspended.

**Trigger:** User submits identifier + password on login page.

**Main Flow:**
1. User enters identifier + password.
2. System validates credentials.
3. On success, return access token/session and role.
4. User is redirected to dashboard.

**Postcondition:** Active session established.

**Role Coverage:**

> **AUTH-UC-01-ADMIN / RESEARCHER / TEACHER**
> - Identifier: Username or email
> - Entry: Application login page
>
> **AUTH-UC-01-STUDENT**
> - Identifier: Username generated at registration
> - Entry: Application login page

**Variants:**

> **AUTH-UC-01a** — Django Admin Login
>
> > **AUTH-UC-01a-ADMIN**
> > - Entry: `/admin/` portal
> > - Auth: Django admin authentication
> > - Scope: `is_staff=True` only
> > - Precondition: Admin account bootstrapped via environment (ENV-UC-02)

**Errors:**

**AUTH-UC-01-E1** — Generic login error
- Trigger: Invalid credentials
- Behavior: Generic error message; no user enumeration
- Constraint: AUTH-CN-04

**AUTH-UC-01-E2** — Rate limit error
- Trigger: Too many failed attempts on same identifier
- Behavior: Cooldown message; 5 attempts per 15 minutes
- Constraint: AUTH-CN-03

**AUTH-UC-01-E3** — Login blocked
- Trigger: Account disabled or suspended
- Behavior: Generic error (may be masked to prevent enumeration)
- Constraint: AUTH-CN-04

**Tests:**

**Backend Unit:**
- test_AUTH_UC_01 (aggregator)
- test_AUTH_UC_01_ADMIN
- test_AUTH_UC_01_RESEARCHER
- test_AUTH_UC_01_TEACHER
- test_AUTH_UC_01_STUDENT
- test_AUTH_UC_01a_ADMIN
- test_AUTH_UC_01_E1
- test_AUTH_UC_01_E2
- test_AUTH_UC_01_E3
- test_AUTH_CN_04 (no enumeration)
- test_AUTH_CN_12 (role-based identifier policy)

**Frontend Unit:**
- test_AUTH_UC_01_form_validation
- test_AUTH_UC_01_error_display

**Backend Integration:**
- test_AUTH_UC_01_login_flow
- test_AUTH_UC_01a_admin_login_flow

**Frontend Integration:**
- N/A (covered by E2E for full auth flow)

**Security:**
- N/A (covered by backend constraint and error-path tests)

**E2E (Playwright):**
- test_AUTH_UC_01_e2e_login
- test_AUTH_UC_01a_e2e_admin_login

**System Tests (Black Box):**
- ST-AUTH-UC-01
- ST-AUTH-UC-01-E1

---

#### AUTH-UC-02 — OAuth Login

**Roles:** ADMIN, RESEARCHER, TEACHER

**Preconditions:** Non-student account exists and was created via code-gated registration (FR-02 REG).

**Trigger:** User selects "Continue with Google."

**Main Flow:**
1. User completes OAuth provider flow.
2. System validates OAuth token and account eligibility.
3. Session token issued; user redirected to dashboard.

**Postcondition:** Active session established.

**Role Coverage:**

> **AUTH-UC-02-ADMIN / RESEARCHER / TEACHER**
> - Behavior: Identical flow for non-student roles

**Errors:**

**AUTH-UC-02-E1** — OAuth denied/failed
- Trigger: User cancels OAuth or provider error
- Behavior: Clear error message; return to login

**AUTH-UC-02-E2** — OAuth account not eligible
- Trigger: No prior code-gated registration, or account suspended
- Behavior: Error indicating account not found or not eligible

**Tests:**

**Backend Unit:**
- test_AUTH_UC_02 (aggregator)
- test_AUTH_UC_02_ADMIN
- test_AUTH_UC_02_RESEARCHER
- test_AUTH_UC_02_TEACHER
- test_AUTH_UC_02_E1
- test_AUTH_UC_02_E2
- test_AUTH_CN_13 (student OAuth disallowed)

**Frontend Unit:**
- test_AUTH_UC_02_oauth_button

**Backend Integration:**
- test_AUTH_UC_02_oauth_flow

**Frontend Integration:**
- N/A (covered by E2E for full OAuth flow)

**Security:**
- N/A (covered by backend eligibility and role-gate tests)

**E2E (Playwright):**
- test_AUTH_UC_02_e2e_oauth_login

**System Tests (Black Box):**
- ST-AUTH-UC-02
- ST-AUTH-UC-02-E2

---

#### AUTH-UC-03 — Token Refresh (backend-only)

**Roles:** ALL

**Preconditions:** Refresh token is valid and not expired.

**Trigger:** Client calls refresh endpoint.

**Main Flow:** Validate refresh token → return new access token.

**Postcondition:** Updated access token.

**Role Coverage:**

> **AUTH-UC-03-ALL**
> - Behavior: Identical flow for ADMIN, RESEARCHER, TEACHER, STUDENT

**Errors:** None defined (standard auth error on invalid/expired token).

**Tests:**

**Backend Unit:**
- test_AUTH_UC_03 (aggregator)
- test_AUTH_UC_03_ADMIN
- test_AUTH_UC_03_RESEARCHER
- test_AUTH_UC_03_TEACHER
- test_AUTH_UC_03_STUDENT
- test_AUTH_CN_02 (JWT lifetimes)

**Frontend Unit:**
- N/A (backend-only use case)

**Backend Integration:**
- N/A (covered by backend API/integration auth suite)

**Frontend Integration:**
- N/A (backend-only use case)

**Security:**
- N/A (covered by backend token validation and auth guard tests)

**E2E (Playwright):**
- N/A (backend-only use case)

**System Tests (Black Box):**
- ST-AUTH-UC-03

---

#### AUTH-UC-08 — Logout

**Roles:** ALL

**Preconditions:** User is authenticated.

**Trigger:** User clicks logout.

**Main Flow:** Invalidate session/token and return to login page.

**Postcondition:** Session invalidated.

**Role Coverage:**

> **AUTH-UC-08-ALL**
> - Behavior: Identical flow for ADMIN, RESEARCHER, TEACHER, STUDENT

**Errors:** None defined.

**Tests:**

**Backend Unit:**
- test_AUTH_UC_08 (aggregator)
- test_AUTH_UC_08_ADMIN
- test_AUTH_UC_08_RESEARCHER
- test_AUTH_UC_08_TEACHER
- test_AUTH_UC_08_STUDENT

**Frontend Unit:**
- test_AUTH_UC_08_logout_button

**Backend Integration:**
- N/A (covered by backend logout/blacklist flow tests)

**Frontend Integration:**
- N/A (covered by E2E logout flow)

**Security:**
- N/A (covered by backend token invalidation tests)

**E2E (Playwright):**
- test_AUTH_UC_08_e2e_logout

**System Tests (Black Box):**
- ST-AUTH-UC-08

---

### Password Management

#### AUTH-UC-04 — Change Password (self-service)

**Roles:** ALL

**Preconditions:** User is authenticated.

**Trigger:** User submits current password + new password + confirm.

**Main Flow:**
1. Verify current password.
2. Validate new password against strength policy (AUTH-CN-01).
3. Verify new password differs from old (AUTH-UC-04-E2).
4. Update password.
5. Invalidate all sessions (AUTH-CN-11).
6. Redirect to login.

**Postcondition:** Password updated; all sessions revoked; user must re-login.

**Role Coverage:**

> **AUTH-UC-04-ALL**
> - Behavior: Identical flow for ADMIN, RESEARCHER, TEACHER, STUDENT

**Errors:**

**AUTH-UC-04-E1** — Change password failed
- Trigger: Weak password, mismatch confirm, or incorrect current password
- Behavior: Specific error per failure type
- Constraint: AUTH-CN-01

**AUTH-UC-04-E2** — New password equals old
- Trigger: New password is identical to current password
- Behavior: Rejection with clear message

**Tests:**

**Backend Unit:**
- test_AUTH_UC_04 (aggregator)
- test_AUTH_UC_04_ADMIN
- test_AUTH_UC_04_RESEARCHER
- test_AUTH_UC_04_TEACHER
- test_AUTH_UC_04_STUDENT
- test_AUTH_UC_04_E1
- test_AUTH_UC_04_E2
- test_AUTH_CN_01 (password strength)
- test_AUTH_CN_11 (session invalidation)

**Frontend Unit:**
- test_AUTH_UC_04_form_validation
- test_AUTH_UC_04_password_strength_indicator

**Backend Integration:**
- test_AUTH_UC_04_change_password_flow

**Frontend Integration:**
- N/A (covered by E2E password-change flow)

**Security:**
- N/A (covered by backend policy/session-invalidation tests)

**E2E (Playwright):**
- test_AUTH_UC_04_e2e_change_password

**System Tests (Black Box):**
- ST-AUTH-UC-04
- ST-AUTH-UC-04-E1

---

### Approval-Based Password Reset

#### AUTH-UC-05 — Password Reset

**Roles:** RESEARCHER, TEACHER, STUDENT

**Preconditions:** User has a valid account.

**Main Flow (RESEARCHER / TEACHER — request-based):**
1. User submits reset request identifier via login screen.
2. System creates pending request and generates request token (REQ-...).
3. Request token is shown once with warning; stored in session.
4. Approver reviews request (AUTH-UC-07).
5. If approved, a reset code (RESET-...) is generated.
6. User enters reset code and sets new password.
7. No auto-login; user returns to login.

**Main Flow (STUDENT — teacher-initiated):**
1. Student approaches teacher out-of-band (in person, etc.).
2. Teacher generates a reset code for the student via course roster (AUTH-UC-07-TEACHER).
3. Teacher shares reset code with student out-of-band.
4. Student enters reset code and sets new password.
5. No auto-login; student returns to login.

**Postcondition:** Password reset; user must log in with new password.

**Role Coverage:**

> **AUTH-UC-05-RESEARCHER**
> - Requests reset from: Admin
> - Identifier submitted: Email
> - Expiry: Configurable via date+time picker, default 30 min
> - Notes: Highest user role; only admin can approve

> **AUTH-UC-05-TEACHER**
> - Requests reset from: Researcher
> - Identifier submitted: Email
> - Expiry: Configurable via date+time picker, default 30 min

> **AUTH-UC-05-STUDENT**
> - Does NOT submit a request through the system
> - Teacher generates reset code directly from course roster (AUTH-UC-07-TEACHER)
> - Student enters reset code on F5 and sets new password on F6
> - Expiry: Fixed 30 minutes (set by system when teacher generates code)
> - Notes: No request token, no status lookup, no approval queue for students

**Errors:**

**AUTH-UC-05-E1** — Reset request denied (RESEARCHER, TEACHER only)
- Trigger: Approver denies the request
- Behavior: Status updates to "denied"; optional reason recorded

**AUTH-UC-05-E2** — Reset request expired (RESEARCHER, TEACHER only)
- Trigger: Pending request window expires before approval
- Behavior: Status updates to "expired"

**AUTH-UC-05-E3** — Reset code invalid/expired/used
- Trigger: Code cannot be redeemed (wrong code, time elapsed, already used)
- Behavior: Error message; researcher/teacher may need to submit new request; student must ask teacher for a new code
- Constraint: AUTH-CN-07, AUTH-CN-08

**AUTH-UC-05-E4** — Reset request blocked (RESEARCHER, TEACHER only)
- Trigger: Existing pending request or rate limit hit
- Behavior: Cannot create duplicate request
- Constraint: AUTH-CN-03

**AUTH-UC-05-E5** — Reset password invalid
- Trigger: New password is weak, mismatched confirm, or same as old
- Behavior: Validation error on the set-new-password step
- Constraint: AUTH-CN-01

**Tests:**

**Backend Unit:**
- test_AUTH_UC_05 (aggregator)
- test_AUTH_UC_05_RESEARCHER
- test_AUTH_UC_05_TEACHER
- test_AUTH_UC_05_STUDENT (code consumption only)
- test_AUTH_UC_05_E1
- test_AUTH_UC_05_E2
- test_AUTH_UC_05_E3
- test_AUTH_UC_05_E4
- test_AUTH_UC_05_E5
- test_AUTH_CN_06 (expiry rules)
- test_AUTH_CN_07 (single-use codes)
- test_AUTH_CN_08 (transactional)
- test_AUTH_CN_09 (cleanup purge of expired/used reset codes)
- test_AUTH_CN_10 (request token, non-student)
- test_AUTH_CN_05_STUDENT (student reset flow excludes request/status queue)

**Frontend Unit:**
- test_AUTH_UC_05_request_form (non-student)
- test_AUTH_UC_05_token_display_warning (non-student)
- test_AUTH_UC_05_reset_code_form
- test_AUTH_UC_05_new_password_form

**Backend Integration:**
- test_AUTH_UC_05_full_reset_flow_teacher
- test_AUTH_UC_05_full_reset_flow_researcher
- test_AUTH_UC_05_teacher_initiated_student_reset

**Frontend Integration:**
- N/A (covered by E2E reset flows)

**Security:**
- N/A (covered by backend reset-token/code and rate-limit tests)

**E2E (Playwright):**
- test_AUTH_UC_05_e2e_reset_request (non-student)
- test_AUTH_UC_05_e2e_reset_complete
- test_AUTH_UC_05_e2e_teacher_student_reset

**System Tests (Black Box):**
- ST-AUTH-UC-05
- ST-AUTH-UC-05-E3

---

#### AUTH-UC-06 — Reset Request Status Lookup

**Roles:** RESEARCHER, TEACHER

**Preconditions:** A request token exists for the user.

**Trigger:** User submits identifier + request token.

**Main Flow:**
1. Validate identifier + request token.
2. Return status: Pending / Approved / Denied / Expired.
3. If approved, user is instructed to enter the reset code (code not shown on this screen).

**Postcondition:** None (read-only).

**Role Coverage:**

> **AUTH-UC-06-RESEARCHER**
> - Behavior: Same as domain flow

> **AUTH-UC-06-TEACHER**
> - Behavior: Same as domain flow

> Students do not use status lookup. Student resets are teacher-initiated (AUTH-UC-07-TEACHER); no request token exists for students.

**Errors:**

**AUTH-UC-06-E1** — Status lookup token invalid
- Trigger: Token not found or identifier mismatch
- Behavior: Generic error (no enumeration)
- Constraint: AUTH-CN-04

**AUTH-UC-06-E2** — Status lookup rate limit
- Trigger: Too many lookup attempts
- Behavior: Cooldown message
- Constraint: AUTH-CN-03

**Tests:**

**Backend Unit:**
- test_AUTH_UC_06 (aggregator)
- test_AUTH_UC_06_RESEARCHER
- test_AUTH_UC_06_TEACHER
- test_AUTH_UC_06_E1
- test_AUTH_UC_06_E2

**Frontend Unit:**
- test_AUTH_UC_06_status_display

**Backend Integration:**
- test_AUTH_UC_06_lookup_flow

**Frontend Integration:**
- N/A (covered by E2E status-lookup flow)

**Security:**
- N/A (covered by backend token + rate-limit tests)

**E2E (Playwright):**
- test_AUTH_UC_06_e2e_status_lookup

**System Tests (Black Box):**
- ST-AUTH-UC-06
- ST-AUTH-UC-06-E1

---

#### AUTH-UC-07 — Reset Code Issuance (Approve/Deny and Teacher-Initiated)

**Roles:** ADMIN, RESEARCHER, TEACHER

**Main Flow (RESEARCHER / ADMIN — Approve request):**
1. Validate permissions (approval chain rules).
2. Validate requested transition from `PENDING` to `APPROVED`.
3. Generate reset code (RESET-...) with expiry per AUTH-CN-06.
4. Approver shares reset code with requester (out-of-band).

**Main Flow (RESEARCHER / ADMIN — Deny request):**
1. Validate permissions.
2. Validate requested transition from `PENDING` to `DENIED`.
3. Mark request denied; optional reason recorded.

**Main Flow (TEACHER — Direct student reset):**
1. Teacher navigates to course roster.
2. Teacher selects a student enrolled in their course.
3. Teacher clicks "Generate Reset Code."
4. System generates reset code (RESET-...) with fixed 30-min expiry (AUTH-CN-06).
5. Teacher shares reset code with student out-of-band (in person, etc.).

**Postcondition:** Reset code generated (approval-based or teacher-initiated) or request denied.

**Reset Chain:**

| Target | Issuer | Trigger | Expiry Config |
|--------|--------|---------|---------------|
| Student | Teacher | Teacher-initiated (direct from course roster) | Fixed 30 min, no picker |
| Teacher | Researcher | Approve pending request | Configurable, date+time picker, default 30 min |
| Researcher | Admin | Approve pending request | Configurable, date+time picker, default 30 min |
| Any | Admin | Approve pending request | Configurable, date+time picker, default 30 min |

**Role Coverage:**

> **AUTH-UC-07-ADMIN**
> - Scope: Can approve any role's reset request
> - Expiry: Configurable via date+time picker, default 30 min
> - Notes: Highest authority in approval chain

> **AUTH-UC-07-RESEARCHER**
> - Scope: Can approve teacher reset requests only
> - Expiry: Configurable via date+time picker, default 30 min

> **AUTH-UC-07-TEACHER**
> - Scope: Can generate reset codes for students enrolled in their courses
> - Trigger: Teacher-initiated from course roster (no pending request required)
> - Expiry: Fixed 30 minutes
> - Notes: No expiry picker; no approval queue; no deny action. Teacher selects student and generates code directly.

**Errors:**

**AUTH-UC-07-E1** — Approval/generation error
- Trigger: Insufficient permission, student not in teacher's course, or request already processed
- Behavior: Error with reason

**Tests:**

**Backend Unit:**
- test_AUTH_UC_07 (aggregator)
- test_AUTH_UC_07_ADMIN
- test_AUTH_UC_07_RESEARCHER
- test_AUTH_UC_07_TEACHER
- test_AUTH_UC_07_E1
- test_AUTH_CN_06 (expiry rules per role)

**Frontend Unit:**
- test_AUTH_UC_07_approval_form (non-student requests)
- test_AUTH_UC_07_expiry_picker_visibility
- test_AUTH_UC_07_teacher_student_roster
- test_AUTH_UC_07_teacher_generate_code

**Backend Integration:**
- test_AUTH_UC_07_approve_flow
- test_AUTH_UC_07_deny_flow
- test_AUTH_UC_07_chain_enforcement
- test_AUTH_UC_07_teacher_direct_student_reset

**Frontend Integration:**
- N/A (covered by E2E approval and teacher-issued reset flows)

**Security:**
- N/A (covered by backend approval-chain and permission tests)

**E2E (Playwright):**
- test_AUTH_UC_07_e2e_approve_teacher_reset
- test_AUTH_UC_07_e2e_deny_request
- test_AUTH_UC_07_e2e_teacher_student_reset

**System Tests (Black Box):**
- ST-AUTH-UC-07
- ST-AUTH-UC-07-E1

---

## 5) Constraints

### AUTH-CN-01 — Password Strength Policy
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character
- **Applies to:** AUTH-UC-04, AUTH-UC-05 (set new password step)
- **Implements:** NFR-SEC-04 (Password Strength Policy) - (user password strength; bootstrap admin covered in ENV-CN-04)

### AUTH-CN-02 — JWT Token Lifetimes
- Access token: session-scoped (invalidated on browser close)
- Refresh token: maximum 24 hours (no sliding window)
- Browser close = session end; refresh does not extend beyond 24h ceiling
- **Applies to:** AUTH-UC-01, AUTH-UC-02, AUTH-UC-03
- **Implements:** NFR-SEC-05 (Session Security)

### AUTH-CN-03 — Rate Limiting
- Per-identifier throttle: 5 failed attempts per 15 minutes per identifier
- Applies to all identifiers equally (existing and non-existing) to prevent enumeration
- No IP-based throttle (school NAT environment)
- Global request throttle as DDoS safety net (infrastructure-level)
- **Applies to:** AUTH-UC-01, AUTH-UC-05, AUTH-UC-06
- **Implements:** NFR-SEC-01 (Rate Limiting Protection) - (per-identifier throttle mechanism; NFR specifies per-IP but school NAT environment requires role-aware identifier keys)

### AUTH-CN-04 — No User Enumeration
- Login failure returns generic error regardless of whether identifier exists
- Rate limiting behavior is identical for existing and non-existing identifiers
- Suspended/disabled accounts may be masked behind generic error
- **Applies to:** AUTH-UC-01, AUTH-UC-06
- **Implements:** NFR-SEC-03 (Enumeration Prevention)

### AUTH-CN-05 — No Email-Based Reset
- Email/SMTP password reset is not available until SMTP infrastructure exists
- Non-student resets use the approval-based flow (AUTH-UC-05 → AUTH-UC-07)
- Student resets are teacher-initiated from course roster (AUTH-UC-07-TEACHER); no request submitted by student
- **Applies to:** AUTH-UC-05

### AUTH-CN-06 — Reset Code Expiry Rules
- Default expiry: 30 minutes for all roles
- Student resets: Fixed 30 minutes, not configurable
- Teacher-issued approvals (for students): Fixed 30 minutes, no expiry picker shown
- Researcher-issued approvals: Configurable via date+time picker, default 30 min
- Admin-issued approvals: Configurable via date+time picker, default 30 min
- **Applies to:** AUTH-UC-05, AUTH-UC-07

### AUTH-CN-07 — Reset Codes Single-Use
- Each reset code can be used exactly once
- Code is invalidated immediately upon successful password reset
- **Applies to:** AUTH-UC-05

### AUTH-CN-08 — Transactional Reset Operations
- Reset code issuance (on approval) and consumption (on password set) must be atomic
- No partial states: either the full operation succeeds or rolls back
- **Applies to:** AUTH-UC-05, AUTH-UC-07
- **Implements:** NFR-REL-01 (Transaction Atomicity for Multi-Record Operations)

### AUTH-CN-09 — Reset Codes Temporary
- Reset codes are not archived or stored long-term
- Expired/used codes are cleaned up (no audit trail for code values)
- **Applies to:** AUTH-UC-05, AUTH-UC-07

### AUTH-CN-10 — Request Token Behavior (Non-Student Only)
- Reset request generates a request token (REQ-...), NOT a reset code
- Token is shown once with a clear warning ("save this token")
- Token is stored in session for quick access during the same browser session
- If session is lost, user must re-enter identifier + request token to check status
- Students do not receive request tokens; student resets are teacher-initiated (AUTH-UC-07-TEACHER)
- **Applies to:** AUTH-UC-05 (RESEARCHER, TEACHER only), AUTH-UC-06

### AUTH-CN-11 — Session Invalidation on Password Change
- Successful password change invalidates ALL existing sessions/tokens
- User must log in again with new password
- This applies to self-service change (AUTH-UC-04) only, not to reset (AUTH-UC-05)
- **Applies to:** AUTH-UC-04
- **Implements:** NFR-SEC-05 (Session Security) - (session invalidation on credential change)

### AUTH-CN-12 — Role-Based Login Identifiers
- STUDENT accounts authenticate with immutable username only
- ADMIN, RESEARCHER, and TEACHER authenticate with username or email
- UI may use a single `Identifier` field, but backend must enforce role-specific rules
- For AUTH-UC-05 / AUTH-UC-06 identifier rules apply to non-student roles only (students do not submit reset requests or check status)
- **Applies to:** AUTH-UC-01, AUTH-UC-05 (non-student), AUTH-UC-06 (non-student)

### AUTH-CN-13 — Student OAuth Disabled
- Google OAuth login is not available for STUDENT accounts
- OAuth endpoints must reject student-role mappings with a clear unsupported-flow error
- **Applies to:** AUTH-UC-02

---

## 6) Approval Chain and State Machines

### Approval / Reset Chain

| Target | Issuer | Trigger | Expiry Config |
|--------|--------|---------|---------------|
| Student | Teacher | Teacher-initiated (direct from course roster, no request) | Fixed 30 min, no picker |
| Teacher | Researcher | Approve pending request | Configurable via picker, default 30 min |
| Researcher | Admin | Approve pending request | Configurable via picker, default 30 min |
| Any | Admin | Approve pending request | Configurable via picker, default 30 min |

### Reset Request States (Non-Student Only)

Students bypass the request state machine entirely. Student resets are teacher-initiated and go directly to code generation.

```
[New] → Pending → Approved → (code generated)
                → Denied
                → Expired (time window elapsed)
```

### Reset Code States

Applies to all roles. For students, codes are generated directly by the teacher (no prior request state).

```
[Generated on approval or teacher action] → Active → Used (password reset successful)
                                                    → Expired (time elapsed)
```

---

## 7) Endpoints (Draft)

### Auth Core

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/auth/sessions` | None | AUTH-UC-01 |
| POST | `/api/v1/auth/sessions/oauth` | None | AUTH-UC-02 |
| POST | `/api/v1/auth/token-exchanges` | Refresh token | AUTH-UC-03 |
| POST | `/api/v1/auth/session-revocations` | Access token | AUTH-UC-08 |

### Password Change

| Method | Path | Auth | UC |
|--------|------|------|----|
| PATCH | `/api/v1/auth/password` | Access token | AUTH-UC-04 |

### Approval-Based Reset (Non-Student)

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/auth/reset-requests` | None | AUTH-UC-05 |
| POST | `/api/v1/auth/reset-request-lookups` | None | AUTH-UC-06 |
| PATCH | `/api/v1/auth/reset-requests/{id}` | Approver | AUTH-UC-07 |

**PATCH payload examples (state-driven):**
- `{ "status": "APPROVED", "expires_at": "2026-02-12T14:30:00Z" }`
- `{ "status": "DENIED", "reason": "request_not_verified" }`

### Teacher-Initiated Student Reset

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/courses/{course_id}/students/{student_user_id}/reset-code` | Teacher | AUTH-UC-07-TEACHER |

Notes:
- Teacher must be the owner of the course and student must be enrolled.
- Backend enforces fixed 30-minute code expiry; no `expires_at` field accepted.

### Reset Code Consumption (All Roles)

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/auth/reset-code-validations` | None | AUTH-UC-05 |
| POST | `/api/v1/auth/password-resets` | None | AUTH-UC-05 |

Notes:
- `/api/v1/auth/sessions/oauth` is for ADMIN/RESEARCHER/TEACHER only; STUDENT attempts must be rejected per AUTH-CN-13.
- Researcher/admin approvals may set optional `expires_at`; default is 30 minutes when omitted.
- Students do not use `/api/v1/auth/reset-requests` or `/api/v1/auth/reset-request-lookups`.

### Admin Panel

| Path | Auth | UC |
|------|------|----|
| `/admin/` | Admin | AUTH-UC-01a-ADMIN |

> Endpoints are proposed and can be adjusted during implementation.

---

## 8) Wireframe Mapping

| UC / Error | Wireframe Screens | Notes |
|------------|-------------------|-------|
| AUTH-UC-01 | B1, B2 | |
| AUTH-UC-01-E1/E2/E3 | B2b, B2c, B2d | |
| AUTH-UC-02 | B3 | |
| AUTH-UC-02-E1/E2 | B3b, B3c | |
| AUTH-UC-04 | B5 | |
| AUTH-UC-04-E1/E2 | B5b, B5c | |
| AUTH-UC-05 (non-student) | F1, F1b | Request submission (RESEARCHER, TEACHER only) |
| AUTH-UC-05 (all) | F5, F6, F7 | Code entry, new password, success (all roles) |
| AUTH-UC-05-E1/E2/E4 | F1c, F1c2, F1c3 | Request errors (non-student only) |
| AUTH-UC-05-E3/E5 | F5b, F6b | Code/password errors (all roles) |
| AUTH-UC-06 | F1d, F1e, B2-rs | Non-student only (status lookup) |
| AUTH-UC-07-TEACHER | F2, F2b | Course roster → generate student reset code |
| AUTH-UC-07-RESEARCHER | F3, F3b | Approve/deny teacher requests |
| AUTH-UC-07-ADMIN | F4, F4b | Approve/deny any requests |
| AUTH-UC-07-E1 | F3c, F4c | Approval errors (non-student requests only) |
| AUTH-UC-08 | B4 | |
| AUTH-UC-01a-ADMIN | B6 | |

> Screen IDs reference the Figma Make wireframes. Verify via official Figma MCP against file `WGyIhW6EpOwfvVH3idkEtG`.

---

## 9) Shared Code Generation (Implementation Note)

Auth reset codes use the same **core code generator** as registration codes, but with a **different policy profile**. This keeps generation logic consistent while preserving domain-specific behavior.

- **Registration policy (REG):** persistent storage, multi-use, revokable/archivable, course linkage
- **Reset policy (AUTH):** short-lived, single-use, not archived, request-token based lookup (non-student) or teacher-initiated (student)

This is an implementation detail; requirements remain scoped under AUTH and REG.
