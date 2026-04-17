# FR-03 Role Hierarchy and Sudo (SUDO) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | COMPLETE |
| **Date** | 2026-02-14 |
| **Domain** | SUDO |
| **Applies To** | ADMIN (system role), RESEARCHER |
| **Related Issues** | #28 (role hierarchy/sudo) |
| **Dependencies** | FR-12 ENV (admin bootstrap for is_staff) |

---

## 1) Scope

### In Scope
- Role hierarchy definition: ADMIN (system role via `is_staff`) > RESEARCHER > TEACHER > STUDENT
- Admin as a system role (`is_staff=True`) separate from user roles (RESEARCHER, TEACHER, STUDENT)
- SudoGrant lifecycle: grant, update, revoke elevated permissions for researchers
- Permission evaluation: role-based + sudo-based authorization checks across all user management operations
- Escalation prevention: subset-only delegation, admin-only `can_grant_sudo`, no cross-space escalation
- Permission enum: CREATE_TEACHER, CREATE_STUDENT, CREATE_RESEARCHER_CODES, EDIT_USER, DELETE_USER, ISSUE_STUDENT_RESET_CODE, ISSUE_RESEARCHER_RESET_CODE, VIEW_IDENTIFIABLE_VIZ, EXPORT_IDENTIFIABLE
- Issuer-based reset authority expansion for researchers via sudo flags (no reset-request workflow)
- Researcher capabilities without sudo (read-only data oversight)

### Out of Scope
- Researcher read access to other FR domains (courses FR-05, assignment templates FR-06, etc.) — those FRs define their own permission rules referencing the role hierarchy
- Audit logging for sudo operations (future enhancement)
- Grant expiration / time-bounded sudo (future enhancement)
- System-wide grant listing endpoint for admin dashboard (future enhancement)
- Delegation chain tracking / grant ancestry (future enhancement)

### Core Intent
- Define explicit role hierarchy with admin as a system role separate from user roles.
- Enable fine-grained permission delegation via SudoGrant without full admin access.
- Prevent privilege escalation through subset-only delegation and non-transitive can_grant_sudo.

---

## 2) Actors

| Role | Type | Notes |
|------|------|-------|
| ADMIN | System role | `is_staff=True`; can grant any permissions to researchers, set `can_grant_sudo=True`, revoke any grant |
| RESEARCHER | User role | Highest user role; receives sudo via SudoGrant; can delegate subset of own permissions when `can_grant_sudo=True` |
| TEACHER | User role | Not directly involved in sudo operations; affected by sudo-elevated user management |
| STUDENT | User role | Not directly involved in sudo operations; affected by sudo-elevated user management |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

**System role vs. user role:**
- ADMIN is determined by `User.is_staff=True` on the User model. It is not a value in the `Role` enum and does not appear in the `user_roles` table.
- RESEARCHER, TEACHER, STUDENT are user roles stored in the `user_roles` table via the `Role` enum.
- A user can be both an admin (`is_staff=True`) and hold a user role, but admin status is always checked separately via `is_staff`.

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| SUDO-US-01 | ADMIN | As an admin I can grant sudo permissions to a researcher so they can perform specific elevated user management actions without full admin access. |
| SUDO-US-02 | ADMIN, RESEARCHER | As an admin I can revoke any sudo grant, and as a researcher I can revoke sudo grants I created, so that elevated permissions can be removed when no longer needed. |
| SUDO-US-03 | RESEARCHER | As a sudoed researcher with `can_grant_sudo` I can delegate a subset of my own permissions to another researcher so they can share user management responsibilities. |
| SUDO-US-04 | RESEARCHER | As a sudoed researcher I can perform elevated user management actions (create, edit, delete users) according to my granted permissions so that I can assist with platform operations without admin access. |

---

## 4) Use Cases

### Sudo Grant Management

#### SUDO-UC-01 — Grant Sudo Permissions

**Roles:** ADMIN, RESEARCHER (with `can_grant_sudo=True`)

**Preconditions:** Grantee exists and has RESEARCHER role.

**Trigger:** Admin or authorized researcher submits grant request.

**Main Flow:**
1. Granter specifies target researcher, permissions list, and optionally `can_grant_sudo`.
2. System validates grantee has RESEARCHER role.
3. System validates granter authorization (admin or researcher with `can_grant_sudo`).
4. System validates escalation prevention rules (SUDO-CN-03, SUDO-CN-05).
5. System validates all permission values against SudoPermission enum (SUDO-CN-06).
6. If grantee already has a SudoGrant, update existing record (SUDO-CN-08).
7. If grantee has no SudoGrant, create new record.
8. Return grant ID.

