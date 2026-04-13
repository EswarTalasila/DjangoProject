# Observability and Diagrams (PlantUML-first)

## Goals
- Make PlantUML the primary diagram format for all architecture, class, ER, and runtime sequence diagrams.
- Keep diagram generation automated and repeatable from code + runtime traces.
- Provide a one-command workflow to refresh diagrams during development.

## Backend tracing (Django) — DEFERRED
OpenTelemetry distributed tracing has been removed from the active runtime. If reintroduced
later, it will be rebuilt intentionally with a clean interface. See Prompt.md for context.

## Frontend trace propagation — DEFERRED
W3C Trace Context propagation is deferred along with backend tracing.

## Diagram generation (backend)
- Class diagrams: generated from Python code and type hints.
  - Include class names, fields, and method signatures where determinable.
  - Represent service and repository layers distinctly.
- ER diagrams: generated directly from Django models (relationships embedded in class diagram output).

## Diagram generation (frontend)
- Class diagrams: generated from Angular TypeScript AST.
- Component/service diagrams: include method signatures and DTO usage.

## Output format and storage
- Primary output: PlantUML `.wsd`.
- Output path: `Docs/diagrams/plantuml` (versioned).
- Optional secondary output: Mermaid `.mmd` (not required for this rewrite).

## Tooling expectations
- Provide scripts/commands to:
  - Generate class diagrams (backend + frontend).
  - Generate ER diagrams from Django models.
  - Sync and index outputs.

## Current implementation
### Diagram generation

The recommended approach is to use the unified generator:
```bash
python scripts/diagrams/generate_all.py
```

This generates all diagrams into the correct directory structure:
- `Docs/diagrams/plantuml/uml/class/backend/` - Backend class diagrams
- `Docs/diagrams/plantuml/uml/class/frontend/` - Frontend class diagrams
- `Docs/diagrams/plantuml/uml/entity/postgres/` - PostgreSQL entity diagrams

Individual scripts (for targeted regeneration):
- Backend entity diagrams: `python scripts/diagrams/models_to_plantuml.py --out Docs/diagrams/plantuml/uml/entity/postgres/postgres-all.wsd`
- Backend class diagrams: `python scripts/diagrams/backend_to_plantuml.py --out Docs/diagrams/plantuml/uml/class/backend/backend-services.wsd`
- Frontend class diagrams: `node scripts/diagrams/frontend_to_plantuml.mjs --out Docs/diagrams/plantuml/uml/class/frontend/frontend-classes.wsd`
  - Requires `npm install` in `frontend/` (for the TypeScript parser).

## Minimum toolchain (suggested)
- Backend class diagrams: `pyreverse` or custom AST parser (preferred if method signatures are required).
- ER diagrams: `django-extensions graph_models`.
- Frontend diagrams: existing TypeScript AST parser extended for PlantUML output.

## Acceptance criteria
- A developer can run a single script to regenerate all diagrams.
- Diagrams render in VS Code with PlantUML extension without manual edits.
- Class diagrams include methods/fields for backend and frontend where available.

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
