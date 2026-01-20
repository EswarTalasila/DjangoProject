# Schema Comparison (Legacy vs Django)

## Purpose
Compare the legacy `schema.sql` to the planned Django models to ensure parity and surface mismatches early.

## Inputs
- Legacy schema: `2025Fall-Team22-EE-Lab-Personal/database/init/schema.sql`
- Planned Django models: `<repository>/Docs/Specs/05-Data-Model.md`

## Comparison checklist
- [ ] All legacy tables have a matching Django model.
- [ ] All legacy columns are represented (or intentionally dropped with rationale).
- [ ] All foreign key relationships are explicit in Django.
- [ ] Indexes exist for high-traffic queries (submissions, assignments, enrollments).
- [ ] Row-level security requirements are translated into application-level RBAC.

## Known mismatches to resolve
- Legacy uses raw ID fields for some relationships; rewrite must use ForeignKey fields.
- Legacy schema may include nullable fields that should be non-null in Django (align with validation).

## Notes
- This document should be updated during implementation with concrete diffs.

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
