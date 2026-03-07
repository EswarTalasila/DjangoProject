# Deployment

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Scope** | Production profile container startup and env contract |

---

## 1) Production Profile Contract

`task up:prod` runs only runtime services:

- `database`
- `backend-prod`
- `frontend-prod`
- `nginx-prod`

No pgAdmin, Jaeger, OTel collector, or E2E containers.

## 2) Production Env File

Production startup uses:

- `env/.env.production`

Create it with:

```bash
task env:init
```

Then update required values:

- `DJANGO_SECRET_KEY`
- `POSTGRES_*` + `DATABASE_URL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`

## 3) Startup Behavior

`backend-prod` startup runs:

1. `migrate`
2. `collectstatic`
3. `ensure_admin`
4. `gunicorn`

No test seeding runs in production.

## 4) Commands

```bash
task up:prod
task down:prod
```

## 5) Local Profile Switching Note

If you switch between `testing` and `production` using the same Docker Postgres volume
while changing DB credentials between env files, backend startup can fail with DB auth
errors. Keep credentials aligned across profile env files, or run:

```bash
task docker:volume-clean
```
