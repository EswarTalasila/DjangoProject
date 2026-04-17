# Migration Plan

## Phase 0: Baseline alignment
- Freeze current API paths and payloads used by Angular services.
- Export and review runtime sequences for core flows.
- Establish a mapping table of endpoints and DTOs.
- Define versioning strategy (`/api/v1`) with compatibility routing for existing `/api/*`.

## Phase 1: Data model parity
- Build Django models mirroring current entities.
- Add foreign keys for raw ID relationships and backfill data.
- Add indexes for submission and visualization queries.

## Phase 2: Auth and user management
- Implement secure first-login and password reset tokens.
- Enforce role-based access control across endpoints.
- Implement Google OAuth verification for registered users.

## Phase 3: Course and assignment template workflows
- Implement courses, enrollments, assignment templates, assignments, submissions.
- Preserve question types and grading modes.
- Enforce assignment template versioning or lock after submissions.

## Phase 4: Visualization and export
- Implement dashboard aggregations with pagination and caching.
- Implement CSV/PDF export with streaming or background jobs.

## Phase 5: Cutover and validation
- Run side-by-side in dev with data imports.
- Validate against existing Angular UI with no code changes.
- Produce final migration checklist and rollback plan.

## Risks and mitigations
- Data mismatch: use migration scripts and validate counts and foreign keys.
- OAuth mismatch: verify Google token flow with test accounts.
- UI compatibility: keep DTO shape consistent with current services.
- Scope creep: keep rewrite limited to parity + critical fixes; defer optional improvements to post-acceptance backlog.

## Known Issues Audit (January 2026)

An audit was conducted comparing the 28 known issues from the original Spring Boot application against the Django rewrite. Results are tracked in GitHub issues with the `legacy-issue` label.

### Issues Fixed in Rewrite (12 total)

| Issue | GitHub | Resolution |
|-------|--------|------------|
| Public registration accepts client-supplied role | #28 | `role_override=Role.STUDENT` forces student role |
| User edit endpoint lacks authorization | #29 | `can_edit_user()` enforces ownership checks |
| Assignment endpoints lack role checks | #30 | `@permission_classes([IsTeacher])` added |
| Submission endpoints lack role checks | #31 | `_can_access_submission()` enforces ownership |
| Visualization endpoint lacks auth | #32 | `@permission_classes([IsTeacherOrAdmin])` added |
| JWT expiration 7 days | #33 | Reduced to 1 hour access, 7 day refresh with rotation |
| CORS defaults to * | #34 | Explicit origins from environment variable |
| ddl-auto recreates schema | #35 | Django migrations used instead |
| Raw Long IDs instead of ForeignKey | #36 | Proper ForeignKey with CASCADE |
| Service layer excessive coupling | #37 | Services separated by domain |
| Override score not persisting | #38 | `bulk_update()` and `save()` persist changes |
| No input validation | #39 | Serializers with `is_valid(raise_exception=True)` |
| Answer orphan removal | #40 | ForeignKey with `on_delete=CASCADE` |

### Issues Still Open (11 total)

| Issue | GitHub | Priority | Status |
|-------|--------|----------|--------|
| Unauthenticated password-set flow | #17 | CRITICAL | Needs token-based flow |
| check-email enables user enumeration | #18 | HIGH | Returns userId without auth |
| JWT stored in localStorage (XSS) | #19 | CRITICAL | Frontend change needed |
| Insecure default secrets | #20 | MEDIUM | Needs fail-fast in production |
| No PostgreSQL RLS policies | #21 | HIGH | Defense-in-depth missing |
| nginx missing security headers | #22 | MEDIUM | CSP, HSTS, etc. missing |
| Image upload not implemented | #23 | MEDIUM | TextField exists, no storage |
| No soft delete/archival | #24 | HIGH | Hard deletes throughout |
| AssignmentTemplate not locked after submissions | #25 | MEDIUM | Can corrupt historical data |
| No reflection trend visualization | #26 | LOW | Only raw data returned |
| PDF/CSV export not implemented | #27 | LOW | Returns 501 |

### Not Applicable to Django Rewrite

- Duplicate Maven dependency (pom.xml) - Python uses pyproject.toml
- README suggests dropping NOT NULL - Proper migrations used

## Diagram references
- DTO and entity mapping context: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-dto-entity-map.wsd`
- Current service structure: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-services.wsd`

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
