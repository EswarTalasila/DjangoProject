# Deployment Templates

Template files for deployment scaffolding and developer tooling.
Copy a template, remove the `.template` suffix, and adjust values as needed.

## Index
- `.gitignore.template`: Suggested ignore rules for local/dev-only artifacts.
- `.pre-commit-config.template.yaml`: Pre-commit hooks for lint/format checks.
- `bandit.yaml.template`: Bandit configuration for Python security scanning.
- `compose.proxy.template.yml`: Shared proxy stack template.
- `compose.dev.template.yml`: Development stack template.
- `compose.test.template.yml`: Testing stack template.
- `compose.prod.template.yml`: Production stack template.
- `pyproject.template.toml`: Python tooling config (deps, lint, format).
- `pytest.ini.template`: Pytest defaults (markers, paths, options).
- `semgrep.yml.template`: Semgrep ruleset config for static analysis.
- `zap-baseline.sh.template`: OWASP ZAP baseline scan script.
