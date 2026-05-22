# Task Runner

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Scope** | Task command contract and environment-aware runtime/testing interface |
| **Applies To** | Development workflow, test orchestration, profile startup |
| **Related FRs** | FR-01, FR-02, FR-12, FR-13 |

---

## 1) Purpose

Define a small, literal Task command interface that:
- maps directly to environment profile behavior (`development`, `testing`, `production`)
- keeps orchestration visible in `Taskfile.yml`
- delegates workflow implementation to `scripts/tasks/*`
- removes legacy aliases and task sprawl

---

## 2) Public Command Surface

### Environment

| Command | Intent |
|---|---|
| `task env:local` | Set root `.env` topology for localhost routing |
| `task env:server` | Set root `.env` topology for deployed host/domain routing |
| `task env:init` | Verify root `.env` and rewrite generated runtime env files |

Rules:
- Root `.env` is the only human-edited env source.
- Generated env files are runtime artifacts only:
  - `env/.env.development`
  - `env/.env.testing`
  - `env/.env.production`

### Startup / Shutdown

| Command | Intent |
|---|---|
| `task up:dev` | Validate env, ensure proxy, start dev stack |
| `task up:test` | Validate env, ensure proxy, start test stack |
| `task up:prod` | Validate env, ensure proxy, start prod stack |
| `task down:dev` | Stop dev stack without removing volumes |
| `task down:test` | Stop test stack without removing volumes |
| `task down:prod` | Stop prod stack without removing volumes |

Rules:
- `up:*` is non-destructive by default.
- `down:*` is non-destructive by default.
- Proxy is shared and internal; app stacks do not own ingress.

### Runtime

| Command | Intent |
|---|---|
| `task status:dev|test|prod` | Show stack state |
| `task logs:dev|test|prod` | Follow stack logs |
| `task restart:dev|test|prod` | Restart profile containers |
| `task rebuild:dev|test|prod` | Rebuild/recreate app containers without destroying data |

### Testing

| Command | Intent |
|---|---|
| `task test` | Ensure testing stack and run backend + frontend tests |
| `task test:backend` | Ensure testing stack and run backend tests |
| `task test:frontend` | Ensure testing stack and run frontend tests |

Rules:
- Tests run against the testing stack, never the dev stack.
- `scripts/tasks/test.sh` owns orchestration.
- Coverage is a final reporting concern and stays under `scripts/coverage`.

### Seeding

| Command | Intent |
|---|---|
| `task seed:account -- <all\|researcher\|teacher\|student> [--profile dev\|test]` | Ensure backend services and provision deterministic seeded account(s) |
| `task seed:data -- [--profile dev\|test]` | Ensure backend services and seed the deterministic demo dataset |

Rules:
- Seed tasks run against backend `db` + `backend` services only; the frontend is not required.
- The default profile is `dev`; `--profile test` targets the testing backend stack.
- `scripts/tasks/seed-prepare.sh` owns service startup, migrations, and admin bootstrap.
- `scripts/tasks/seed-account.sh` and `scripts/tasks/seed-data.sh` own wrapper UX and argument validation.
- The underlying source of truth remains the Django management commands:
  - `provision_account`
  - `seed_demo_data`

### Auto-Deploy

| Command | Intent |
|---|---|
| `task auto-deploy:on` | Install/update the prod auto-deploy runner and cron schedule |
| `task auto-deploy:off` | Disable the prod auto-deploy cron schedule without removing keys or logs |
| `task auto-deploy:status` | Show installed state, drift, and recent deploy log lines |

Rules:
- These commands are intended to be run on the server-side checkout, not on normal day-to-day local development machines.
- When not already root they use `sudo` to write into `/opt/deploy` and `/etc/cron.d`.
- The repo owns the source-of-truth runner and cron template.
- `task auto-deploy:on` installs a rendered runtime copy to `/opt/deploy/auto-deploy.sh`.
- `task auto-deploy:on` also installs `/etc/cron.d/lattice-auto-deploy`.
- `task auto-deploy:off` removes only the cron file; it leaves the deploy key, installed runner, and log intact.
- The installed runner fetches `origin/master` by default, but `AUTO_DEPLOY_BRANCH` may override the tracked branch.
- The installed runner refuses to run when the server checkout is dirty.
- The installed runner rolls back to the previous revision if `task env:init` or `task rebuild:prod` fails.
- The deploy key is expected at `/opt/deploy/keys/github_deploy` unless overridden explicitly.

### Destructive

| Command | Intent |
|---|---|
| `task destroy:all` | Wipe all Lattice containers, volumes, and proxy state after interactive confirmation |

Rules:
- The command first requires explicit `y/N` confirmation.
- The command then requires the exact typed phrase `Lattice`.
- No hidden destructive cleanup is allowed in normal startup/shutdown tasks.

---

## 3) Internal Task Conventions

- `_check:*` tasks validate state and may fail fast.
- `_ensure:*` tasks are idempotent and may create/fix required runtime state.
- The actual implementation lives in `scripts/tasks/*`.

Examples:
- `_check:docker`
- `_check:env:dev`
- `_check:env:test`
- `_check:env:prod`
- `_ensure:proxy`
- `_ensure:test-stack`

---

## 4) Stability Rules

- If a task is not explicitly kept in this contract, it should be removed or replaced.
- Legacy aliases such as `task up`, `task down`, `task up:prod:local`, old `docker:*` cleanup wrappers, proxy overlay tasks, OTEL toggles, and E2E task families are not part of the kept public surface.
- `task help` remains the human-facing grouped command index.

---

## 5) Traceability Notes

- FR-12 governs env selection, validation, and startup gating.
- FR-13 governs compose/proxy/runtime orchestration.
- `Diagnostics-Index.md` is the source of truth for env validation diagnostics.