**Postcondition:** SudoGrant created or updated; grantee can now perform elevated actions per their permissions list.

**Role Coverage:**

> **SUDO-UC-01-ADMIN**
> - Can grant any combination of SudoPermission values
> - Can set `can_grant_sudo=True`
> - No restrictions on which permissions to grant

> **SUDO-UC-01-RESEARCHER**
> - Must have existing SudoGrant with `can_grant_sudo=True`
> - Can only grant permissions they themselves hold (subset check)
> - Cannot set `can_grant_sudo=True` (admin only, SUDO-CN-05)
> - Cannot delegate `CREATE_RESEARCHER_CODES` even if they hold it (admin-only delegation for researcher invite capability)

**Errors:**

**SUDO-UC-01-E1** — Grantee not a researcher
- Trigger: Target user does not have RESEARCHER role
- Behavior: 400 error with "must have RESEARCHER role"

**SUDO-UC-01-E2** — Escalation attempt
- Trigger: Researcher granter tries to grant permissions they don't hold
- Behavior: 403 error with "Cannot grant permissions you don't hold"
- Constraint: SUDO-CN-03

**SUDO-UC-01-E3** — Researcher attempts `can_grant_sudo=True`
- Trigger: Researcher granter sets `can_grant_sudo=True`
- Behavior: 403 error with "Only admins can set can_grant_sudo=True"
- Constraint: SUDO-CN-05

**SUDO-UC-01-E4** — Granter not authorized
- Trigger: Researcher without `can_grant_sudo` attempts to grant
- Behavior: 403 error with "can_grant_sudo=False"

**SUDO-UC-01-E5** — Missing required fields
- Trigger: `user_id` not provided
- Behavior: 400 error

**SUDO-UC-01-E6** — User not found
- Trigger: `user_id` does not match any user
- Behavior: 404 error

**SUDO-UC-01-E7** — Invalid permission values
- Trigger: Permissions list contains values not in SudoPermission enum
- Behavior: Validation error from model `clean()`
- Constraint: SUDO-CN-06

**SUDO-UC-01-E8** — Non-researcher/non-admin role attempts grant
- Trigger: Teacher or student calls grant endpoint
- Behavior: 403 from `IsResearcherOrAdmin` permission class

**Tests (representative):** test_SUDO_UC_01, test_SUDO_UC_01_ADMIN, test_SUDO_UC_01_RESEARCHER, test_SUDO_UC_01_E1–E8, test_SUDO_CN_03, test_SUDO_CN_05, test_SUDO_CN_06, test_SUDO_CN_08; ST-SUDO-UC-01, ST-SUDO-UC-01-E2

---

#### SUDO-UC-02 — Revoke Sudo Permissions

**Roles:** ADMIN, RESEARCHER

**Preconditions:** SudoGrant exists.

**Trigger:** Admin or grant creator submits revoke request.

**Main Flow:**
1. System looks up SudoGrant by ID.
2. System validates revoker authorization.
3. System deletes the SudoGrant record.
4. Grantee immediately loses all elevated permissions.

**Postcondition:** SudoGrant deleted; grantee reverts to base researcher permissions.

**Role Coverage:**

> **SUDO-UC-02-ADMIN**
> - Can revoke any SudoGrant regardless of who created it

> **SUDO-UC-02-RESEARCHER**
> - Can only revoke SudoGrants where `granted_by` is themselves

**Errors:**

**SUDO-UC-02-E1** — Grant not found
- Trigger: `grant_id` does not match any SudoGrant
- Behavior: 404 error

**SUDO-UC-02-E2** — Unauthorized revocation
- Trigger: Researcher tries to revoke a grant they didn't create
- Behavior: 403 error with "You can only revoke grants you created"

**SUDO-UC-02-E3** — Non-researcher/non-admin role attempts revoke
- Trigger: Teacher or student calls revoke endpoint
- Behavior: 403 from `IsResearcherOrAdmin` permission class

**Tests (representative):** test_SUDO_UC_02, test_SUDO_UC_02_ADMIN, test_SUDO_UC_02_RESEARCHER, test_SUDO_UC_02_E1–E3; ST-SUDO-UC-02

---

### Permission Evaluation

#### SUDO-UC-03 — Sudo-Elevated User Creation

**Roles:** ADMIN, RESEARCHER (with sudo), TEACHER

**Preconditions:** Creator is authenticated; target role is within creation scope.

**Description:** This use case defines how sudo permissions affect user creation authorization. The `can_create_user` function evaluates the creator's role and sudo permissions to determine if the requested user creation is allowed.

**Permission Matrix:**

