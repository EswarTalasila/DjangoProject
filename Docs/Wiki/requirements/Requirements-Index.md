# Requirements Index (v5)

| Field | Value |
|-------|-------|
| **Status** | DRAFT |
| **Date** | 2026-02-10 |
| **Serialization** | FR-##; {DOMAIN}-(US\|UC\|CN)-##; {DOMAIN}-UC-##-{ROLE/ALL}; {DOMAIN}-US-##-{ROLE/ALL} |
| **Valid Roles** | ADMIN (system role) and RESEARCHER, TEACHER, STUDENT (user roles) |

---

## Actor Assignment Policy (Golden Standard)

### Role Classification

| Type | Role | Implementation | Description |
|------|------|----------------|-------------|
| **System Role** | ADMIN | `is_staff=True` | Platform administrator, Django admin access |
| **User Role** | RESEARCHER | `Role.RESEARCHER` | Highest user role, study oversight, assessment design |
| **User Role** | TEACHER | `Role.TEACHER` | Course management, student enrollment, grading |
| **User Role** | STUDENT | `Role.STUDENT` | Assignment completion, submission |

> **Key Distinction:** ADMIN is NOT in the Role enum. Admin status uses Django's `is_staff` flag. User roles are stored in the `user_roles` table.

### Actor Ordering Convention

When listing multiple actors, always use hierarchy order: **ADMIN > RESEARCHER > TEACHER > STUDENT**

### 2-Level Hierarchy

```
Level 1: FR-##                              Functional Requirement (WHAT the system must have)
    │
    └── Level 2: {DOMAIN}-{UC|US|CN}-##     Domain use case / user story / constraint
            │
            ├── Variant: {DOMAIN}-UC-##a    Lettered variant (different entry point / flow)
            └── Role stand-in: {DOMAIN}-UC-##-{ROLE/ALL}   Per-role coverage (metadata, not standalone)
```

### ID Format Reference

| Type | Pattern | Example |
|------|---------|---------|
| Functional Requirement | `FR-##` | FR-01, FR-02, FR-03 |
| Domain User Story | `{DOMAIN}-US-##[a-z]?` | AUTH-US-01, AUTH-US-01a-ADMIN |
| Domain Use Case | `{DOMAIN}-UC-##[a-z]?` | AUTH-UC-01, AUTH-UC-01a |
| Domain UC Error | `{DOMAIN}-UC-##[a-z]?-E#[a-z]?` | AUTH-UC-01-E1, AUTH-UC-01a-E1 |
| Domain Constraint | `{DOMAIN}-CN-##` | AUTH-CN-01, REG-CN-12 |
| Role Stand-in (UC) | `{DOMAIN}-UC-##[a-z]?-{ROLE/ALL}` | AUTH-UC-01-ALL, AUTH-UC-01a-ADMIN |
| Role Stand-in (US) | `{DOMAIN}-US-##[a-z]?-{ROLE/ALL}` | AUTH-US-01-ALL, AUTH-US-01a-ADMIN |

### Numbering

| Level | Format | Rule |
|-------|--------|------|
| **FR-##** | 01-99 | Sequential (01, 02, 03...) |
| **US/UC/CN-##** | 01-99 | Sequential per domain, starting at 01 |

**FR-to-Domain Mapping:**
```
FR-01  → AUTH
FR-02  → REG
FR-03  → SUDO
FR-04  → USER
FR-05  → CRS
FR-06  → ASMT
FR-07  → ASGN
FR-08  → SUB
FR-09  → VIZ
FR-10  → EXP
FR-11  → OBS
FR-12  → ENV
FR-13  → INFRA
FR-14  → ARCH
```

> **Rationale:** Domain prefix (AUTH, REG, etc.) identifies the FR. No range alignment needed — numbering is sequential per domain from 01.

### Valid Domains

| Feature Domains | Role Keywords |
|-----------------|---------------|
| AUTH, REG, SUDO, USER, CRS, ASMT, ASGN, SUB, VIZ, EXP, OBS, ENV, INFRA, ARCH | ADMIN, RESEARCHER, TEACHER, STUDENT |

### Role Coverage Policy

