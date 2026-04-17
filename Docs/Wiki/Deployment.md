# Deployment

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Scope** | Production stack startup and env contract |

---

## 1) Production Profile Contract

`task up:prod` runs:

- shared `proxy`
- `db`
- `backend`
- `frontend`

The production app stack does not own ingress directly. Browser and SSR traffic still go through the shared proxy.

## 2) Production Env Workflow

Production uses:

- root `.env` as canonical source
- generated `env/.env.production` as runtime artifact

Prepare it with:

```bash
task env:server
task env:init
```

Then set serious root `.env` values, rerun `task env:init`, and validate with `task up:prod`.

Required production values include:

- `DJANGO_SECRET_KEY`
- `POSTGRES_*`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

## 3) Startup Behavior

`task up:prod` is non-destructive:

- it prepares and validates env first
- it ensures the shared proxy exists
- it runs `docker compose ... up -d` for the prod stack
- it refuses startup when production placeholders or weak values remain
- it preserves DB, media, and artifact volumes

## 4) Commands

```bash
task up:prod
task down:prod
```

## 5) Volume and Routing Isolation

Production data is isolated by:

- compose project `eelab-prod`
- network `eelab-prod-app`
- volumes:
  - `eelab-prod-db-data`
  - `eelab-prod-media-data`
  - `eelab-prod-artifact-data`

The shared proxy owns public ports and routes `80/443` to:

- `eelab-prod-backend`
- `eelab-prod-frontend`