| Creator | Can Create RESEARCHER | Can Create TEACHER | Can Create STUDENT |
|---------|----------------------|-------------------|-------------------|
| ADMIN (`is_staff`) | Yes | Yes | No |
| RESEARCHER + sudo `CREATE_TEACHER` | No | Yes | No |
| RESEARCHER + sudo `CREATE_STUDENT` | No | No | Yes |
| RESEARCHER (no sudo) | No | No | No |
| TEACHER | No | No | Yes |
| STUDENT | No | No | No |

**Role Coverage:**

> **SUDO-UC-03-ADMIN**
> - Can create RESEARCHER and TEACHER accounts
> - Cannot create STUDENT accounts directly (use teacher or sudoed researcher)

> **SUDO-UC-03-RESEARCHER**
> - Without sudo: Cannot create any users
> - With `CREATE_TEACHER`: Can create teacher accounts
> - With `CREATE_STUDENT`: Can create student accounts

> **SUDO-UC-03-TEACHER**
> - Can create STUDENT accounts only

**Errors:**

**SUDO-UC-03-E1** — Insufficient permission
- Trigger: Creator lacks the necessary role or sudo permission for the requested target role
- Behavior: 403 Forbidden

**Tests (representative):** test_SUDO_UC_03, test_SUDO_UC_03_ADMIN, test_SUDO_UC_03_RESEARCHER, test_SUDO_UC_03_RESEARCHER_CREATE_TEACHER, test_SUDO_UC_03_RESEARCHER_CREATE_STUDENT, test_SUDO_UC_03_TEACHER, test_SUDO_UC_03_E1; ST-SUDO-UC-03

---

#### SUDO-UC-04 — Sudo-Elevated User Edit

**Roles:** ADMIN, RESEARCHER (with sudo), TEACHER

**Preconditions:** Editor is authenticated; target user exists.

**Description:** This use case defines how sudo permissions affect user editing authorization. The `can_edit_user` function evaluates the editor's role and sudo permissions.

**Permission Matrix:**

| Editor | Can Edit RESEARCHER | Can Edit TEACHER | Can Edit STUDENT |
|--------|-------------------|-----------------|-----------------|
| ADMIN (`is_staff`) | Yes | Yes | No |
| RESEARCHER + sudo `EDIT_USER` | No | Yes | Yes |
| RESEARCHER (no sudo) | No | No | No |
| TEACHER | No | No | Own students only |
| STUDENT | No | No | No |

**Additional Rules:**
- Admin/staff accounts (`is_staff=True`) cannot be edited through role-assignment flows regardless of editor's permissions (SUDO-CN-04)
- Teacher ownership is determined via enrollment: teacher must own a course the student is enrolled in

**Role Coverage:**

> **SUDO-UC-04-ADMIN**
> - Can edit RESEARCHER and TEACHER accounts
> - Cannot edit admin accounts (SUDO-CN-04)

> **SUDO-UC-04-RESEARCHER**
> - Without sudo: Cannot edit any users
> - With `EDIT_USER`: Can edit TEACHER and STUDENT accounts

> **SUDO-UC-04-TEACHER**
> - Can edit STUDENT accounts enrolled in their courses only

**Errors:**

**SUDO-UC-04-E1** — Insufficient permission
- Trigger: Editor lacks the necessary role or sudo permission for the target user
- Behavior: 403 Forbidden

**SUDO-UC-04-E2** — Admin target blocked
- Trigger: Any user attempts to edit an admin account through role-assignment flows
- Behavior: 403 Forbidden
- Constraint: SUDO-CN-04

**Tests (representative):** test_SUDO_UC_04, test_SUDO_UC_04_ADMIN, test_SUDO_UC_04_RESEARCHER_EDIT_USER, test_SUDO_UC_04_TEACHER, test_SUDO_UC_04_E1, test_SUDO_UC_04_E2; ST-SUDO-UC-04

---

#### SUDO-UC-05 — Sudo-Elevated User Deletion

**Roles:** ADMIN, RESEARCHER (with sudo), TEACHER

**Preconditions:** Deleter is authenticated; target user exists.

**Description:** This use case defines how sudo permissions affect user deletion authorization. The `can_delete_user` function evaluates the deleter's role and sudo permissions.

**Permission Matrix:**

| Deleter | Can Delete RESEARCHER | Can Delete TEACHER | Can Delete STUDENT |
|---------|----------------------|-------------------|-------------------|
| ADMIN (`is_staff`) | Yes | Yes | No |
| RESEARCHER + sudo `DELETE_USER` | No | Yes | Yes |
| RESEARCHER (no sudo) | No | No | No |
| TEACHER | No | No | Own students only |
| STUDENT | No | No | No |

