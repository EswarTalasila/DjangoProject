# Observability and Diagrams (PlantUML-first)

## Goals
- Make PlantUML the primary diagram format for all architecture, class, ER, and runtime sequence diagrams.
- Keep diagram generation automated and repeatable from code + runtime traces.
- Provide a one-command workflow to refresh diagrams during development.

## Backend tracing (Django)
- Use OpenTelemetry for Django and database instrumentation.
- Export OTLP traces to a local collector (Jaeger or Tempo).
- Include request IDs and user context (role, userId) in trace attributes where safe.

## Frontend trace propagation
- Ensure API calls propagate trace headers (W3C Trace Context).
- If Angular instrumentation is adopted, correlate UI actions to backend traces.
  - For now, the frontend interceptor injects a `traceparent` header per request.

## Diagram generation (backend)
- Class diagrams: generated from Python code and type hints.
  - Include class names, fields, and method signatures where determinable.
  - Represent service and repository layers distinctly.
- ER diagrams: generated directly from Django models (relationships embedded in class diagram output).
- Runtime sequence diagrams: generated from OpenTelemetry traces of test workflows.

## Diagram generation (frontend)
- Class diagrams: generated from Angular TypeScript AST.
- Component/service diagrams: include method signatures and DTO usage.

## Output format and storage
- Primary output: PlantUML `.wsd`.
- Output path: `Docs/diagrams/plantuml` (versioned).
- Runtime sequences stored under `Docs/diagrams/plantuml/sequence`.
- Optional secondary output: Mermaid `.mmd` (not required for this rewrite).

## Tooling expectations
- Provide scripts/commands to:
  - Generate class diagrams (backend + frontend).
  - Generate ER diagrams from Django models.
  - Generate runtime sequences from traces.
  - Sync and index outputs.

## Current implementation
### Backend tracing
- Enable tracing via `OTEL_ENABLED=true` and set `OTEL_TRACE_FILE` to write JSONL spans.
- Optional OTLP export via `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS`.

### Diagram generation

The recommended approach is to use the unified generator:
```bash
python scripts/diagrams/generate_all.py
```

This generates all diagrams into the correct directory structure:
- `Docs/diagrams/plantuml/uml/class/backend/` - Backend class diagrams
- `Docs/diagrams/plantuml/uml/class/frontend/` - Frontend class diagrams
- `Docs/diagrams/plantuml/uml/entity/postgres/` - PostgreSQL entity diagrams
- `Docs/diagrams/plantuml/sequence/api/` - Runtime sequence diagrams

Individual scripts (for targeted regeneration):
- Backend entity diagrams: `python scripts/diagrams/models_to_plantuml.py --out Docs/diagrams/plantuml/uml/entity/postgres/postgres-all.wsd`
- Backend class diagrams: `python scripts/diagrams/backend_to_plantuml.py --out Docs/diagrams/plantuml/uml/class/backend/backend-services.wsd`
- Frontend class diagrams: `node scripts/diagrams/frontend_to_plantuml.mjs --out Docs/diagrams/plantuml/uml/class/frontend/frontend-classes.wsd`
  - Requires `npm install` in `frontend/` (for the TypeScript parser).
- Runtime sequences: `python scripts/diagrams/trace_to_plantuml.py --input Docs/diagrams/otel/trace.jsonl --out Docs/diagrams/plantuml/sequence/api`

## Minimum toolchain (suggested)
- Backend class diagrams: `pyreverse` or custom AST parser (preferred if method signatures are required).
- ER diagrams: `django-extensions graph_models`.
- Runtime sequences: custom script to translate OTel spans to PlantUML sequence diagrams.
- Frontend diagrams: existing TypeScript AST parser extended for PlantUML output.

## Acceptance criteria
- A developer can run a single script to regenerate all diagrams.
- Diagrams render in VS Code with PlantUML extension without manual edits.
- Class diagrams include methods/fields for backend and frontend where available.
- Runtime sequences reflect the executed test workflows and match API endpoints.

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
