# Development Workflow

## Goals
- Fast local setup for backend + frontend + database.
- Repeatable development commands.
- Proxy-first architecture with the shared nginx proxy active in dev, test, and prod.

## Local development options

### Node.js version
- Use Node.js LTS (see `.nvmrc` for the pinned LTS version).
- Example: `nvm install` then `nvm use` before running frontend commands.

### Option A: Docker Compose (recommended)
Use the task surface and generated env files.

1) Choose topology and materialize env files:
```bash
task env:local
task env:init
```

2) Review the root `.env` for serious values (do not commit):
```bash
# PUBLIC_HOST=localhost
# DJANGO_SECRET_KEY=...
# POSTGRES_PASSWORD=...
# GOOGLE_CLIENT_ID=...
```

3) Start services:
```bash
task up:dev
```

4) Inspect state or logs if needed:
```bash
task status:dev
task logs:dev
```

### Option A1: Docker Compose (dev with live reload)
The active dev stack already includes live backend/frontend development behavior through `task up:dev`.
Use `task rebuild:dev` if image or dependency changes require a non-destructive refresh.

### Option B: Hybrid (local backend/frontend, dockerized DB)
- Run Postgres via Docker.
- Run Django and Angular locally for faster iteration.

Commands (example):
```bash
# Start database only
# (Use the database service from the compose template)

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend
npm install
npm start
```

## Testing commands (target)
- Ensure the testing stack and run all test surfaces:
```bash
task test
```

- Backend-focused run:
```bash
task test:backend
```

- Frontend-focused run:
```bash
task test:frontend
```

## Diagram generation (PlantUML-first)
- Diagram generation is currently deferred and not part of the active workflow.
- Historical outputs under `docs/diagrams/plantuml` may remain as references.

## Notes
- Keep `/api/v1/*` paths compatible with frontend services and route them through the proxy.
- Version endpoints under `/api/v1` with compatibility routing.
- Proxy remains active locally; use `localhost:8080/8443` for dev and `localhost:9080/9443` for test.
- Use a unified `.env` during development and a committed `.env.template` for defaults/documentation.
- Do not keep `.env.local` variants; `.env` is gitignored and treated as the single source of truth for dev.

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
