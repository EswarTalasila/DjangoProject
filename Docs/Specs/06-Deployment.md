# Deployment

## Targets
- Local dev: Docker Compose.
- Self-hosted prod: Docker Compose with the shared nginx proxy stack for TLS and routing.

## Containers
- `frontend`: Angular static assets (nginx or lightweight static server).
- `backend`: Django REST API (gunicorn + uvicorn or gunicorn + ASGI).
- `database`: PostgreSQL.
- `proxy`: shared nginx proxy (TLS termination and routing).

## Templates
- Proxy compose template: `<repository>/Deployment/templates/compose.proxy.template.yml`
- Dev compose template: `<repository>/Deployment/templates/compose.dev.template.yml`
- Test compose template: `<repository>/Deployment/templates/compose.test.template.yml`
- Prod compose template: `<repository>/Deployment/templates/compose.prod.template.yml`
- Gitignore template: `<repository>/Deployment/templates/.gitignore.template`
- Python tooling template: `<repository>/Deployment/templates/pyproject.template.toml`
- Pre-commit template: `<repository>/Deployment/templates/.pre-commit-config.template.yaml`
- Pytest template: `<repository>/Deployment/templates/pytest.ini.template`
- Bandit template: `<repository>/Deployment/templates/bandit.yaml.template`
- Semgrep template: `<repository>/Deployment/templates/semgrep.yml.template`
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

## Proxy behavior
- App should honor `X-Forwarded-*` headers.
- Browser and SSR traffic should both traverse the shared proxy.
- Do not hard-code hostnames or TLS assumptions.

## Shared proxy notes
- Route `/` -> frontend and `/api/v1`, `/admin`, `/static` -> backend.
- Keep dev/test/prod isolated by compose project, proxy alias, and named volumes.

## Database migrations
- Use Django migrations only.
- Keep migrations explicit; app startup should not hide migration execution inside container entrypoints.

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
