# Deployment Templates

Template files for local development, CI checks, and deployment scaffolding.
Copy a template, remove the `.template` suffix, and adjust values as needed.

## Index
- `.gitignore.template`: Suggested ignore rules for local/dev-only artifacts (includes OTEL trace file).
- `.pre-commit-config.template.yaml`: Pre-commit hooks for lint/format checks.
- `bandit.yaml.template`: Bandit configuration for Python security scanning.
- `docker-compose.dev.template.yml`: Development compose stack with hot reload.
- `docker-compose.template.yml`: Baseline compose stack (production-oriented).
- `playwright.config.template.ts`: Playwright E2E test configuration.
- `pyproject.template.toml`: Python tooling config (deps, lint, format).
- `pytest.ini.template`: Pytest defaults (markers, paths, options).
- `semgrep.yml.template`: Semgrep ruleset config for static analysis.
- `traefik.template.yml`: Traefik proxy config (routing, entrypoints).
- `zap-baseline.sh.template`: OWASP ZAP baseline scan script.