**Role Coverage:**

> **SUDO-UC-05-ADMIN**
> - Can delete RESEARCHER and TEACHER accounts

> **SUDO-UC-05-RESEARCHER**
> - Without sudo: Cannot delete any users
> - With `DELETE_USER`: Can delete TEACHER and STUDENT accounts

> **SUDO-UC-05-TEACHER**
> - Can delete STUDENT accounts enrolled in their courses only

**Errors:**

**SUDO-UC-05-E1** — Insufficient permission
- Trigger: Deleter lacks the necessary role or sudo permission for the target user
- Behavior: 403 Forbidden

**Tests (representative):** test_SUDO_UC_05, test_SUDO_UC_05_ADMIN, test_SUDO_UC_05_RESEARCHER_DELETE_USER, test_SUDO_UC_05_TEACHER, test_SUDO_UC_05_E1; ST-SUDO-UC-05

---

## 5) Constraints

### SUDO-CN-01 — Role Hierarchy
- Application roles follow a strict hierarchy: ADMIN > RESEARCHER > TEACHER > STUDENT
- ADMIN is a system role determined by `User.is_staff=True`, not a value in the `Role` enum
- RESEARCHER, TEACHER, STUDENT are user roles stored in `user_roles` table
- `primary_role()` returns the highest user role: RESEARCHER > TEACHER > STUDENT; returns `"ADMIN"` for `is_staff` users
- A user has exactly one user role at a time via `set_single_role()`
- **Applies to:** All use cases
- **Implements:** NFR-PRIV-01 (FERPA-Compliant Data Access Controls) — role hierarchy ensures users can only access data appropriate to their role level

### SUDO-CN-02 — Default-Deny Permissions
- A researcher without a SudoGrant has zero elevated permissions
- Researcher base capabilities (without sudo): read-only data oversight, assignment template management
- Elevated capabilities (user management) require explicit SudoGrant with specific permissions
- **Applies to:** SUDO-UC-01, SUDO-UC-03, SUDO-UC-04, SUDO-UC-05

### SUDO-CN-03 — No Privilege Escalation
- A researcher with `can_grant_sudo=True` can only delegate permissions they themselves hold
- The granted permissions must be a subset of the granter's own permissions list
- `CREATE_RESEARCHER_CODES` is non-delegable by researchers, even when present in the granter's own permissions
- Attempting to grant a permission the granter does not hold results in a 403 error
- **Applies to:** SUDO-UC-01
- **Implements:** NFR-SEC-08 (Principle of Least Privilege)

> **Policy:** ISSUE_STUDENT_RESET_CODE and ISSUE_RESEARCHER_RESET_CODE are delegable. They are NOT members of NON_DELEGABLE_PERMISSIONS. Only CREATE_RESEARCHER_CODES is non-delegable by researchers. A researcher with `can_grant_sudo=True` who holds either reset permission can delegate it to another researcher; the recipient can USE the permission but cannot delegate further unless they also have `can_grant_sudo=True`. Applies to: SUDO-CN-03, SUDO-UC-01-RESEARCHER.

### SUDO-CN-04 — Admin/User Space Separation
- Sudo permissions operate exclusively within the user role space (RESEARCHER, TEACHER, STUDENT)
- A sudoed researcher cannot create, modify, or delete admin accounts (`is_staff=True`)
- Admin accounts (`is_staff=True`) are protected from role-assignment edit flows
- Admin creation is bootstrapped via environment (ENV-UC-02), not through user management endpoints
- **Applies to:** SUDO-UC-03, SUDO-UC-04, SUDO-UC-05

### SUDO-CN-05 — `can_grant_sudo` Admin-Only
- Only an admin (`is_staff=True`) can set `can_grant_sudo=True` on a SudoGrant
- This flag is never transitive: a researcher with `can_grant_sudo=True` cannot give another researcher the ability to grant sudo
- A researcher attempting to set `can_grant_sudo=True` receives a 403 error
- **Applies to:** SUDO-UC-01

### SUDO-CN-06 — Permission Enum Validation
- All permission values in a SudoGrant must be valid `SudoPermission` enum choices
- The `SudoGrant.clean()` method validates the `permissions` JSONField against the enum
- Invalid permission values result in a `ValidationError`
- **Applies to:** SUDO-UC-01

### SUDO-CN-07 — OneToOne Grant Per Researcher
- Each researcher can have at most one SudoGrant (enforced via `OneToOneField`)
- Granting sudo to a researcher who already has a grant updates the existing record
- **Applies to:** SUDO-UC-01

