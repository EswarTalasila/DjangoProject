# FR-04 User Management (USER) — Detailed Spec (v5)

| Field | Value |
|-------|-------|
| **Status** | COMPLETE |
| **Date** | 2026-02-28 |
| **Domain** | USER |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER |
| **Dependencies** | FR-03 SUDO (role matrix, sudo permissions for elevated user management) |
| **Related Issues** | #28 (role hierarchy and sudo interaction) |

---

## 1) Scope

### Core Intent
- Provide privileged user lifecycle operations (create, edit, delete) within the user-role space.
- Enforce role-based and ownership-based authorization with sudo-driven capability extension.
- Maintain system-managed username immutability and identifier uniqueness across all user operations.

### In Scope
- Privileged user lifecycle in user-role space (`RESEARCHER`, `TEACHER`, `STUDENT`):
  - create user
  - edit user
  - delete user
  - list staff users
- System-managed username policy (caller cannot set or update usernames).
- Role-based and ownership-based authorization for user management.
- Sudo-driven capability extension for researchers (delegation rules are defined in FR-03).
- ID-based user path contract (`/users/{user_id}`).

### Out of Scope
- Self-registration flows (`/registration/*`) — FR-02.
- Authentication/session/password flows (`/auth/*`) — FR-01.
- Sudo grant/revoke lifecycle (`/sudo-grants*`) — FR-03.
- Course enrollment and student onboarding flows — FR-05 / FR-02.
- Bulk user provisioning — superseded by registration code flows (FR-02). Registration codes with configurable `max_uses` provide secure self-service onboarding without credential distribution problems.

---

## 2) Actors

| Role | Type | USER domain permissions |
|------|------|-------------------------|
| ADMIN | System role (`is_staff=True`) | Create RESEARCHER/TEACHER users, edit RESEARCHER/TEACHER users, delete RESEARCHER/TEACHER users, list staff |
| RESEARCHER | User role | Base: read-only staff list. Elevated write actions require sudo permissions from FR-03 (`CREATE_TEACHER`, `CREATE_STUDENT`, `EDIT_USER`, `DELETE_USER`) |
| TEACHER | User role | Create/edit/delete students they own via enrollment ownership boundary |
| STUDENT | User role | No USER write permissions |

**Actor ordering:** ADMIN > RESEARCHER > TEACHER > STUDENT

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| USER-US-01 | ADMIN, RESEARCHER, TEACHER | As a privileged user I can create users within my allowed role space so onboarding is controlled by policy. |
| USER-US-02 | ADMIN, RESEARCHER, TEACHER | As a privileged user I can edit user profile/role data within allowed scope. |
| USER-US-03 | ADMIN, RESEARCHER, TEACHER | As a privileged user I can delete users within allowed scope. |
| USER-US-04 | ADMIN, RESEARCHER | As a privileged user I can list staff users for management workflows. |

---

## 4) Use Cases

### USER-UC-01 — Create User

**Roles:** ADMIN, RESEARCHER (with sudo), TEACHER
**Endpoint:** `POST /api/v1/users`

**Main Flow:**
1. Caller submits create payload (`name`, optional `role`, optional `password`, optional `email`).
2. System enforces username immutability: caller cannot provide `username`.
3. System resolves requested role (default `STUDENT`).
4. System enforces role matrix authorization.
5. System enforces non-student email requirement.
6. System checks identifier uniqueness.
7. System generates managed username and creates user + exactly one role + role profile.
8. Returns created user object.

**Role Coverage:**
- `USER-UC-01-ADMIN`: Can create `RESEARCHER` and `TEACHER`.
- `USER-UC-01-RESEARCHER`: Requires sudo permissions (`CREATE_TEACHER` and/or `CREATE_STUDENT`) from FR-03.
- `USER-UC-01-TEACHER`: Can create `STUDENT` only.

**Errors:**
- `USER-UC-01-E1`: Missing required name.
- `USER-UC-01-E2`: Forbidden by role matrix.
- `USER-UC-01-E3`: Non-student create missing email.
- `USER-UC-01-E4`: Email already taken.
- `USER-UC-01-E5`: Caller supplied username (rejected).

**Tests (representative):**
- `test_USER_UC_01_ADMIN`
- `test_USER_UC_01_E2`
- `test_USER_UC_01_E3`
- `test_create_user_rejects_taken_email`
- `test_create_user_rejects_username_field`
- `test_USER_UC_01` (single-role invariant)

