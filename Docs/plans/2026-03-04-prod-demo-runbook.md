# Production Demo Runbook (task up:prod)

## Goal
Run a production-like stack with only:
- `database`
- `backend-prod`
- `frontend-prod`
- `nginx-prod`

All browser traffic goes through Nginx on port `80`.

## Prerequisites
- Docker + Docker Compose installed
- `.env` present and set for production-safe values
- User can run Docker commands (in `docker` group on server)

## Required `.env` values
At minimum:
- `ENVIRONMENT=production`
- `POSTGRES_DB` (non-default)
- `POSTGRES_USER` (non-default)
- `POSTGRES_PASSWORD` (strong)
- `DATABASE_URL=postgres://<user>:<password>@database:5432/<db>`
- `DJANGO_SECRET_KEY` (strong random)
- `DJANGO_ALLOWED_HOSTS` (real hostnames, no localhost)
- `DJANGO_CORS_ALLOWED_ORIGINS` (trusted origins, no localhost/wildcard)
- `ADMIN_EMAIL` (non-default)
- `ADMIN_PASSWORD` (>=12 chars, non-default)
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
- `NEXT_PUBLIC_API_URL=/api/v1`

## Start
```bash
task down
task up:prod
```

## Validate
```bash
task audit:prod
curl -I http://localhost/
curl -I http://localhost/api/v1/health
```

Expected:
- `/` proxied to frontend
- `/api/v1/*` proxied to backend
- no direct host ports for backend/frontend in prod services

## Logs
```bash
docker compose logs -f backend-prod frontend-prod nginx-prod
```

## Stop
```bash
task down
```

## Notes
- Frontend uses Next.js standalone production image (`frontend/Dockerfile.prod`).
- Build-time public env is injected for Next.js (`NEXT_PUBLIC_*`).
- Package/image uploads via X-Accel-Redirect are supported in prod through mounted `media_data` volume.
