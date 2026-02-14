# FR-01 Authentication (AUTH) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | READY |
| **Date** | 2026-02-07 |
| **Domain** | AUTH |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER, STUDENT |
| **Related Issues** | #29 (code-gated auth/registration), #28 (role hierarchy/sudo) |

---

## 1) Scope

### In Scope
- Password login for all roles
- OAuth login for users with code-gated accounts
- Token refresh (backend-only)
- Self-service password change
- Approval-based password reset (no SMTP)
- Reset request status lookup (request token)
- Reset request state transitions (approve/deny by teacher/researcher/admin)
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
| TEACHER | User role | Can approve student resets |
| STUDENT | User role | Can request reset; cannot approve |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| AUTH-US-01 | ALL | As an admin, researcher, teacher, or student I can log in with my email and password so that I can access the application. |
| AUTH-US-01a-ADMIN | ADMIN | As an admin I can log in to the Django admin panel so that I can manage the system. |
| AUTH-US-02 | ALL | As an admin, researcher, teacher, or student I can log in with Google OAuth so that I can access the application without a password. |
| AUTH-US-03 | ALL | As an admin, researcher, teacher, or student I can have my session tokens refreshed so that I stay authenticated during active use. |
| AUTH-US-04 | ALL | As an admin, researcher, teacher, or student I can change my password so that I can keep my account secure. |
| AUTH-US-05 | RESEARCHER, TEACHER, STUDENT | As a researcher, teacher, or student I can request an approval-based password reset so that I can regain access to my account without email. |
| AUTH-US-06 | RESEARCHER, TEACHER, STUDENT | As a researcher, teacher, or student I can look up the status of my reset request so that I know whether it has been approved, denied, or is still pending. |
| AUTH-US-07 | ADMIN, RESEARCHER, TEACHER | As an admin, researcher, or teacher I can approve or deny password reset requests so that users under my scope can regain account access. |
| AUTH-US-08 | ALL | As an admin, researcher, teacher, or student I can log out so that my session is securely terminated. |

---

## 4) Use Cases

### Core Authentication

#### AUTH-UC-01 — Password Login

**Roles:** ALL

**Preconditions:** User account exists; account not disabled/suspended.

**Trigger:** User submits email + password on login page.

**Main Flow:**
1. User enters email + password.
2. System validates credentials.
3. On success, return access token/session and role.
4. User is redirected to dashboard.

**Postcondition:** Active session established.

**Role Coverage:**

> **AUTH-UC-01-ALL**
> - Behavior: Identical flow for ADMIN, RESEARCHER, TEACHER, STUDENT
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
- Trigger: Too many failed attempts on same email
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

**Frontend Unit:**
- test_AUTH_UC_01_form_validation
- test_AUTH_UC_01_error_display

**Integration:**
- test_AUTH_UC_01_login_flow
- test_AUTH_UC_01a_admin_login_flow

**E2E (Playwright):**
- test_AUTH_UC_01_e2e_login
- test_AUTH_UC_01a_e2e_admin_login

---

#### AUTH-UC-02 — OAuth Login

**Roles:** ALL

**Preconditions:** Account exists and was created via code-gated registration (FR-02 REG).

**Trigger:** User selects "Continue with Google."

**Main Flow:**
1. User completes OAuth provider flow.
2. System validates OAuth token and account eligibility.
3. Session token issued; user redirected to dashboard.

**Postcondition:** Active session established.

**Role Coverage:**

> **AUTH-UC-02-ALL**
> - Behavior: Identical flow for ADMIN, RESEARCHER, TEACHER, STUDENT

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
- test_AUTH_UC_02_STUDENT
- test_AUTH_UC_02_E1
- test_AUTH_UC_02_E2

**Frontend Unit:**
- test_AUTH_UC_02_oauth_button

**Integration:**
- test_AUTH_UC_02_oauth_flow

**E2E (Playwright):**
- test_AUTH_UC_02_e2e_oauth_login

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

**E2E (Playwright):**
- test_AUTH_UC_08_e2e_logout

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

**Integration:**
- test_AUTH_UC_04_change_password_flow