### SUDO-CN-08 — Grant Update Semantics
- Re-granting sudo to a researcher with an existing SudoGrant replaces the permissions list and updates `granted_by`
- The grant ID remains the same (update, not delete + create)
- This supports permission modification without requiring explicit revoke-then-regranting
- **Applies to:** SUDO-UC-01

### SUDO-CN-09 — Permission Scope Definitions
- Each `SudoPermission` value unlocks specific elevated capabilities:

| Permission | Capability | Affected Endpoints |
|-----------|-----------|-------------------|
| `CREATE_TEACHER` | Create teacher accounts | `POST /api/v1/users` |
| `CREATE_STUDENT` | Create student accounts; generate student registration codes | `POST /api/v1/users`, `POST /api/v1/codes` |
| `CREATE_RESEARCHER_CODES` | Generate researcher registration codes | `POST /api/v1/codes` (`codeType=RESEARCHER`) |
| `EDIT_USER` | Edit teacher and student accounts | `PATCH /api/v1/users/{user_id}` |
| `DELETE_USER` | Delete teacher and student accounts | `DELETE /api/v1/users/{user_id}` |
| `ISSUE_STUDENT_RESET_CODE` | Allow researcher to issue reset codes for students (outside teacher-owned course flow) | `POST /api/v1/auth/password-reset-codes` (target role STUDENT) |
| `ISSUE_RESEARCHER_RESET_CODE` | Allow researcher to issue reset codes for other researchers | `POST /api/v1/auth/password-reset-codes` (target role RESEARCHER) |
| `VIEW_IDENTIFIABLE_VIZ` | Allow researcher to view identifiable fields (courseId, courseName, assignmentId, assignmentTemplateTitle) in visualization responses | `GET /api/v1/visualizations/*` (FR-09 VIZ-CN-01) |
| `EXPORT_IDENTIFIABLE` | Allow researcher to export identifiable fields (studentId, studentName, courseId, etc.) in CSV exports when `identifiable=true` query param is set | `GET /api/v1/exports/*` (FR-10 EXP-CN-01) |

- Default role behavior (no sudo permission required): researcher can issue teacher reset codes; teacher can issue student reset codes in owned courses.
- **Applies to:** SUDO-UC-03, SUDO-UC-04, SUDO-UC-05

### SUDO-CN-10 — Grant Revocation Scope
- Admins can revoke any SudoGrant
- Researchers can only revoke SudoGrants where `granted_by` points to themselves
- Revocation is immediate: the grantee loses elevated permissions as soon as the grant is deleted
- **Applies to:** SUDO-UC-02

### SUDO-CN-11 — Teacher Ownership via Enrollment
- Teachers can only manage students enrolled in their courses
- Ownership is determined by `Enrollment` records linking `StudentProfile` to `Course` via `teacher_profile`
- This applies to teacher-initiated create, edit, and delete operations on students
- **Applies to:** SUDO-UC-04, SUDO-UC-05

### SUDO-CN-12 — Admin Creation Restricted to Bootstrap
- Admin accounts (`is_staff=True`) are created exclusively through the `ensure_admin` management command during environment bootstrap (ENV-UC-02)
- No API endpoint creates admin accounts; the `can_create_user` function never returns `True` for admin creation
- **Applies to:** SUDO-UC-03

### SUDO-CN-13 — Self-Issuance Blocked
- No reset code can ever target the issuer, regardless of permission type or role
- This is a universal rule: applies to ISSUE_STUDENT_RESET_CODE, ISSUE_RESEARCHER_RESET_CODE, and default teacher/researcher issuance
- Backend enforces: `_authorize_reset_issuance` rejects `issuer.id == target.id` with a generic permission denied error
- Error message must not reveal the self-targeting rule (defense-in-depth; self-issuance is practically impossible since a user must be logged in to issue)
- **Applies to:** AUTH-UC-07, SUDO-CN-09

> **Policy:** Self-issuance of reset codes is universally blocked. The issuer and target must be different users for all reset code operations, regardless of role or sudo permissions. Enforced in `_authorize_reset_issuance`. Applies to: SUDO-CN-13, AUTH-UC-07.

---

## 6) Infrastructure Contract

### 6.1 Endpoint Contract

#### Sudo Grant Management

| Method | Path | Auth | UC |
|--------|------|------|----|
| POST | `/api/v1/sudo-grants` | Researcher or Admin | SUDO-UC-01 |
| DELETE | `/api/v1/sudo-grants/{grant_id}` | Researcher or Admin | SUDO-UC-02 |

