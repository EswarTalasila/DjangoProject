# PlantUML Diagrams

See `Diagrams-Index.md` for a full list of generated diagrams and their locations.

## Structure
- `uml/class/backend/`: backend class diagrams (per module + combined).
- `uml/class/frontend/`: frontend class diagrams (optional, only if tooling available).
- `uml/entity/postgres/`: entity relationship diagrams from Django models.
- `sequence/api/`: runtime API sequences grouped by route segment and status.

## Sequence grouping
- Route segments are derived from `http.route`/`http.target`.
- `sequence/api/<segment>/<success|error>/` splits pass/fail paths.
- Filenames follow `seq-<method>-<route>-<status>.wsd`.

## Regenerate
- `scripts/diagrams/generate_all.sh` (runs inside Docker)
  - Backend classes: `uml/class/backend/backend-services.wsd`
  - Backend per-module classes: `uml/class/backend/backend-<app>.wsd`
  - Postgres entities: `uml/entity/postgres/postgres-all.wsd`
  - Postgres per-module entities: `uml/entity/postgres/postgres-<app>.wsd`
  - Sequences (OTel required): `sequence/api/...`
  - Frontend classes (optional): `uml/class/frontend/frontend-classes.wsd`
- `scripts/diagrams/index_diagrams.sh` (refresh `Diagrams-Index.md` only, Docker)
- `scripts/diagrams/generate_all.sh` also refreshes the index after generation