**E2E (Playwright):**
- test_AUTH_UC_04_e2e_change_password

---

### Approval-Based Password Reset

#### AUTH-UC-05 — Request Password Reset

**Roles:** RESEARCHER, TEACHER, STUDENT

**Preconditions:** User has a valid account.

**Trigger:** User requests reset via login screen.

**Main Flow:**
1. User submits reset request (email).
2. System creates pending request and generates request token (REQ-...).
3. Request token is shown once with warning; stored in session.
4. Approver reviews request (AUTH-UC-07).
5. If approved, a reset code (RESET-...) is generated.
6. User enters reset code and sets new password.
7. No auto-login; user returns to login.

**Postcondition:** Password reset if approved; otherwise request remains denied/expired.

**Role Coverage:**

> **AUTH-UC-05-RESEARCHER**
> - Requests reset from: Admin
> - Expiry: Configurable via date+time picker, default 30 min
> - Notes: Highest user role; only admin can approve

> **AUTH-UC-05-TEACHER**
> - Requests reset from: Researcher
> - Expiry: Configurable via date+time picker, default 30 min

> **AUTH-UC-05-STUDENT**
> - Requests reset from: Teacher
> - Expiry: Fixed 30 minutes, no picker
> - Notes: Teacher UI does not expose expiry configuration

**Errors:**

**AUTH-UC-05-E1** — Reset request denied
- Trigger: Approver denies the request
- Behavior: Status updates to "denied"; optional reason recorded

**AUTH-UC-05-E2** — Reset request expired
- Trigger: Pending request window expires before approval
- Behavior: Status updates to "expired"

**AUTH-UC-05-E3** — Reset code invalid/expired/used
- Trigger: Code cannot be redeemed (wrong code, time elapsed, already used)
- Behavior: Error message; user may need to submit new request
- Constraint: AUTH-CN-07, AUTH-CN-08

**AUTH-UC-05-E4** — Reset request blocked
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
- test_AUTH_UC_05_STUDENT
- test_AUTH_UC_05_E1
- test_AUTH_UC_05_E2
- test_AUTH_UC_05_E3
- test_AUTH_UC_05_E4
- test_AUTH_UC_05_E5
- test_AUTH_CN_06 (expiry rules)
- test_AUTH_CN_07 (single-use codes)
- test_AUTH_CN_08 (transactional)
- test_AUTH_CN_09 (no archival)
- test_AUTH_CN_10 (request token)

**Frontend Unit:**
- test_AUTH_UC_05_request_form
- test_AUTH_UC_05_token_display_warning
- test_AUTH_UC_05_reset_code_form
- test_AUTH_UC_05_new_password_form

**Integration:**
- test_AUTH_UC_05_full_reset_flow
- test_AUTH_UC_05_approval_chain_student
- test_AUTH_UC_05_approval_chain_teacher
- test_AUTH_UC_05_approval_chain_researcher

**E2E (Playwright):**
- test_AUTH_UC_05_e2e_reset_request
- test_AUTH_UC_05_e2e_reset_complete

---

#### AUTH-UC-06 — Reset Request Status Lookup

**Roles:** RESEARCHER, TEACHER, STUDENT

**Preconditions:** A request token exists for the user.

**Trigger:** User submits email + request token.

**Main Flow:**
1. Validate email + request token.
2. Return status: Pending / Approved / Denied / Expired.
3. If approved, user is instructed to enter the reset code (code not shown on this screen).

**Postcondition:** None (read-only).

**Role Coverage:**

> **AUTH-UC-06-RESEARCHER**
> - Behavior: Same as domain flow

> **AUTH-UC-06-TEACHER**
> - Behavior: Same as domain flow

> **AUTH-UC-06-STUDENT**
> - Behavior: Same as domain flow

**Errors:**

**AUTH-UC-06-E1** — Status lookup token invalid
- Trigger: Token not found or email mismatch
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
- test_AUTH_UC_06_STUDENT
- test_AUTH_UC_06_E1
- test_AUTH_UC_06_E2

**Frontend Unit:**
- test_AUTH_UC_06_status_display