**POST payload:**
```json
{
    "user_id": 123,
    "permissions": ["CREATE_TEACHER", "EDIT_USER"],
    "can_grant_sudo": false
}
```

**POST response (201):**
```json
{
    "message": "Sudo granted",
    "grant_id": 1
}
```

**DELETE response (204):** no body

#### Affected Endpoints (Permission Enforcement)

These endpoints are defined in other FR domains but enforce sudo permission checks defined by this spec:

| Method | Path | Permission Check | UC |
|--------|------|------|----|
| POST | `/api/v1/users` | `can_create_user()` | SUDO-UC-03 |
| PATCH | `/api/v1/users/{user_id}` | `can_edit_user()` | SUDO-UC-04 |
| DELETE | `/api/v1/users/{user_id}` | `can_delete_user()` | SUDO-UC-05 |
| POST | `/api/v1/codes` | `_can_generate_code_type()` | SUDO-UC-03 (via CREATE_STUDENT) |
| POST | `/api/v1/auth/password-reset-codes` | `can_issue_reset_code()` | AUTH-UC-07 (via ISSUE_STUDENT_RESET_CODE / ISSUE_RESEARCHER_RESET_CODE) |
| GET | `/api/v1/users/staff` | `IsResearcherOrAdmin` | (read access) |

Notes:
- `IsResearcherOrAdmin` guards sudo and staff endpoints; checks `is_staff` or `RESEARCHER` role.
- `IsTeacherOrAbove` guards user management endpoints; checks `is_staff`, `RESEARCHER`, or `TEACHER` role.
- Individual permission functions (`can_create_user`, `can_edit_user`, `can_delete_user`) perform the fine-grained sudo checks within these views.

### 6.2 Permission Check Flow

#### Evaluation Order

```
1. Is user.is_staff?
   → Yes: Admin-level access (within admin scope; cannot target other admins)
   → No: Continue

2. Is user a RESEARCHER with SudoGrant?
   → Yes: Check if specific SudoPermission is in grant.permissions
     → Permission present: Elevated access for that action
     → Permission absent: Denied
   → No SudoGrant: Researcher-level access only (read-heavy, assignment template management)

3. Is user a TEACHER?
   → Teacher-level access (own students via enrollment)

4. Is user a STUDENT?
   → Student-level access (own data only)
```

#### Creation Hierarchy

```
Admin seeds → Researchers (via ensure_admin + create_user)
Researchers seed → Teachers (via sudo CREATE_TEACHER or registration codes)
Teachers seed → Students (via create_user or registration codes)
```

#### SudoGrant Lifecycle

```
[No Grant] → Grant Created (admin or authorized researcher)
                → Grant Updated (re-grant with new permissions)
                → Grant Revoked (admin or grant creator)
                   → [No Grant]
```

### 6.3 DRF Permission Classes

The following DRF permission classes enforce role-based access control across all API endpoints. They are defined in `core/permissions.py` and used with the `@permission_classes` decorator.

| Class | Access Rule | Usage |
|-------|------------|-------|
| `IsAdmin` | `is_staff` only | Admin-exclusive endpoints |
| `IsResearcher` | RESEARCHER role only | Researcher-exclusive endpoints |
| `IsResearcherOrAdmin` | `is_staff` or RESEARCHER | Sudo, staff list |
| `IsTeacher` | TEACHER role only | Teacher-exclusive endpoints |
| `IsTeacherOrAdmin` | `is_staff` or TEACHER | Legacy alias |
| `IsTeacherOrAbove` | `is_staff`, RESEARCHER, or TEACHER | User CRUD, code management |

**Helper Functions:**

| Function | Signature | Purpose |
|----------|-----------|---------|
| `primary_role(user)` | `→ str` | Returns highest role: `"ADMIN"` for `is_staff`, else RESEARCHER > TEACHER > STUDENT |
| `has_role(user, role)` | `→ bool` | Check if user has specific role |
| `has_any_role(user, roles)` | `→ bool` | Check if user has any of the specified roles |
| `has_sudo_permission(user, perm)` | `→ bool` | Check if user is a sudoed researcher with the given permission |

### 6.4 Data Model

#### SudoPermission Enum

```
CREATE_TEACHER    — Create teacher accounts
CREATE_STUDENT    — Create student accounts
CREATE_RESEARCHER_CODES — Generate researcher registration codes
EDIT_USER         — Edit user accounts (within user role space)
DELETE_USER        — Delete user accounts (within user role space)
ISSUE_STUDENT_RESET_CODE — Researcher can issue reset codes for students (sudo extension)
ISSUE_RESEARCHER_RESET_CODE — Researcher can issue reset codes for researchers (sudo extension)
VIEW_IDENTIFIABLE_VIZ — Researcher can view identifiable fields in visualization data (FR-09)
EXPORT_IDENTIFIABLE — Researcher can export identifiable fields in CSV exports (FR-10)
```

