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
task auto-deploy:on
task auto-deploy:off
task auto-deploy:status
```

## 5) Toggleable Auto-Deploy

The repo owns a toggleable prod auto-deploy installation:

- `scripts/tasks/auto-deploy.sh`
- `scripts/tasks/auto-deploy-run.sh`
- `Deployment/templates/eelab-auto-deploy.cron.template`

`task auto-deploy:on` installs:

- `/opt/deploy/auto-deploy.sh`
- `/etc/cron.d/eelab-auto-deploy`

These commands are intended for the server checkout. When run as a non-root user they escalate with `sudo` to install into `/opt/deploy` and `/etc/cron.d`.

The installed runner:

- fetches `origin/master` by default (`AUTO_DEPLOY_BRANCH` may override this)
- refuses to run if the server checkout has uncommitted or untracked files
- hard-resets the server checkout to the fetched revision only after confirming the repo is clean
- runs `task env:init`
- runs `task rebuild:prod`
- rolls back to the previous revision if rebuild fails
- writes output to `/opt/deploy/deploy.log`

`task auto-deploy:off` removes only the cron entry so the next team can re-enable it instantly without re-provisioning the deploy key or runner.

## 6) Volume and Routing Isolation

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
