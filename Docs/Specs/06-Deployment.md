# Deployment

## Targets
- Local dev: Docker Compose.
- Self-hosted prod: Docker Compose with Traefik for TLS.

## Containers
- `frontend`: Angular static assets (nginx or lightweight static server).
- `backend`: Django REST API (gunicorn + uvicorn or gunicorn + ASGI).
- `database`: PostgreSQL.
- `proxy`: Traefik (TLS termination and routing).

## Templates
- Docker Compose template: `<repository>/Deployment/templates/docker-compose.template.yml`
- Docker Compose dev template: `<repository>/Deployment/templates/docker-compose.dev.template.yml`
- Traefik template: `<repository>/Deployment/templates/traefik.template.yml`
- Gitignore template: `<repository>/Deployment/templates/.gitignore.template`
- Python tooling template: `<repository>/Deployment/templates/pyproject.template.toml`
- Pre-commit template: `<repository>/Deployment/templates/.pre-commit-config.template.yaml`
- Pytest template: `<repository>/Deployment/templates/pytest.ini.template`
- Bandit template: `<repository>/Deployment/templates/bandit.yaml.template`
- Semgrep template: `<repository>/Deployment/templates/semgrep.yml.template`
- Playwright template: `<repository>/Deployment/templates/playwright.config.template.ts`
- ZAP baseline template: `<repository>/Deployment/templates/zap-baseline.sh.template`

## Python environment
- Use a pinned `requirements.txt` (or `requirements.lock`) in the repo.
- Docker build installs dependencies into a virtual environment or image layer for isolation.

## Environment variables (baseline)
- `DATABASE_URL=postgres://...`
- `DJANGO_SECRET_KEY=...`
- `DJANGO_ALLOWED_HOSTS=...`
- `DJANGO_CORS_ALLOWED_ORIGINS=...`
- `GOOGLE_OAUTH_CLIENT_ID=...`
- `GOOGLE_OAUTH_CLIENT_SECRET=...`
- `SESSION_COOKIE_SECURE=true`
- `CSRF_COOKIE_SECURE=true`

## Configuration files
- Use `.env.template` (committed) to document required variables and defaults.
- Use `.env` (gitignored) as the single source of truth for development values.
- Avoid `.env.local` variants to keep configuration declarative and consistent.
- Production runtime should use an environment file or secrets manager with the same variable names.

## Proxy agnostic behavior
- App should honor `X-Forwarded-*` headers.
- Do not hard-code hostnames or TLS assumptions.

## Traefik notes
- Provide labels for `/` -> frontend and `/api` -> backend routing.
- Use LetsEncrypt ACME TLS and HTTP-01 or DNS-01 challenge.

## Database migrations
- Use Django migrations only.
- Migrations run on deploy and before app starts.

## Backups
- Nightly database dump to local disk or mounted volume.
- Manual restore procedure documented and tested.

## Diagram references
- Current proxy flow: `2025Fall-Team22-EE-Lab-Personal/Migration Notes/diagrams-wsd/uml/uml-frontend-backend-map.wsd`

## Sources
- `Migration Notes/Known Issues.md`
- `Migration Notes/Personal Audit.md`
- `Migration Notes/Performance Review.md`
- `Migration Notes/dev_guide_extracted.md`
- `Migration Notes/user_guide_extracted.md`
- `Migration Notes/deployment_guide_extracted.md`
- `2025Fall-Team22-EE-Lab-Personal/Migration Notes/Diagrams-Index.md`
