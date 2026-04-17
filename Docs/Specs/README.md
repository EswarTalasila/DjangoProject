# <repository> Spec Sheets

This folder contains the rewrite spec set for the Python/Django + Angular (TypeScript) + Postgres stack, designed around the shared nginx proxy and self-hosted Docker deployment model. The rewrite is parity-focused: same UI and workflows, versioned APIs with compatibility for existing `/api/*`, and no new features beyond critical fixes.

## Index
- `<repository>/Docs/Specs/00-Overview.md`
- `<repository>/Docs/Specs/01-User-Stories.md`
- `<repository>/Docs/Specs/02-Functional-Requirements.md`
- `<repository>/Docs/Specs/03-Non-Functional-Requirements.md`
- `<repository>/Docs/Specs/04-Architecture.md`
- `<repository>/Docs/Specs/05-Data-Model.md`
- `<repository>/Docs/Specs/06-Deployment.md`
- `<repository>/Docs/Specs/07-Testing-Strategy.md`
- `<repository>/Docs/Specs/08-Migration-Plan.md`
- `<repository>/Docs/Specs/09-Observability-and-Diagrams.md`
- `<repository>/Docs/Specs/10-Development-Workflow.md`
- `<repository>/Docs/Specs/11-Code-Style-and-Architecture.md`
- `<repository>/Docs/Specs/12-API-Contract.md`
- `<repository>/Docs/Specs/13-Question-Answer-Matrix.md`
- `<repository>/Docs/Specs/14-Frontend-Backend-Mapping.md`
- `<repository>/Docs/Specs/15-Schema-Comparison.md`

## Legacy Java Codebase References

> **Note:** References to `2025Fall-Team22-EE-Lab-Personal/` and `Migration Notes/` throughout these specs point to the **original Java/Spring Boot codebase** that this Python/Django rewrite is based on. These paths reference an external repository and are preserved for historical context during the migration process.

## Diagram references (PlantUML) - Original Java Codebase
- Backend structural context (current): `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-all.wsd`
- Backend entities: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-entities.wsd`
- Backend DTO map: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-dto.wsd`
- Service/repo map: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-service-repo-map.wsd`
- DTO to entity map: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-backend-dto-entity-map.wsd`
- Frontend services: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-frontend-services.wsd`
- Frontend component structure: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-frontend-components.wsd`
- Frontend to backend map: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-frontend-backend-map.wsd`
- Merged services map: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-merged-services.wsd`
- Runtime sequences (current): `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/sequence`

These diagrams are derived from compiled bytecode, frontend AST, and runtime traces to give a reliable view of current structure and flows.

## Source references (audit + issues) - Original Java Codebase
- Migration audit and issues: `Migration Notes/Known Issues.md`
- Personal audit summary: `Migration Notes/Personal Audit.md`
- Performance review: `Migration Notes/Performance Review.md`
- Guide extracts: `Migration Notes/dev_guide_extracted.md`, `Migration Notes/user_guide_extracted.md`, `Migration Notes/deployment_guide_extracted.md`
- Personal repo diagram index: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