---

### USER-UC-02 — Edit User

**Roles:** ADMIN, RESEARCHER (with `EDIT_USER`), TEACHER (owned students only)
**Endpoint:** `PATCH /api/v1/users/{user_id}`

**Main Flow:**
1. Caller submits patch payload.
2. System resolves target user by ID.
3. System checks authorization by role/sudo/ownership.
4. System rejects username edits (immutable).
5. System enforces duplicate-email prevention.
6. System enforces non-student email requirement on updates.
7. System applies updates (name/email/password/role).
8. Returns updated user object.

**Errors:**
- `USER-UC-02-E1`: Forbidden by scope matrix.
- `USER-UC-02-E2`: Admin/staff target cannot be edited through role flows.
- `USER-UC-02-E3`: Username update attempt (immutable).
- `USER-UC-02-E4`: Duplicate email.
- `USER-UC-02-E5`: Non-student email removed/empty.

**Tests (representative):**
- `test_USER_UC_02_E1`
- `test_edit_user_rejects_student_username_change`
- `test_edit_user_rejects_taken_email`
- `test_edit_user_email_required_non_student`
- `test_edit_user_name_update`
- `test_edit_user_password_update`
- `test_edit_user_role_change`

---

### USER-UC-03 — Delete User

**Roles:** ADMIN, RESEARCHER (with `DELETE_USER`), TEACHER (owned students only)
**Endpoint:** `DELETE /api/v1/users/{user_id}`

**Main Flow:**
1. System resolves target user by ID.
2. System validates delete authorization.
3. System deletes user and returns no-content response.

**Errors:**
- `USER-UC-03-E1`: Forbidden by scope matrix.
- `USER-UC-03-E2`: Target user not found.

**Tests (representative):**
- `test_USER_UC_03_E1`
- `test_SUDO_UC_05_*` references (FR-03 elevated delete paths)

---

### USER-UC-04 — List Staff

**Roles:** ADMIN, RESEARCHER
**Endpoint:** `GET /api/v1/users/staff`

**Main Flow:**
1. System applies role gate.
2. System returns paginated list of users in role set `{TEACHER, RESEARCHER}`.

**Errors:**
- `USER-UC-04-E1`: Forbidden for non-admin/non-researcher callers.

**Tests (representative):**
- `test_USER_UC_04_ADMIN`

---

## 5) Constraints

### USER-CN-01 — Role Matrix Enforcement
- Create/edit/delete must follow role + sudo + ownership matrix.
- Applies to: USER-UC-01, USER-UC-02, USER-UC-03.

### USER-CN-02 — Username Is System-Managed and Immutable
- Caller cannot set username on create.
- Username cannot be edited on patch.
- Applies to: USER-UC-01, USER-UC-02.

### USER-CN-03 — Non-Student Email Requirement
- Non-student users require email at create time and cannot remove it on update.
- Applies to: USER-UC-01, USER-UC-02.

### USER-CN-04 — Staff Target Protection in Role Flows
- Admin/staff accounts are blocked from edit path in user-role management flow.
- Applies to: USER-UC-02.

### USER-CN-05 — Teacher Ownership Boundary
- Teacher edit/delete only for students enrolled in teacher-owned courses.
- Applies to: USER-UC-02, USER-UC-03.

### USER-CN-06 — Identifier Uniqueness
- Email collisions are rejected against existing identifier space.
- Applies to: USER-UC-01, USER-UC-02.

### USER-CN-07 — Single-Role Invariant
- Created users are assigned exactly one role in `user_roles`.
- Applies to: USER-UC-01.

### USER-CN-08 — ID-Based Path Contract
- User edit/delete paths use numeric IDs (`/users/{user_id}`).
- Applies to: USER-UC-02, USER-UC-03.

### USER-CN-09 — Staff Listing Scope
- Staff listing endpoint includes TEACHER and RESEARCHER role users.
- Applies to: USER-UC-04.

---

## 6) Infrastructure Contract

### 6.1 Endpoint Contract

| Method | Path | Auth | UC |
|--------|------|------|-----|
| POST | `/api/v1/users` | IsTeacherOrAbove | USER-UC-01 |
| PATCH | `/api/v1/users/{user_id}` | IsTeacherOrAbove | USER-UC-02 |
| DELETE | `/api/v1/users/{user_id}` | IsTeacherOrAbove | USER-UC-03 |
| GET | `/api/v1/users/staff` | IsResearcherOrAdmin | USER-UC-04 |

