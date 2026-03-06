"""FR-13 Infrastructure contract tests.

These tests verify that infrastructure configuration files satisfy the
constraints defined in FR-13 Infrastructure spec. They parse config files
mounted read-only into the backend container and assert structural invariants.

Naming convention per FR-13 Section 8:
  - test_INFRA_UC_##      : use-case coverage
  - test_INFRA_UC_##_E#   : error-path coverage
  - test_INFRA_CN_##      : constraint coverage
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/app")


def _load_yaml(relpath: str) -> dict:
    """Load a YAML file relative to PROJECT_ROOT."""
    path = PROJECT_ROOT / relpath
    if not path.exists():
        pytest.skip(f"{relpath} not mounted (run tests via docker compose)")
    return yaml.safe_load(path.read_text())


def _load_text(relpath: str) -> str:
    path = PROJECT_ROOT / relpath
    if not path.exists():
        pytest.skip(f"{relpath} not mounted")
    return path.read_text()


def _compose_services() -> dict:
    return _load_yaml("docker-compose.yml").get("services", {})


# ---------------------------------------------------------------------------
# INFRA-UC-01 — Startup command sequence
# ---------------------------------------------------------------------------


class TestINFRA_UC_01:
    """Verify backend startup command sequence ordering."""

    def test_INFRA_UC_01_startup_sequence(self):
        """migrate → collectstatic (prod) → ensure_admin → seed_e2e (testing) → runserver."""
        services = _compose_services()
        backend = services.get("backend", {})
        command = backend.get("command", "")

        # Extract the command steps in order
        assert "migrate" in command, "migrate must be in startup sequence"
        assert "ensure_admin" in command, "ensure_admin must be in startup sequence"
        assert "runserver" in command, "runserver must be in startup sequence"

        # Verify ordering: migrate before ensure_admin before runserver
        idx_migrate = command.index("migrate")
        idx_ensure_admin = command.index("ensure_admin")
        idx_runserver = command.index("runserver")
        assert idx_migrate < idx_ensure_admin < idx_runserver, (
            "Startup sequence must be: migrate → ensure_admin → runserver"
        )

        # collectstatic guarded by production check
        assert "collectstatic" in command
        assert "production" in command, "collectstatic must be guarded by production check"

        # seed_e2e guarded by testing check
        assert "seed_e2e" in command
        assert "testing" in command, "seed_e2e must be guarded by testing check"


# ---------------------------------------------------------------------------
# INFRA-UC-01-E4 — Profile guard
# ---------------------------------------------------------------------------


class TestINFRA_UC_01_E4:
    """Verify profile_guard.py functions."""

    def test_INFRA_UC_01_E4_parse_reason_env_error(self):
        """parse_reason extracts ENV-P001 error code from startup logs."""
        from scripts.runtime.profile_guard import parse_reason

        logs = 'ERROR ENV-P001: backend failed startup validation.\n  reason: ADMIN_EMAIL bad'
        result = parse_reason(logs)
        assert "ENV-P001" in result

    def test_INFRA_UC_01_E4_parse_reason_command_error(self):
        """parse_reason extracts the message from a CommandError line."""
        from scripts.runtime.profile_guard import parse_reason

        logs = "CommandError: something went wrong"
        result = parse_reason(logs)
        assert "something went wrong" in result

    def test_INFRA_UC_01_E4_hint_for_admin_email(self):
        """hint_for_reason returns an actionable hint mentioning ADMIN_EMAIL."""
        from scripts.runtime.profile_guard import hint_for_reason

        hint = hint_for_reason("ADMIN_EMAIL is default", "production")
        assert "ADMIN_EMAIL" in hint

    def test_INFRA_UC_01_E4_hint_for_secret_key(self):
        """hint_for_reason returns an actionable hint mentioning DJANGO_SECRET_KEY."""
        from scripts.runtime.profile_guard import hint_for_reason

        hint = hint_for_reason("DJANGO_SECRET_KEY is default", "production")
        assert "DJANGO_SECRET_KEY" in hint


# ---------------------------------------------------------------------------
# INFRA-CN-01 — Service dependency ordering
# ---------------------------------------------------------------------------


class TestINFRA_CN_01:
    """Backend waits for database healthcheck; frontend depends on backend."""

    def test_INFRA_CN_01_backend_depends_on_db_healthy(self):
        """Backend service depends on database with service_healthy condition."""
        services = _compose_services()
        backend_deps = services["backend"].get("depends_on", {})
        assert "database" in backend_deps
        assert backend_deps["database"].get("condition") == "service_healthy"

    def test_INFRA_CN_01_database_healthcheck(self):
        """Database service has a healthcheck using pg_isready."""
        services = _compose_services()
        hc = services["database"].get("healthcheck", {})
        assert hc, "database must have a healthcheck"
        test_cmd = " ".join(hc["test"]) if isinstance(hc["test"], list) else hc["test"]
        assert "pg_isready" in test_cmd

    def test_INFRA_CN_01_frontend_depends_on_backend(self):
        """Frontend service declares a dependency on the backend service."""
        services = _compose_services()
        frontend_deps = services["frontend"].get("depends_on", {})
        # depends_on can be a list or dict
        if isinstance(frontend_deps, list):
            assert "backend" in frontend_deps
        else:
            assert "backend" in frontend_deps


# ---------------------------------------------------------------------------
# INFRA-CN-02 — Postgres version consistency
# ---------------------------------------------------------------------------


class TestINFRA_CN_02:
    """All compose files must use postgres:17-alpine."""

    EXPECTED_PG = "postgres:17-alpine"

    def test_INFRA_CN_02_main_compose(self):
        """Main docker-compose uses postgres:17-alpine for the database image."""
        services = _compose_services()
        assert services["database"]["image"] == self.EXPECTED_PG

    def test_INFRA_CN_02_production_template(self):
        """Production compose template uses postgres:17-alpine for the database image."""
        tmpl = _load_yaml("Deployment/templates/docker-compose.template.yml")
        db_image = tmpl["services"]["database"]["image"]
        assert db_image == self.EXPECTED_PG, f"Production template uses {db_image}"

    def test_INFRA_CN_02_dev_template(self):
        """Dev compose template uses postgres:17-alpine for the database image."""
        tmpl = _load_yaml("Deployment/templates/docker-compose.dev.template.yml")
        db_image = tmpl["services"]["database"]["image"]
        assert db_image == self.EXPECTED_PG, f"Dev template uses {db_image}"


# ---------------------------------------------------------------------------
# INFRA-CN-03 — Environment variable passthrough
# ---------------------------------------------------------------------------


class TestINFRA_CN_03:
    """ENVIRONMENT must be passed to backend in all compose files."""

    def test_INFRA_CN_03_main_compose_environment(self):
        """Main compose passes ENVIRONMENT variable to the backend service."""
        services = _compose_services()
        backend_env = services["backend"].get("environment", [])
        env_str = str(backend_env)
        assert "ENVIRONMENT" in env_str, "ENVIRONMENT must be passed to backend"

    def test_INFRA_CN_03_production_template(self):
        """Production template passes ENVIRONMENT variable to the backend service."""
        tmpl = _load_yaml("Deployment/templates/docker-compose.template.yml")
        backend_env = tmpl["services"]["backend"].get("environment", [])
        env_str = str(backend_env)
        assert "ENVIRONMENT" in env_str, "Production template must pass ENVIRONMENT"

    def test_INFRA_CN_03_dev_template(self):
        """Dev template passes ENVIRONMENT variable to the backend service."""
        tmpl = _load_yaml("Deployment/templates/docker-compose.dev.template.yml")
        backend_env = tmpl["services"]["backend"].get("environment", [])
        env_str = str(backend_env)
        assert "ENVIRONMENT" in env_str, "Dev template must pass ENVIRONMENT"


# ---------------------------------------------------------------------------
# INFRA-CN-04 — Hot reload support
# ---------------------------------------------------------------------------


class TestINFRA_CN_04:
    """Volume mounts enable hot reload for backend and frontend."""

    def test_INFRA_CN_04_backend_source_mount(self):
        """Backend source directory is volume-mounted for hot reload."""
        services = _compose_services()
        volumes = services["backend"].get("volumes", [])
        vol_str = str(volumes)
        assert "/app/src" in vol_str, "Backend src must be volume-mounted for hot reload"

    def test_INFRA_CN_04_frontend_source_mount(self):
        """Frontend directory is volume-mounted for hot reload."""
        services = _compose_services()
        volumes = services["frontend"].get("volumes", [])
        vol_str = str(volumes)
        assert "/app" in vol_str, "Frontend must be volume-mounted for hot reload"

    def test_INFRA_CN_04_frontend_named_node_modules(self):
        """A named volume for frontend node_modules exists in the compose file."""
        compose = _load_yaml("docker-compose.yml")
        volumes = compose.get("volumes", {})
        assert "frontend_node_modules" in volumes, (
            "Named volume for node_modules must exist"
        )


# ---------------------------------------------------------------------------
# INFRA-CN-05 — Pre-commit hook coverage
# ---------------------------------------------------------------------------


class TestINFRA_CN_05:
    """Pre-commit hooks enforce lint, format, hygiene, and branch guard."""

    def _hook_ids(self) -> list[str]:
        config = _load_yaml(".pre-commit-config.yaml")
        ids = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                ids.append(hook["id"])
        return ids

    def test_INFRA_CN_05_ruff_lint(self):
        """Pre-commit config includes the ruff linter hook."""
        assert "ruff" in self._hook_ids()

    def test_INFRA_CN_05_ruff_format(self):
        """Pre-commit config includes the ruff formatter hook."""
        assert "ruff-format" in self._hook_ids()

    def test_INFRA_CN_05_large_file_guard(self):
        """Pre-commit config includes the large file guard hook."""
        assert "check-added-large-files" in self._hook_ids()

    def test_INFRA_CN_05_trailing_whitespace(self):
        """Pre-commit config includes the trailing whitespace hook."""
        assert "trailing-whitespace" in self._hook_ids()

    def test_INFRA_CN_05_eof_fixer(self):
        """Pre-commit config includes the end-of-file fixer hook."""
        assert "end-of-file-fixer" in self._hook_ids()

    def test_INFRA_CN_05_yaml_check(self):
        """Pre-commit config includes the YAML syntax check hook."""
        assert "check-yaml" in self._hook_ids()

    def test_INFRA_CN_05_toml_check(self):
        """Pre-commit config includes the TOML syntax check hook."""
        assert "check-toml" in self._hook_ids()

    def test_INFRA_CN_05_branch_guard(self):
        """Pre-commit config includes the no-commit-to-branch guard hook."""
        assert "no-commit-to-branch" in self._hook_ids()

    def test_INFRA_CN_05_ruff_scoped_to_backend(self):
        """Ruff hooks are scoped to the backend directory only."""
        config = _load_yaml(".pre-commit-config.yaml")
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                if hook["id"] in ("ruff", "ruff-format"):
                    assert hook.get("files", "").startswith("^backend"), (
                        f"Hook {hook['id']} must scope to ^backend/"
                    )


# ---------------------------------------------------------------------------
# INFRA-CN-07 — Docker image pinning
# ---------------------------------------------------------------------------


class TestINFRA_CN_07:
    """Core images pinned; :latest prohibited for database and E2E."""

    def test_INFRA_CN_07_database_pinned(self):
        """Database image is pinned to a specific version, not :latest."""
        services = _compose_services()
        img = services["database"]["image"]
        assert ":latest" not in img, f"Database image must be pinned, got {img}"
        assert "17" in img

    def test_INFRA_CN_07_e2e_pinned(self):
        """E2E image is pinned to a specific Playwright version, not :latest."""
        services = _compose_services()
        img = services["frontend-e2e"]["image"]
        assert ":latest" not in img, f"E2E image must be pinned, got {img}"
        assert "playwright" in img.lower() or "mcr.microsoft.com" in img

    def test_INFRA_CN_07_otel_collector_pinned(self):
        """OTel Collector image is pinned to version 0.120.0."""
        services = _compose_services()
        img = services["otel-collector"]["image"]
        assert ":latest" not in img
        assert "0.120.0" in img, f"OTel Collector must be pinned to 0.120.0, got {img}"

    def test_INFRA_CN_07_jaeger_pinned(self):
        """Jaeger image is pinned to version 1.76."""
        services = _compose_services()
        img = services["jaeger"]["image"]
        assert ":latest" not in img
        assert "1.76" in img, f"Jaeger must be pinned to 1.76, got {img}"


# ---------------------------------------------------------------------------
# INFRA-CN-08 — Multi-stage build
# ---------------------------------------------------------------------------


class TestINFRA_CN_08:
    """Backend Dockerfile uses multi-stage build with non-root user."""

    def test_INFRA_CN_08_multi_stage(self):
        """Backend Dockerfile has at least two stages with a builder stage."""
        dockerfile = _load_text("Dockerfile")
        from_lines = [l for l in dockerfile.splitlines() if l.strip().startswith("FROM")]
        assert len(from_lines) >= 2, "Dockerfile must have at least 2 stages"
        assert any("AS builder" in l or "as builder" in l for l in from_lines), (
            "First stage must be named 'builder'"
        )

    def test_INFRA_CN_08_non_root_user(self):
        """Production Dockerfile stage runs as non-root django user."""
        dockerfile = _load_text("Dockerfile")
        assert "USER django" in dockerfile, "Production stage must run as non-root user"

    def test_INFRA_CN_08_gunicorn_default(self):
        """Production Dockerfile defaults to gunicorn as the application server."""
        dockerfile = _load_text("Dockerfile")
        assert "gunicorn" in dockerfile, "Production default must use Gunicorn"


# ---------------------------------------------------------------------------
# INFRA-CN-09 — Compose profile-based service activation
# ---------------------------------------------------------------------------


class TestINFRA_CN_09:
    """Optional services use profiles; core services start without flags."""

    def test_INFRA_CN_09_e2e_profile(self):
        """E2E service is gated behind the 'e2e' compose profile."""
        services = _compose_services()
        profiles = services["frontend-e2e"].get("profiles", [])
        assert "e2e" in profiles

    def test_INFRA_CN_09_proxy_profile(self):
        """Nginx proxy service is gated behind the 'proxy' compose profile."""
        services = _compose_services()
        profiles = services["nginx"].get("profiles", [])
        assert "proxy" in profiles

    def test_INFRA_CN_09_core_services_no_profile(self):
        """Core services (database, backend, frontend, pgadmin) have no profile restrictions."""
        services = _compose_services()
        for svc_name in ("database", "backend", "frontend", "pgadmin"):
            profiles = services[svc_name].get("profiles", [])
            assert not profiles, f"Core service {svc_name} must not have profiles"


# ---------------------------------------------------------------------------
# INFRA-UC-05 — OTel Collector + Jaeger services
# ---------------------------------------------------------------------------


class TestINFRA_UC_05:
    """Observability infrastructure services and collector config."""

    def test_INFRA_UC_05_collector_service_exists(self):
        """OTel Collector service is defined in docker-compose."""
        services = _compose_services()
        assert "otel-collector" in services

    def test_INFRA_UC_05_jaeger_service_exists(self):
        """Jaeger service is defined in docker-compose."""
        services = _compose_services()
        assert "jaeger" in services

    def test_INFRA_UC_05_collector_ports(self):
        """OTel Collector exposes gRPC (4317) and HTTP (4318) ports."""
        services = _compose_services()
        ports = services["otel-collector"].get("ports", [])
        port_str = str(ports)
        assert "4317" in port_str, "Collector must expose gRPC port 4317"
        assert "4318" in port_str, "Collector must expose HTTP port 4318"

    def test_INFRA_UC_05_jaeger_ui_port(self):
        """Jaeger exposes its UI on port 16686."""
        services = _compose_services()
        ports = services["jaeger"].get("ports", [])
        port_str = str(ports)
        assert "16686" in port_str, "Jaeger must expose UI port 16686"

    def test_INFRA_UC_05_collector_config_valid(self):
        """Collector config has OTLP receiver, Jaeger exporter, and traces pipeline."""
        config = _load_yaml("otel-collector-config.yaml")
        # Verify OTLP receiver
        receivers = config.get("receivers", {})
        assert "otlp" in receivers, "Collector must have OTLP receiver"

        # Verify exporter pipeline exists
        exporters = config.get("exporters", {})
        assert any("jaeger" in k for k in exporters), (
            "Collector must export to Jaeger"
        )

        # Verify traces pipeline
        pipelines = config.get("service", {}).get("pipelines", {})
        assert "traces" in pipelines, "Collector must define traces pipeline"

    def test_INFRA_UC_05_backend_otlp_endpoint_default(self):
        """Backend OTEL_EXPORTER_OTLP_ENDPOINT defaults to the otel-collector service."""
        services = _compose_services()
        backend_env = services["backend"].get("environment", [])
        endpoint_found = False
        for entry in backend_env:
            if "OTEL_EXPORTER_OTLP_ENDPOINT" in str(entry):
                assert "otel-collector" in str(entry), (
                    "Backend OTLP endpoint must default to otel-collector service"
                )
                endpoint_found = True
                break
        assert endpoint_found, "OTEL_EXPORTER_OTLP_ENDPOINT must be in backend env"

    def test_INFRA_UC_05_collector_on_network(self):
        """OTel Collector is attached to the eel-network."""
        services = _compose_services()
        networks = services["otel-collector"].get("networks", [])
        net_str = str(networks)
        assert "eel-network" in net_str, "Collector must be on eel-network"

    def test_INFRA_UC_05_jaeger_on_network(self):
        """Jaeger is attached to the eel-network."""
        services = _compose_services()
        networks = services["jaeger"].get("networks", [])
        net_str = str(networks)
        assert "eel-network" in net_str, "Jaeger must be on eel-network"


# ---------------------------------------------------------------------------
# INFRA-CN-10 — Taskfile precondition checks (profile_guard integration)
# ---------------------------------------------------------------------------


class TestINFRA_CN_10:
    """Profile guard produces actionable hints for common failures."""

    def test_INFRA_CN_10_hint_admin_password(self):
        """hint_for_reason returns a specific hint for ADMIN_PASSWORD failures."""
        from scripts.runtime.profile_guard import hint_for_reason

        hint = hint_for_reason("ADMIN_PASSWORD is default", "production")
        assert "ADMIN_PASSWORD" in hint
        assert len(hint) > 10  # Not a generic fallback

    def test_INFRA_CN_10_hint_database_url(self):
        """hint_for_reason returns a specific hint for DATABASE_URL failures."""
        from scripts.runtime.profile_guard import hint_for_reason

        hint = hint_for_reason("DATABASE_URL uses defaults", "production")
        assert "DATABASE_URL" in hint

    def test_INFRA_CN_10_hint_otel(self):
        """hint_for_reason returns a specific hint for OTEL-related failures."""
        from scripts.runtime.profile_guard import hint_for_reason

        hint = hint_for_reason("OTEL endpoint missing", "production")
        assert "OTEL" in hint

    def test_INFRA_CN_10_hint_generic_fallback(self):
        """hint_for_reason returns a generic fallback hint for unknown reasons."""
        from scripts.runtime.profile_guard import hint_for_reason

        hint = hint_for_reason("unknown issue", "development")
        assert "development" in hint
