# Development Setup

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Scope** | Local developer startup and profile env workflow |

---

## 1) Initialize Environment Files

```bash
task env:init
```

This creates missing runtime env files (gitignored):

- `env/.env.development`
- `env/.env.testing`
- `env/.env.production`

Edit values as needed for your machine.

## 2) Start Profiles

### Development (minimal)

```bash
task up:dev
```

Runs:

- `database`
- `backend`
- `frontend`

### Testing (full validation stack)

```bash
task up:test
```

Runs:

- `database`
- `backend`
- `frontend`
- `pgadmin`
- `otel-collector`
- `jaeger`

## 3) Readiness and Diagnostics

Startup tasks run `scripts/runtime/profile_guard.py` to verify backend diagnostics before continuing.

Testing commands also wait for backend readiness in the testing profile before running pytest.

## 4) Stop Services

```bash
task down
```

Stops all profile stacks and removes orphans.
