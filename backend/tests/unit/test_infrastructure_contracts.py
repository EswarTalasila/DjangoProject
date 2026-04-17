"""Infrastructure contract tests for the rebuilt task/compose model."""

from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path("/app")


def _load_yaml(relpath: str) -> dict:
    path = PROJECT_ROOT / relpath
    assert path.exists(), f"{relpath} must exist"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_text(relpath: str) -> str:
    path = PROJECT_ROOT / relpath
    assert path.exists(), f"{relpath} must exist"
    return path.read_text(encoding="utf-8")


def _services(relpath: str) -> dict:
    return _load_yaml(relpath).get("services", {})


class TestTaskSurface:
    """The public Task surface must match the prompt contract."""

    def test_public_task_surface_kept(self):
        """All prompt-specified public task targets exist in Taskfile.yml."""
        taskfile = _read_text("Taskfile.yml")
        for task_name in [
            "env:local:",
            "env:server:",
            "env:init:",
            "up:dev:",
            "up:test:",
            "up:prod:",
            "down:dev:",
            "down:test:",
            "down:prod:",
            "status:dev:",
            "status:test:",
            "status:prod:",
            "logs:dev:",
            "logs:test:",
            "logs:prod:",
            "restart:dev:",
            "restart:test:",
            "restart:prod:",
            "rebuild:dev:",
            "rebuild:test:",
            "rebuild:prod:",
            "test:",
            "test:backend:",
            "test:frontend:",
            "seed:account:",
            "seed:data:",
            "destroy:all:",
        ]:
            assert task_name in taskfile

    def test_legacy_public_tasks_removed(self):
        """Removed legacy tasks no longer appear in Taskfile.yml."""
        taskfile = _read_text("Taskfile.yml")
        for removed in [
            "\n  up:\n",
            "up:prod:local:",
            "\n  down:\n",
            "down:proxy:",
            "\n  proxy:\n",
            "proxy:off:",
            "debug:",
            "env:reset:",
            "docker:clean:",
            "docker:volume-clean:",
            "docker:rebuild-clean:",
            "docker:pgadmin:",
            "test:integration:",
            "test:unit:",
            "test:coverage:",
        ]:
            assert removed not in taskfile


class TestEnvContract:
    """The repo now has one canonical env template and checked-in env policy."""

    def test_root_env_template_exists(self):
        """Root .env.template is the only checked-in env template."""
        assert (PROJECT_ROOT / ".env.template").exists()

    def test_old_profile_env_templates_removed(self):
        """Per-profile .env.*.template files have been deleted."""
        for relpath in [
            "env/.env.development.template",
            "env/.env.testing.template",
            "env/.env.production.template",
        ]:
            assert not (PROJECT_ROOT / relpath).exists()

    def test_env_policy_exists(self):
        """Checked-in env_policy.yml contains targets, profiles, and validation."""
        policy = _load_yaml("scripts/config/env_policy.yml")
        assert "targets" in policy
        assert "profiles" in policy
        assert "validation" in policy


class TestComposeLayout:
    """Compose has been split into proxy/dev/test/prod files."""

    def test_compose_files_exist(self):
        """Four separate compose files exist in docker/ directory."""
        for relpath in [
            "docker/compose.proxy.yml",
            "docker/compose.dev.yml",
            "docker/compose.test.yml",
            "docker/compose.prod.yml",
        ]:
            assert (PROJECT_ROOT / relpath).exists()

    def test_legacy_monolithic_compose_removed(self):
        """The old single docker-compose.yml has been deleted."""
        assert not (PROJECT_ROOT / "docker-compose.yml").exists()

    def test_proxy_compose_has_only_proxy_service(self):
        """Proxy compose file defines only the proxy service."""
        services = _services("docker/compose.proxy.yml")
        assert set(services) == {"proxy"}

    def test_app_compose_files_have_db_backend_frontend(self):
        """Each app compose file defines exactly db, backend, frontend."""
        expected = {"db", "backend", "frontend"}
        for relpath in [
            "docker/compose.dev.yml",
            "docker/compose.test.yml",
            "docker/compose.prod.yml",
        ]:
            assert set(_services(relpath)) == expected

    def test_no_service_uses_container_name(self):
        """No compose service uses manual container_name."""
        for relpath in [
            "docker/compose.proxy.yml",
            "docker/compose.dev.yml",
            "docker/compose.test.yml",
            "docker/compose.prod.yml",
        ]:
            for service in _services(relpath).values():
                assert "container_name" not in service


