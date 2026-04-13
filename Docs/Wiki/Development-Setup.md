# Development Setup

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Scope** | Local developer startup and generated env workflow |

---

## 1) Choose Topology and Initialize Env

```bash
task env:local
task env:init
```

This workflow:

- ensures root `.env` exists
- sets localhost topology in root `.env`
- rewrites runtime env files:
  - `env/.env.development`
  - `env/.env.testing`
  - `env/.env.production`

Edit root `.env` only. Do not edit generated profile env files directly.

## 2) Start Profiles

### Development

```bash
task up:dev
```

Runs:

- shared `proxy`
- `db`
- `backend`
- `frontend`

Access through proxy:

- `http://localhost:8080`
- `https://localhost:8443`

### Testing

```bash
task up:test
```

Runs:

- shared `proxy`
- `db`
- `backend`
- `frontend`

Access through proxy:

- `http://localhost:9080`
- `https://localhost:9443`

## 3) Readiness and Validation

Startup tasks:

- check Docker
- prepare generated env files
- validate env policy for the chosen profile
- ensure the shared proxy is running
- start the target stack and wait for health

## 4) Stop Services

```bash
task down:dev
task down:test
```

These commands stop only the requested stack and preserve volumes.
