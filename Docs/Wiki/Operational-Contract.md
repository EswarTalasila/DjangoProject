# Operational Contract

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Scope** | Permanent runtime, task, env, compose, proxy, media, and test contract |
| **Applies To** | `Taskfile.yml`, `scripts/tasks/*`, `scripts/coverage/*`, `docker/*`, `proxy/*`, env generation, deployment |
| **Related FRs** | FR-12, FR-13, FR-15, FR-16 |

---

## 1) Purpose

This document is the permanent repo-owned version of the operational contract that was originally worked out in the external `Prompt.md` planning file.

It exists so that:

- the task/runtime design is preserved in-repo
- future work can reuse the contract without depending on a scratch prompt file
- implementation changes can be reviewed against one stable source of truth

If implementation and this contract disagree, implementation should be treated as wrong unless this document is intentionally updated first.

---

## 2) Core Rules

- Task commands must be literal.
- Public commands must do exactly what their names say they do.
- Hidden side effects are not allowed.
- The public task surface stays intentionally small.
- If a task family is not explicitly kept here, it should be removed or replaced.
- Browser traffic and SSR traffic both go through the shared proxy.
- Root `.env` is the only human-edited env source.
- Generated profile env files are runtime artifacts, not source of truth.
- Bytes for uploaded files live on the filesystem; metadata, ownership, and bindings live in the database.

---

## 3) Public Task Surface

### Environment

- `task env:local`
- `task env:server`
- `task env:init`

### Startup / Shutdown

- `task up:dev`
- `task up:test`
- `task up:prod`
- `task down:dev`
- `task down:test`
- `task down:prod`

### Runtime

- `task status:dev`
- `task status:test`
- `task status:prod`
- `task logs:dev`
- `task logs:test`
- `task logs:prod`
- `task restart:dev`
- `task restart:test`
- `task restart:prod`
- `task rebuild:dev`
- `task rebuild:test`
- `task rebuild:prod`

### Testing

- `task test`
- `task test:backend`
- `task test:frontend`

### Destructive

- `task destroy:all`

### Help

- `task help` stays and should remain grouped, clear, and useful.

No other public task families are part of the kept operational surface.

---

## 4) Internal Task and Script Conventions

Internal task meanings:

- `_check:*` validates only
- `_ensure:*` creates or fixes state until valid

Primary script entry points:

- `./scripts/tasks/set-env-target.sh <local|server>`
- `./scripts/tasks/prepare-env.sh <dev|test|prod|all|init>`
- `./scripts/tasks/check-env.sh <dev|test|prod>`
- `./scripts/tasks/up.sh <proxy|dev|test|prod>`
- `./scripts/tasks/down.sh <dev|test|prod>`
- `./scripts/tasks/status.sh <dev|test|prod>`
- `./scripts/tasks/logs.sh <dev|test|prod>`
- `./scripts/tasks/restart.sh <dev|test|prod>`
- `./scripts/tasks/rebuild.sh <dev|test|prod>`
- `./scripts/tasks/test.sh <all|backend|frontend>`
- `./scripts/tasks/destroy-all.sh`

The `Taskfile.yml` layer stays thin. Real workflow logic belongs under `scripts/tasks/*`.

---

## 5) Env Model

### Canonical Inputs

- `.env.template`
- `.env`
- `scripts/config/env_policy.yml`

### Generated Runtime Artifacts

- `env/.env.development`
- `env/.env.testing`
- `env/.env.production`

### Ownership Rules

- `.env` is the serious canonical input file.
- `.env.template` is the only checked-in env template.
- `.env.bak` is a temporary gitignored backup file.
- Generated `env/.env.*` files are disposable runtime files and are not manually edited.

### `env:local` / `env:server`

`task env:local` and `task env:server`:

- ensure root `.env` exists
- set topology intent in root `.env`
- preserve all non-topology values already present

These commands do not generate runtime env files by themselves.

### `env:init`

`task env:init`:

1. ensures root `.env` exists
2. creates it from `.env.template` if missing
3. stops and asks the developer to fill it out if a new root `.env` was created
4. verifies root `.env` against `.env.template`
5. prefers a key-preserving merge when template keys were added
6. if a safe merge cannot be done, replaces root `.env` from template and writes the old file to `.env.bak`
7. writes or rewrites all generated runtime env files

The only retained backup file is the most recent `.env.bak`.

### Local vs Server

Local and server are not different configuration philosophies.

They are the same architecture with different topology inputs, such as:

- host: `localhost` vs real domain
- scheme and TLS expectations
- production strictness

The system must work locally with the same proxy-driven routing model:

- dev: `localhost:8080` and `localhost:8443`
- test: `localhost:9080` and `localhost:9443`

---

## 6) Env Validation Policy

Env validation is policy-driven through `env_policy.yml` and `check-env.sh`.

Validation stages:

1. required keys exist
2. rendered values do not still match forbidden placeholders for that profile
3. field-specific criteria pass
4. topology-derived values match the expected profile origin model

Profile enforcement:

- `dev`: warnings allowed
- `test`: warnings allowed
- `prod`: fail hard

This applies to security-sensitive keys and topology-sensitive keys alike.

### Allowed Hosts / CORS / CSRF

These settings must be derived from the real public origin for the profile.

- `DJANGO_ALLOWED_HOSTS`: host-based acceptance
- `DJANGO_CORS_ALLOWED_ORIGINS`: browser cross-origin JavaScript access
- `DJANGO_CSRF_TRUSTED_ORIGINS`: trusted origins for authenticated write requests

Production validation must fail when these values:

- still contain placeholders
- contain `localhost` or `127.0.0.1`
- contain internal service names
- do not match the expected public host/origin for the active topology

