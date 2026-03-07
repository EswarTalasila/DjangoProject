# Environment Files

Use profile-scoped env files instead of exporting `ENVIRONMENT` in shell commands.

## Files

- `env/.env.development` (runtime, gitignored)
- `env/.env.testing` (runtime, gitignored)
- `env/.env.production` (runtime, gitignored)

Templates:

- `env/.env.development.template`
- `env/.env.testing.template`
- `env/.env.production.template`

## Bootstrap

Run:

```bash
task env:init
```

This creates missing runtime files from templates.

To force-refresh runtime files from templates:

```bash
task env:reset
```

## Profile Mapping

- `task up:dev` -> `env/.env.development`
- `task up:test` -> `env/.env.testing`
- `task up:prod` -> `env/.env.production`

## Notes

- Runtime files are intentionally gitignored.
- `.env.template` at the repo root remains as a compatibility reference.
- If profile DB credentials differ and you switch profiles on the same Docker volume,
  Postgres auth can fail. Either keep DB credentials aligned across profile files or
  run `task docker:volume-clean` before switching.
