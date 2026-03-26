# Development Workflow

## Goals
- Fast local setup for backend + frontend + database.
- Repeatable development commands.
- Proxy-agnostic architecture with optional Traefik for TLS in dev.

## Local development options

### Node.js version
- Use Node.js LTS (see `.nvmrc` for the pinned LTS version).
- Example: `nvm install` then `nvm use` before running frontend commands.

### Option A: Docker Compose (recommended)
Use the provided templates and fill in environment values.

1) Copy templates:
```bash
cp "<repository>/Deployment/templates/docker-compose.template.yml" "<repository>/Deployment/docker-compose.yml"
cp "<repository>/Deployment/templates/traefik.template.yml" "<repository>/Deployment/traefik.yml"
```

2) Create a local `.env` for secrets (do not commit):
```bash
# Example variables
POSTGRES_DB=eelab
POSTGRES_USER=eelab
POSTGRES_PASSWORD=replace_me
DJANGO_SECRET_KEY=replace_me
DJANGO_ALLOWED_HOSTS=localhost
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost
```

3) Start services:
```bash
docker compose -f "<repository>/Deployment/docker-compose.yml" up -d --build
```

4) Run migrations:
```bash
docker compose -f "<repository>/Deployment/docker-compose.yml" exec backend python manage.py migrate
```

### Option A1: Docker Compose (dev with live reload)
Use the dev template for hot-reload on both backend and frontend.

1) Copy templates:
```bash
cp "<repository>/Deployment/templates/docker-compose.dev.template.yml" "<repository>/Deployment/docker-compose.dev.yml"
```

2) Start services:
```bash
docker compose -f "<repository>/Deployment/docker-compose.dev.yml" up -d
```

3) Notes:
- Backend runs `manage.py runserver` and installs deps on start for quick iteration.
- Frontend runs `npm start` on port 4200 behind Traefik.
- Replace `REPLACE_ME_HOST` values to match your local domain or `localhost`.
- Use the Python tooling templates for consistent linting/formatting.
  - `<repository>/Deployment/templates/pyproject.template.toml`
  - `<repository>/Deployment/templates/.pre-commit-config.template.yaml`
- Security/testing templates are available under `<repository>/Deployment/templates` (pytest, bandit, semgrep, Playwright, ZAP).

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
- Backend unit tests:
```bash
pytest backend/tests/unit
```

- Backend integration tests:
```bash
pytest backend/tests/integration
```

- Backend security tests:
```bash
pytest backend/tests/security
```

- Frontend unit tests:
```bash
npm run test
```

- Frontend e2e tests:
```bash
npm run e2e
```

## Diagram generation (PlantUML-first)
- Regenerate diagrams from code and traces using the planned scripts under `backend/tools/diagrams`.
- Output should be placed under `docs/diagrams/plantuml`.

## Notes
- Keep `/api/*` paths compatible with existing Angular services.
- Version endpoints under `/api/v1` with compatibility routing.
- Traefik is optional in dev; use it only when TLS testing is required.
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