---

## 7) Error Model

| Scenario | Behavior | Contract |
|----------|----------|----------|
| Missing required name (create) | Validation error | `400` |
| Forbidden by role matrix (create) | Access denied | `403` |
| Non-student create missing email | Validation error | `400` |
| Email already taken | Duplicate identifier | `409` |
| Caller supplied username (create) | Rejected; username is system-managed | `400` |
| Forbidden by scope matrix (edit) | Access denied | `403` |
| Admin/staff target edit via role flows | Protected from role-flow edits | `403` |
| Username update attempt (edit) | Immutable field rejection | `400` |
| Duplicate email (edit) | Duplicate identifier | `409` |
| Non-student email removed (edit) | Required field error | `400` |
| Forbidden by scope matrix (delete) | Access denied | `403` |
| Target user not found (delete) | Not found | `404` |
| Forbidden for non-admin/non-researcher (list staff) | Access denied | `403` |

---

## 8) Test Strategy by Layer

**Naming Convention:** `test_USER_UC_##[_ROLE|_E#]`, `test_USER_CN_##`, `ST-USER-UC-##`

### Backend Unit
- Permission matrix and ownership logic:
  - `tests/unit/services/test_permission_services.py`
- Goal: prove USER-CN-01/CN-05/CN-07 and FR-03-linked sudo enforcement logic in isolation.

### Backend Integration
- Route + serializer + persistence behavior:
  - `tests/integration/test_accounts_routes.py`
  - `tests/integration/test_accounts_error_paths.py`
- Goal: prove endpoint contracts and UC error paths (`USER-UC-01..04`).

### Frontend Unit / Integration
- No dedicated FR-04-only UI traceability suite yet.
- Existing dashboard and auth tests are tracked under frontend test suites and are out of FR-04 backend contract scope.

### Security Tests
- USER-relevant access gates are covered in accounts integration/security suites.
- FR-03 sudo tests provide security coverage for elevated USER actions.

### System Tests (Black Box)

These IDs define end-to-end black-box checks for USER behavior:

- **ST-USER-UC-01**: Privileged create-user role matrix (admin/researcher-sudo/teacher)
- **ST-USER-UC-02**: Edit-user authorization + immutable username enforcement
- **ST-USER-UC-03**: Delete-user authorization + not-found handling
- **ST-USER-UC-04**: Staff-list role gate + output scope (`TEACHER`, `RESEARCHER` only)

Current status:
- System test IDs are defined here for traceability.
- Execution is currently represented by backend integration coverage; dedicated external black-box harness is tracked separately.

---

## 9) NFR Cross-References

The following NFRs are applicable to FR-04 endpoints and flows:

- **NFR-Security**
  - Role/sudo/ownership authorization is enforced server-side for all USER write operations.
  - Username immutability and identifier uniqueness prevent identity tampering/collision.
- **NFR-Reliability**
  - USER APIs return deterministic status codes and structured error payloads.
- **NFR-Performance**
  - Staff listing uses pagination and prefetch (`prefetch_related("roles")`) for stable list performance.
- **NFR-Maintainability**
  - USER authorization logic is centralized in permission/service helpers (`can_create_user`, `can_edit_user`, `can_delete_user`).

---

## 10) Cross-Domain References

| Domain | USER dependency | Integration note |
|--------|----------------|------------------|
| FR-02 REG | Registration creates user accounts | REG-UC-01 creates accounts that USER endpoints subsequently manage |
| FR-03 SUDO | Role matrix and sudo permissions | USER-UC-01..03 authorization delegated to FR-03 can_create/edit/delete_user functions |
| FR-05 CRS | Course enrollment for teacher ownership boundary | USER-CN-05 teacher ownership determined via enrollment records |

---

## 11) Current Implementation Alignment Notes

1. USER behavior is covered by `tests/integration/test_accounts_routes.py` and `tests/integration/test_accounts_error_paths.py`, with permission logic unit-tested in `tests/unit/services/test_permission_services.py`.
2. Additional endpoint-focused coverage exists in `tests/integration/test_sudo_traceability.py` (FR-03 elevated USER paths) and `tests/integration/test_sudo_grants_me.py` (`/sudo-grants/me` capability gating consumed by USER dashboards).
3. FR-03 sudo traceability tests intentionally reference USER flows for elevated variants.
4. Wireframes/UI for FR-04-specific admin console flows are not required for backend contract completeness and are tracked separately.