**Role stand-ins** (`{DOMAIN}-UC-##-{ROLE/ALL}`) are metadata entries nested under their parent domain UC. They are NOT standalone use cases.

- If **all 4 roles** have identical behavior: Roles column shows `ALL` and a single `-ALL` stand-in is used in docs (tests still split by role).
- If **a subset** of roles: Roles column lists specific roles, each with a stand-in
- **Variants** (lettered: `a`, `b`, `c`) represent a different entry point or flow for a specific role (e.g., AUTH-UC-01a-ADMIN for Django admin login)

### User Story Actor Listing

When writing user stories, explicitly list each included actor in hierarchy order:

```
AUTH-US-01: As an admin, researcher, teacher, or student I can log in with email and password...
```

### Constraint Scope

Constraints are **domain-based** and apply to ALL use cases under that functional requirement:

```
AUTH-CN-01 applies to → AUTH-UC-01, AUTH-UC-02, etc.
```

### Test Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Domain aggregator | `test_{DOMAIN}_UC_##` | `test_AUTH_UC_01` |
| Role test | `test_{DOMAIN}_UC_##_{ROLE}` | `test_AUTH_UC_01_ADMIN` |
| Variant test | `test_{DOMAIN}_UC_##a_{ROLE}` | `test_AUTH_UC_01a_ADMIN` |
| Error test | `test_{DOMAIN}_UC_##_E#` | `test_AUTH_UC_01_E1` |
| Constraint test | `test_{DOMAIN}_CN_##` | `test_AUTH_CN_04` |

**Aggregation Rule:** Domain tests pass only if ALL required role-specific tests pass.
```
test_AUTH_UC_01 PASSES only if test_AUTH_UC_01_ADMIN, test_AUTH_UC_01_RESEARCHER,
test_AUTH_UC_01_TEACHER, and test_AUTH_UC_01_STUDENT all pass.
```

**No ALL in test names.** Always split by role.

### ID Regex (Golden Standard)

```
FR:            ^FR-\d{2}$
DOMAIN-US:     ^(AUTH|REG|SUDO|USER|CRS|ASMT|ASGN|SUB|VIZ|EXP|OBS|ENV|INFRA|ARCH)-US-\d{2}[a-z]?$
DOMAIN-UC:     ^(AUTH|REG|SUDO|USER|CRS|ASMT|ASGN|SUB|VIZ|EXP|OBS|ENV|INFRA|ARCH)-UC-\d{2}[a-z]?$
DOMAIN-UC-E:   ^(AUTH|REG|SUDO|USER|CRS|ASMT|ASGN|SUB|VIZ|EXP|OBS|ENV|INFRA|ARCH)-UC-\d{2}[a-z]?-E\d+[a-z]?(-(ADMIN|RESEARCHER|TEACHER|STUDENT|ALL))?$
DOMAIN-CN:     ^(AUTH|REG|SUDO|USER|CRS|ASMT|ASGN|SUB|VIZ|EXP|OBS|ENV|INFRA|ARCH)-CN-\d{2}$
ROLE-STANDIN:  ^(AUTH|REG|SUDO|USER|CRS|ASMT|ASGN|SUB|VIZ|EXP|OBS|ENV|INFRA|ARCH)-UC-\d{2}[a-z]?-(ADMIN|RESEARCHER|TEACHER|STUDENT|ALL)$
ROLE-STANDIN-US: ^(AUTH|REG|SUDO|USER|CRS|ASMT|ASGN|SUB|VIZ|EXP|OBS|ENV|INFRA|ARCH)-US-\d{2}[a-z]?-(ADMIN|RESEARCHER|TEACHER|STUDENT|ALL)$
```

---

## FR Pages

- `FR-01-Auth.md`
- `FR-02-Registration.md`
- `FR-03-Sudo.md`
- `FR-04-User.md`
- `FR-05-Courses.md`
- `FR-06-Assessments.md`
- `FR-07-Assignments.md`
- `FR-08-Submissions.md`
- `FR-09-Visualization.md`
- `FR-10-Export.md`
- `FR-11-Observability.md`
- `FR-12-Environment.md`
- `FR-13-Infrastructure.md`
- `FR-14-Lifecycle-Archival.md`

---

## NFR Pages

- `../nfr/NFR-Index.md`