class TestComposeNamesAndVolumes:
    """Networks, aliases, and volumes must use explicit EElab naming."""

    def test_proxy_network_name(self):
        """Shared proxy network is named eelab-proxy."""
        config = _load_yaml("docker/compose.proxy.yml")
        assert config["networks"]["eelab-proxy"]["name"] == "eelab-proxy"

    def test_app_network_names(self):
        """Each app stack has a profile-scoped private network plus shared proxy."""
        expectations = {
            "docker/compose.dev.yml": "eelab-dev-app",
            "docker/compose.test.yml": "eelab-test-app",
            "docker/compose.prod.yml": "eelab-prod-app",
        }
        for relpath, expected_name in expectations.items():
            config = _load_yaml(relpath)
            assert config["networks"]["app"]["name"] == expected_name
            assert config["networks"]["eelab-proxy"]["external"] is True
            assert config["networks"]["eelab-proxy"]["name"] == "eelab-proxy"

    def test_service_aliases_are_explicit(self):
        """Backend and frontend expose stable proxy aliases per profile."""
        expectations = {
            "docker/compose.dev.yml": ("eelab-dev-backend", "eelab-dev-frontend"),
            "docker/compose.test.yml": ("eelab-test-backend", "eelab-test-frontend"),
            "docker/compose.prod.yml": ("eelab-prod-backend", "eelab-prod-frontend"),
        }
        for relpath, (backend_alias, frontend_alias) in expectations.items():
            services = _services(relpath)
            assert backend_alias in services["backend"]["networks"]["eelab-proxy"]["aliases"]
            assert frontend_alias in services["frontend"]["networks"]["eelab-proxy"]["aliases"]

    def test_named_volumes_are_profile_specific(self):
        """Named volumes use eelab-{profile}-{purpose} naming convention."""
        expectations = {
            "docker/compose.dev.yml": {
                "db-data": "eelab-dev-db-data",
                "media-data": "eelab-dev-media-data",
                "artifact-data": "eelab-dev-artifact-data",
            },
            "docker/compose.test.yml": {
                "db-data": "eelab-test-db-data",
                "media-data": "eelab-test-media-data",
                "artifact-data": "eelab-test-artifact-data",
            },
            "docker/compose.prod.yml": {
                "db-data": "eelab-prod-db-data",
                "media-data": "eelab-prod-media-data",
                "artifact-data": "eelab-prod-artifact-data",
            },
        }
        for relpath, volume_map in expectations.items():
            config = _load_yaml(relpath)
            for logical_name, actual_name in volume_map.items():
                assert config["volumes"][logical_name]["name"] == actual_name


class TestProxyRouting:
    """The shared proxy must own the public ports and route each profile explicitly."""

    def test_proxy_ports_cover_prod_dev_test(self):
        """Proxy exposes only shared public ports 80/443."""
        proxy = _services("docker/compose.proxy.yml")["proxy"]
        assert proxy["ports"] == [
            "80:80",
            "443:443",
        ]

    def test_proxy_templates_exist(self):
        """Nginx config and the unified multi-profile server-block template exist."""
        for relpath in [
            "proxy/nginx.conf",
            "proxy/templates/prod.conf.template",
        ]:
            assert (PROJECT_ROOT / relpath).exists()

    def test_dev_proxy_template_routes_expected_aliases(self):
        """Dev proxy routes to eelab-dev-backend/frontend under /_dev/."""
        text = _read_text("proxy/templates/prod.conf.template")
        assert "eelab-dev-backend:8000" in text
        assert "eelab-dev-frontend:3000" in text
        for path in ["/_dev/api/v1/", "/_dev/admin/", "/_dev/static/", "/_dev/"]:
            assert path in text

    def test_test_proxy_template_routes_expected_aliases(self):
        """Test proxy routes to eelab-test-backend/frontend under /_test/."""
        text = _read_text("proxy/templates/prod.conf.template")
        assert "eelab-test-backend:8000" in text
        assert "eelab-test-frontend:3000" in text
        for path in ["/_test/api/v1/", "/_test/admin/", "/_test/static/", "/_test/"]:
            assert path in text

    def test_prod_proxy_template_routes_expected_aliases(self):
        """Prod proxy routes to eelab-prod-backend/frontend at root on 80/443."""
        text = _read_text("proxy/templates/prod.conf.template")
        assert "eelab-prod-backend:8000" in text
        assert "eelab-prod-frontend:3000" in text
        # Both listeners must be marked default_server so the stock
        # default.conf shipped in the nginx:alpine image doesn't shadow us
        # for unmatched Host headers (internal docker-network traffic).
        assert "listen 80 default_server;" in text
        assert "listen 443 ssl default_server;" in text


class TestTaskScripts:
    """The new scripts/tasks entrypoints must exist."""

    def test_required_task_scripts_exist(self):
        """All 11 required task workflow scripts are present."""
        for relpath in [
            "scripts/tasks/prepare-env.sh",
            "scripts/tasks/check-env.sh",
            "scripts/tasks/set-env-target.sh",
            "scripts/tasks/up.sh",
            "scripts/tasks/down.sh",
            "scripts/tasks/status.sh",
            "scripts/tasks/logs.sh",
            "scripts/tasks/restart.sh",
            "scripts/tasks/rebuild.sh",
            "scripts/tasks/test.sh",
            "scripts/tasks/destroy-all.sh",
        ]:
            assert (PROJECT_ROOT / relpath).exists()

    def test_legacy_runtime_scripts_removed(self):
        """Old backend_start.sh and profile_guard.py are deleted."""
        for relpath in [
            "scripts/runtime/backend_start.sh",
            "scripts/runtime/profile_guard.py",
        ]:
            assert not (PROJECT_ROOT / relpath).exists()
