# Observability and Diagrams

## Goals
- Make PlantUML the primary diagram format for all architecture, class, ER, and runtime sequence diagrams.
- Keep diagram generation automated and repeatable from code + runtime traces.
- Provide a one-command workflow to refresh diagrams during development.

## Backend tracing (Django) — DEFERRED
OpenTelemetry distributed tracing has been removed from the active runtime. If reintroduced
later, it will be rebuilt intentionally with a clean interface. See Prompt.md for context.

## Frontend trace propagation — DEFERRED
W3C Trace Context propagation is deferred along with backend tracing.

## Diagram generation — DEFERRED
Automated diagram generation is removed from the active workflow until revisited.
Historical PlantUML outputs may remain in the repository as references, but
there is currently no supported regeneration command.

## Output format and storage
- Primary output: PlantUML `.wsd`.
- Output path: `Docs/diagrams/plantuml` (versioned).
- Optional secondary output: Mermaid `.mmd` (not required for this rewrite).

## Tooling expectations
- Diagram generation is currently out of scope for the active workflow.
- If reintroduced later, it should come back with a maintained interface and matching docs.

## Acceptance criteria
- Historical diagrams remain readable when present.
- No active workflow or CI path depends on diagram-generation scripts.

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