**Integration:**
- test_AUTH_UC_06_lookup_flow

**E2E (Playwright):**
- test_AUTH_UC_06_e2e_status_lookup

---

#### AUTH-UC-07 — Reset Request State Transition (Approve/Deny)

**Roles:** ADMIN, RESEARCHER, TEACHER

**Preconditions:** Pending reset request exists within approver's scope.

**Trigger:** Approver submits a request status update (`APPROVED` or `DENIED`).

**Main Flow (Approve):**
1. Validate permissions (approval chain rules).
2. Validate requested transition from `PENDING` to `APPROVED`.
3. Generate reset code (RESET-...) with expiry per AUTH-CN-06.
4. Approver shares reset code with requester (out-of-band).

**Main Flow (Deny):**
1. Validate permissions.
2. Validate requested transition from `PENDING` to `DENIED`.
3. Mark request denied; optional reason recorded.

**Postcondition:** Request approved (code generated) or denied.

**Approval Chain:**

| Requester | Approver | Expiry Config |
|-----------|----------|---------------|
| Student | Teacher | Fixed 30 min, no picker |
| Teacher | Researcher | Configurable, date+time picker, default 30 min |
| Researcher | Admin | Configurable, date+time picker, default 30 min |
| Any | Admin | Configurable, date+time picker, default 30 min |

**Role Coverage:**

> **AUTH-UC-07-ADMIN**
> - Scope: Can approve any role's reset request
> - Expiry: Configurable via date+time picker, default 30 min
> - Notes: Highest authority in approval chain

> **AUTH-UC-07-RESEARCHER**
> - Scope: Can approve teacher reset requests only
> - Expiry: Configurable via date+time picker, default 30 min

> **AUTH-UC-07-TEACHER**
> - Scope: Can approve student reset requests only
> - Expiry: Fixed 30 minutes
> - Notes: No expiry picker exposed in UI

**Errors:**

**AUTH-UC-07-E1** — Approval error
- Trigger: Insufficient permission (wrong chain level) or request already processed
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
- test_AUTH_UC_07_approval_form
- test_AUTH_UC_07_expiry_picker_visibility

**Integration:**
- test_AUTH_UC_07_approve_flow
- test_AUTH_UC_07_deny_flow
- test_AUTH_UC_07_chain_enforcement

**E2E (Playwright):**
- test_AUTH_UC_07_e2e_approve_student_reset
- test_AUTH_UC_07_e2e_deny_request

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
- Per-email throttle: 5 failed attempts per 15 minutes per email
- Applies to all emails equally (existing and non-existing) to prevent enumeration
- No IP-based throttle (school NAT environment)
- Global request throttle as DDoS safety net (infrastructure-level)
- **Applies to:** AUTH-UC-01, AUTH-UC-05, AUTH-UC-06
- **Implements:** NFR-SEC-01 (Rate Limiting Protection) - (per-email throttle mechanism; NFR specifies per-IP but school NAT environment requires per-email)

### AUTH-CN-04 — No User Enumeration
- Login failure returns generic error regardless of whether email exists
- Rate limiting behavior is identical for existing and non-existing emails
- Suspended/disabled accounts may be masked behind generic error
- **Applies to:** AUTH-UC-01, AUTH-UC-06
- **Implements:** NFR-SEC-03 (Enumeration Prevention)

### AUTH-CN-05 — No Email-Based Reset
- Email/SMTP password reset is not available until SMTP infrastructure exists
- All resets go through the approval-based flow (AUTH-UC-05 → AUTH-UC-07)
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

### AUTH-CN-10 — Request Token Behavior
- Reset request generates a request token (REQ-...), NOT a reset code
- Token is shown once with a clear warning ("save this token")
- Token is stored in session for quick access during the same browser session
- If session is lost, user must re-enter email + request token to check status
- **Applies to:** AUTH-UC-05, AUTH-UC-06

### AUTH-CN-11 — Session Invalidation on Password Change
- Successful password change invalidates ALL existing sessions/tokens
- User must log in again with new password
- This applies to self-service change (AUTH-UC-04) only, not to reset (AUTH-UC-05)
- **Applies to:** AUTH-UC-04
- **Implements:** NFR-SEC-05 (Session Security) - (session invalidation on credential change)

