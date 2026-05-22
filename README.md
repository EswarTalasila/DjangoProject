# Lattice Data Dashboard

This repo now uses one explicit task surface, one canonical root `.env`, four compose files, and a shared proxy that handles all browser and SSR traffic for `dev`, `test`, and `prod`.

## Quick Start

1. Install Docker, Docker Compose, and [Task](https://taskfile.dev/).
2. Choose topology and bootstrap env files:

```bash
task env:local
task env:init
```

3. Edit root `.env` with the serious values that matter for your machine.
4. Start the development stack:

```bash
task up:dev
```

5. Open the application through proxy:
- Dev: `https://localhost/_dev/login`

Testing and production use the same proxy model:
- Test: `https://localhost/_test/login`
- Prod HTTP/HTTPS: `http://<host>` / `https://<host>`

## Environment Model

- The only human-edited env file is root `.env`.
- `task env:local` and `task env:server` set topology fields in root `.env`.
- `task env:init` verifies root `.env` against `.env.template` and rewrites:
  - `env/.env.development`
  - `env/.env.testing`
  - `env/.env.production`
- Generated env files are runtime artifacts. Do not edit them directly.

Development and testing can use policy-defined weak defaults. Production is rendered from root `.env` and fails startup if placeholders or weak values remain.

## Task Surface

Run `task help` for the grouped command guide. The public command surface is intentionally small:

- `task env:local`
- `task env:server`
- `task env:init`
- `task up:dev`
- `task up:test`
- `task up:prod`
- `task down:dev`
- `task down:test`
- `task down:prod`
- `task status:dev|test|prod`
- `task logs:dev|test|prod`
- `task restart:dev|test|prod`
- `task rebuild:dev|test|prod`
- `task test`
- `task test:backend`
- `task test:frontend`
- `task seed:account -- <all|researcher|teacher|student> [--profile dev|test]`
- `task seed:data -- [--profile dev|test]`
- `task destroy:all`

## Compose Layout

The repo no longer uses one profile-driven mega-compose. The active files are:

- `docker/compose.proxy.yml`
- `docker/compose.dev.yml`
- `docker/compose.test.yml`
- `docker/compose.prod.yml`

Compose project names:

- `lattice-proxy`
- `lattice-dev`
- `lattice-test`
- `lattice-prod`

Each app stack owns its own DB/media/artifact volumes. Only the shared proxy owns the public ports.

## Testing

Tests run against the testing stack, not the dev stack:

```bash
task test
task test:backend
task test:frontend
```

`scripts/tasks/test.sh` owns orchestration. Coverage remains under `scripts/coverage` and is run as the final reporting step for task-driven test runs.

## Deterministic Seeding

Seed helpers run against backend services only (`db` + `backend`), defaulting to development:

```bash
task seed:account -- all
task seed:account -- researcher
task seed:data
task seed:account -- teacher --profile test
task seed:data -- --profile test
```

`task seed:account` provisions deterministic role accounts through the real registration pipeline and prints the resulting credentials. `task seed:data` provisions those accounts first, then seeds a fuller deterministic demo dataset. Both commands prepare the selected runtime env, start the required backend services, apply migrations, and ensure the admin bootstrap first.