Dev and test may allow localhost-derived values.

---

## 7) Compose and Profile Contract

### Compose Files

- `docker/compose.proxy.yml`
- `docker/compose.dev.yml`
- `docker/compose.test.yml`
- `docker/compose.prod.yml`

The repo does not use one profile-driven mega-compose anymore.

### Compose Projects

- `eelab-proxy`
- `eelab-dev`
- `eelab-test`
- `eelab-prod`

`container_name` should not be used.

### Services

Proxy stack:

- `proxy`

App stacks:

- `db`
- `backend`
- `frontend`

No OTEL, Jaeger, Playwright, or E2E sidecars are part of the active contract.

### Networks

- shared external proxy network: `eelab-proxy`
- per-profile private app network:
  - `eelab-dev-app`
  - `eelab-test-app`
  - `eelab-prod-app`

### Volumes

- `eelab-dev-db-data`
- `eelab-dev-media-data`
- `eelab-dev-artifact-data`
- `eelab-test-db-data`
- `eelab-test-media-data`
- `eelab-test-artifact-data`
- `eelab-prod-db-data`
- `eelab-prod-media-data`
- `eelab-prod-artifact-data`

Each profile owns only its own data.

### Ports

- prod: `80` and `443`
- dev: `8080` and `8443`
- test: `9080` and `9443`

### Proxy Aliases

- `eelab-dev-backend`
- `eelab-dev-frontend`
- `eelab-test-backend`
- `eelab-test-frontend`
- `eelab-prod-backend`
- `eelab-prod-frontend`

Implementation should match these names unless this contract changes.

---

## 8) Proxy and Routing Contract

The shared proxy owns ingress.

It is responsible for:

- routing
- TLS termination
- header forwarding
- websocket forwarding when needed

It is not responsible for:

- media file serving
- hidden bootstrap logic
- app-stack lifecycle ownership

Routing intent:

- `80/443` -> prod
- `8080/8443` -> dev
- `9080/9443` -> test

Within each profile route:

- `/api/v1/` -> backend
- `/admin/` -> backend
- `/static/` -> backend
- `/` -> frontend

Both browser traffic and SSR traffic go through proxy. No direct frontend-to-backend bypass is part of the kept model.

---

## 9) Startup and Shutdown Semantics

### `up:*`

`task up:<profile>` is non-destructive.

It may:

- create missing containers
- start stopped containers
- reconcile app services via normal compose behavior

It must not:

- delete DB/media/artifact volumes
- perform hidden cleanup
- silently hide broken states

State model:

- `missing`
- `stopped`
- `running_healthy`
- `running_unhealthy`
- `partial`
- `broken`

Success means the required services for the profile are healthy, not merely present.

### `down:*`

`task down:<profile>` is non-destructive.

It:

- stops and removes only that profile stack
- preserves volumes
- preserves DB/media/artifact data
- does not implicitly tear down proxy

### Destroy

`destroy:all` is the only kept full wipe command.

It must:

- require the operator to type `EELAB` at an interactive confirmation prompt
- act only on EElab-owned Docker state
- never be used as an implicit fallback by normal commands

---

## 10) Media and Artifact Contract

### Storage Model

- image bytes live on the filesystem
- image metadata and bindings live in the database
- generated artifacts are not part of the image domain

### Instance-Scoped Roots

- `/srv/eelab-dev/media`
- `/srv/eelab-test/media`
- `/srv/eelab-prod/media`

### Namespaces

- `images/questions`
- `images/submissions`
- `artifacts/packages`
- `artifacts/snapshots`

### Storage Keys

- question images: `questions/<question_id>/<blob_sha256>.<ext>`
- submission images: `submissions/<submission_id>/<blob_sha256>.<ext>`

### Serving Model

Protected image reads are backend-streamed for both question and submission flows.

The proxy does not mount or serve per-instance media bytes in the active model.

### Domain Rules

The image system is unified, but bindings remain context-specific:

- question/template image bindings
- submission image bindings

Uploads share one core image pipeline:

- validate
- normalize
- hash
- store bytes
- create/reuse blob metadata
- create context binding
- return normalized API DTO with a real `url`

Delete/archive behavior is binding-aware. Physical blob deletion only happens when no active bindings remain.

---

## 11) Testing and Coverage Contract

Tests run against the testing stack, never the dev stack.

Public commands:

- `task test`
- `task test:backend`
- `task test:frontend`

### Ownership Split

- `scripts/tasks/test.sh` owns orchestration
- `scripts/tasks/lib/pytest_runner.py` owns backend pretty pytest output
- `scripts/coverage/coverage_report.py` owns coverage reporting only

Coverage is a final reporting step after task-driven test execution. It is not the hidden owner of test orchestration.

Retained behavior:

- readable live backend test output
- aligned/colorized result rows
- final coverage tables
- final FR traceability reporting

Coverage/report correctness should be maintained as a separate concern from test orchestration.

---

## 12) Legacy Removals

The following classes of legacy behavior are intentionally removed from the active operational model:

- OTEL and Jaeger runtime dependencies
- Playwright / E2E task and startup wiring
- monolithic `docker-compose.yml`
- per-profile env templates
- hidden runtime bootstrap scripts that mix startup with migrations/seeding
- oversized public task families
- stray convenience commands not explicitly kept in this contract

If a future change reintroduces one of these areas, it should be added back deliberately and documented here first.

---

## 13) Maintenance Rule

This page is the permanent operational contract.

When future work touches:

- task commands
- env generation or validation
- compose/proxy topology
- media serving/storage
- testing orchestration

the implementation should be reviewed against this document, and this document should be updated in the same change if the contract intentionally changes.