---

## 6) Approval Chain and State Machines

### Approval Chain

| Requester | Approver | Expiry Config |
|-----------|----------|---------------|
| Student | Teacher | Fixed 30 min, no picker |
| Teacher | Researcher | Configurable via picker, default 30 min |
| Researcher | Admin | Configurable via picker, default 30 min |
| Any | Admin | Configurable via picker, default 30 min |

### Reset Request States

```
[New] → Pending → Approved → (code generated)
                → Denied
                → Expired (time window elapsed)
```

### Reset Code States

```
[Generated on approval] → Active → Used (password reset successful)
                                  → Expired (time elapsed)
```

---

## 7) Endpoints (Draft)

### Auth Core

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/auth/login` | None | AUTH-UC-01 |
| POST | `/api/v1/auth/oauth/google` | None | AUTH-UC-02 |
| POST | `/api/v1/auth/refresh` | Refresh token | AUTH-UC-03 |
| POST | `/api/v1/auth/logout` | Access token | AUTH-UC-08 |

### Password Change

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/auth/password/change` | Access token | AUTH-UC-04 |

### Approval-Based Reset

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/auth/reset-requests` | None | AUTH-UC-05 |
| POST | `/api/v1/auth/reset-requests/status` | None | AUTH-UC-06 |
| PATCH | `/api/v1/auth/reset-requests/{id}` | Approver | AUTH-UC-07 |
| POST | `/api/v1/auth/reset-codes/verify` | None | AUTH-UC-05 |
| POST | `/api/v1/auth/reset-codes/complete` | None | AUTH-UC-05 |

**PATCH payload examples (state-driven):**
- `{ "status": "APPROVED", "expires_at": "2026-02-12T14:30:00Z" }`
- `{ "status": "DENIED", "reason": "request_not_verified" }`

Notes:
- Teacher approvals for student requests do not accept custom expiry; backend enforces fixed 30-minute code expiry.
- Researcher/admin approvals may set optional `expires_at`; default is 30 minutes when omitted.

### Admin Panel

| Path | Auth | UC |
|------|------|----|
| `/admin/` | Admin | AUTH-UC-01a-ADMIN |

> Endpoints are proposed and can be adjusted during implementation.

---

## 8) Wireframe Mapping

| UC / Error | Wireframe Screens |
|------------|-------------------|
| AUTH-UC-01 | B1, B2 |
| AUTH-UC-01-E1/E2/E3 | B2b, B2c, B2d |
| AUTH-UC-02 | B3 |
| AUTH-UC-02-E1/E2 | B3b, B3c |
| AUTH-UC-04 | B5 |
| AUTH-UC-04-E1/E2 | B5b, B5c |
| AUTH-UC-05 | F1, F1b, F5, F6, F7 |
| AUTH-UC-05-E1/E2/E3/E4/E5 | F1c, F1c2, F5b, F1c3, F6b |
| AUTH-UC-06 | F1d, F1e, B2-rs |
| AUTH-UC-07-TEACHER | F2, F2b |
| AUTH-UC-07-RESEARCHER | F3, F3b |
| AUTH-UC-07-ADMIN | F4, F4b |
| AUTH-UC-07-E1 | F2c, F3c, F4c |
| AUTH-UC-08 | B4 |
| AUTH-UC-01a-ADMIN | B6 |

> Screen IDs reference the Figma Make wireframes. Verify via official Figma MCP against file `WGyIhW6EpOwfvVH3idkEtG`.

---

## 9) Shared Code Generation (Implementation Note)

Auth reset codes use the same **core code generator** as registration codes, but with a **different policy profile**. This keeps generation logic consistent while preserving domain-specific behavior.

- **Registration policy (REG):** persistent storage, multi-use, revokable/archivable, course linkage
- **Reset policy (AUTH):** short-lived, single-use, not archived, request-token based lookup

This is an implementation detail; requirements remain scoped under AUTH and REG.