#### SudoGrant Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `user` | OneToOneField(User) | The researcher receiving elevated permissions (unique per user) |
| `granted_by` | ForeignKey(User, PROTECT) | Admin or sudoed researcher who created this grant |
| `granted_at` | DateTimeField(auto_now_add) | When the grant was created |
| `can_grant_sudo` | BooleanField(default=False) | Whether this researcher can delegate sudo to others |
| `permissions` | JSONField(default=list) | List of SudoPermission values (e.g., `["CREATE_TEACHER", "EDIT_USER"]`) |

**Table:** `sudo_grants`

**Validation:** `SudoGrant.clean()` validates that all values in `permissions` are valid `SudoPermission` choices.

### 6.5 Wireframe Mapping

No wireframes have been created for FR-03 sudo management. The grant and revoke operations are admin/researcher dashboard features that will be designed when the admin panel wireframes are created.

| UC | Wireframe Status |
|----|-----------------|
| SUDO-UC-01 | Pending — admin/researcher dashboard |
| SUDO-UC-02 | Pending — admin/researcher dashboard |
| SUDO-UC-03–05 | N/A — permission checks are backend-only; affected UIs are defined in their respective FRs |

---

## 7) Error Model

| Scenario | Behavior | Contract |
|----------|----------|----------|
| Grantee not a researcher | Must have RESEARCHER role | `400` |
| Escalation attempt (granting unheld permissions) | Cannot grant permissions you don't hold | `403` |
| Researcher sets can_grant_sudo=True | Only admins can set can_grant_sudo | `403` |
| Granter not authorized (no can_grant_sudo) | can_grant_sudo=False | `403` |
| Missing required user_id | Missing field | `400` |
| User not found | Not found | `404` |
| Invalid permission values | Validation error from clean() | `400` |
| Non-researcher/non-admin attempts grant | Permission class rejection | `403` |
| Grant not found (revoke) | Not found | `404` |
| Unauthorized revocation (not grant creator) | Can only revoke grants you created | `403` |
| Non-researcher/non-admin attempts revoke | Permission class rejection | `403` |
| Insufficient permission for user creation | Forbidden | `403` |
| Insufficient permission for user edit | Forbidden | `403` |
| Admin target blocked in edit | Forbidden | `403` |
| Insufficient permission for user delete | Forbidden | `403` |

---

## 8) Test Strategy by Layer

**Naming Convention:** `test_SUDO_UC_nn[_ROLE|_En]`, `test_SUDO_CN_nn`, `ST-SUDO-UC-nn`

### Backend Unit

- test_SUDO_UC_01 (aggregator)
- test_SUDO_UC_01_ADMIN
- test_SUDO_UC_01_RESEARCHER
- test_SUDO_UC_01_E1
- test_SUDO_UC_01_E2
- test_SUDO_UC_01_E3
- test_SUDO_UC_01_E4
- test_SUDO_UC_01_E5
- test_SUDO_UC_01_E6
- test_SUDO_UC_01_E7
- test_SUDO_UC_01_E8
- test_SUDO_CN_03 (escalation prevention)
- test_SUDO_CN_05 (admin-only can_grant_sudo)
- test_SUDO_CN_06 (permission enum validation)
- test_SUDO_CN_08 (update-on-regranting)
- test_SUDO_UC_02 (aggregator)
- test_SUDO_UC_02_ADMIN
- test_SUDO_UC_02_RESEARCHER
- test_SUDO_UC_02_E1
- test_SUDO_UC_02_E2
- test_SUDO_UC_02_E3
- test_SUDO_UC_03 (aggregator — role matrix)
- test_SUDO_UC_03_ADMIN
- test_SUDO_UC_03_RESEARCHER (no sudo)
- test_SUDO_UC_03_RESEARCHER_CREATE_TEACHER
- test_SUDO_UC_03_RESEARCHER_CREATE_STUDENT
- test_SUDO_UC_03_TEACHER
- test_SUDO_UC_03_E1
- test_SUDO_UC_04 (aggregator — role matrix)
- test_SUDO_UC_04_ADMIN
- test_SUDO_UC_04_RESEARCHER_EDIT_USER
- test_SUDO_UC_04_TEACHER (own students)
- test_SUDO_UC_04_E1
- test_SUDO_UC_04_E2
- test_SUDO_UC_05 (aggregator — role matrix)
- test_SUDO_UC_05_ADMIN
- test_SUDO_UC_05_RESEARCHER_DELETE_USER
- test_SUDO_UC_05_TEACHER (own students)
- test_SUDO_UC_05_E1

### Backend Integration

- test_SUDO_UC_01_admin_grant_flow
- test_SUDO_UC_01_researcher_delegate_flow
- test_SUDO_UC_01_escalation_blocked
- test_SUDO_UC_02_admin_revoke_flow
- test_SUDO_UC_02_researcher_revoke_own
- test_SUDO_UC_02_researcher_revoke_other_blocked

### Security

- test_SUDO_UC_01_non_admin_cannot_grant_sudo

### System Tests (Black Box)

- ST-SUDO-UC-01
- ST-SUDO-UC-01-E2
- ST-SUDO-UC-02
- ST-SUDO-UC-03
- ST-SUDO-UC-04
- ST-SUDO-UC-05

---

## 9) NFR Cross-References

| Constraint | NFR | Rationale |
|-----------|-----|-----------|
| SUDO-CN-03 (no escalation) | NFR-SEC-08 (Least Privilege) | Subset-only delegation ensures researchers cannot grant permissions beyond what they hold |
| SUDO-CN-04 (admin/user space separation) | NFR-SEC-08 (Least Privilege) | Sudo operates exclusively within user role space; admin accounts are protected from sudo-elevated operations |
| SUDO-CN-01 (role hierarchy) | NFR-PRIV-01 (FERPA-Compliant Data Access Controls) | Role hierarchy ensures users can only access data appropriate to their role level |

---

## 10) Cross-Domain References

FR-03 defines the permission model that other FR domains reference:

| FR | Cross-Reference | Notes |
|----|----------------|-------|
| FR-01 AUTH | AUTH-UC-07 uses role hierarchy for issuer-based reset-code generation | Defaults: teacher->student, researcher->teacher, admin->any; sudo extends researcher scope for student/researcher issuance |
| FR-02 REG | REG-CN-10 references role hierarchy + sudo for code generation | `CREATE_STUDENT` and `CREATE_RESEARCHER_CODES` sudo expand researcher code generation scope |
| FR-05 CRS | Course visibility uses role hierarchy | Researcher read access to all courses (defined in FR-05) |
| FR-06 ATMPL | AssignmentTemplate CRUD uses role hierarchy | Researcher full access to assignment templates (defined in FR-06) |
| FR-09 VIZ | VIZ-CN-01 uses `VIEW_IDENTIFIABLE_VIZ` sudo to gate researcher access to identifiable fields | `has_sudo_permission(user, VIEW_IDENTIFIABLE_VIZ)` controls anonymization in VIZ endpoints |
| FR-10 EXP | EXP-CN-01 uses `EXPORT_IDENTIFIABLE` sudo to gate researcher access to identifiable fields in CSV exports | `has_sudo_permission(user, EXPORT_IDENTIFIABLE)` + explicit `identifiable=true` query param required |
| FR-12 ENV | Admin bootstrap creates system admin | `ensure_admin` sets `is_staff=True` without user role |

---

## 11) Current Implementation Alignment Notes

### Permission Wiring Status

All seven `SudoPermission` enum values are fully wired in the codebase:

- **User management permissions** (`CREATE_TEACHER`, `CREATE_STUDENT`, `EDIT_USER`, `DELETE_USER`): Enforced via `can_create_user`, `can_edit_user`, `can_delete_user` in `accounts/services/_roles.py`.
- **Code generation permission** (`CREATE_RESEARCHER_CODES`): Enforced via `_can_generate_code_type` in `accounts/services/_registration.py`. Explicitly non-delegable by researchers (only CREATE_RESEARCHER_CODES is in `NON_DELEGABLE_PERMISSIONS`).
- **Reset code permissions** (`ISSUE_STUDENT_RESET_CODE`, `ISSUE_RESEARCHER_RESET_CODE`): Enforced via `_authorize_reset_issuance` in `accounts/services/_password_reset.py`. When a researcher issuer targets a student, the function checks for `ISSUE_STUDENT_RESET_CODE`; when targeting a researcher, it checks for `ISSUE_RESEARCHER_RESET_CODE`.

### Admin Panel Registration

Both sudo-related models are registered in `accounts/admin.py` with full admin classes:

- `SudoGrant` is registered as `SudoGrantAdmin` with list display (id, user, granted_by, can_grant_sudo, granted_at), list filter (can_grant_sudo), and search fields (user username, granted_by username).
- `ResearcherProfile` is registered as `ResearcherProfileAdmin` with list display (user, created_at) and search fields (user username, user name).
