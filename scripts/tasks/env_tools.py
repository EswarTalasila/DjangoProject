#!/usr/bin/env python3
"""Shared env preparation and validation helpers for task scripts."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / ".env.template"
ROOT_ENV_PATH = ROOT / ".env"
BACKUP_ENV_PATH = ROOT / ".env.bak"
POLICY_PATH = ROOT / "scripts" / "config" / "env_policy.yml"
ENV_DIR = ROOT / "env"

PROFILE_FILE_MAP = {
    "dev": ENV_DIR / ".env.development",
    "test": ENV_DIR / ".env.testing",
    "prod": ENV_DIR / ".env.production",
}

RUNTIME_KEY_ORDER = [
    "ENVIRONMENT",
    "ENV_TARGET",
    "PUBLIC_HOST",
    "PUBLIC_SCHEME",
    "FORCE_SCRIPT_NAME",
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_CORS_ALLOWED_ORIGINS",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "DJANGO_SECURE_SSL_REDIRECT",
    "DJANGO_SESSION_COOKIE_SECURE",
    "DJANGO_CSRF_COOKIE_SECURE",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "NEXT_PUBLIC_GOOGLE_CLIENT_ID",
    "NEXT_PUBLIC_API_URL",
    "NEXT_BASE_PATH",
    "SERVER_PROXY_ORIGIN",
    "ADMIN_USERNAME",
    "ADMIN_EMAIL",
    "ADMIN_PASSWORD",
    "MEDIA_ROOT",
]

ENV_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def load_policy() -> dict:
    # env_policy.yml uses JSON serialization (valid YAML subset) so we can
    # parse with the stdlib json module without requiring PyYAML on the host.
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = ENV_LINE_RE.match(raw.strip())
        if match:
            values[match.group(1)] = match.group(2)
    return values


def template_keys(template_lines: list[str]) -> list[str]:
    keys: list[str] = []
    for raw in template_lines:
        match = ENV_LINE_RE.match(raw.strip())
        if match:
            keys.append(match.group(1))
    return keys


def render_template(template_lines: list[str], values: dict[str, str], extras: dict[str, str] | None = None) -> str:
    rendered: list[str] = []
    seen: set[str] = set()
    for raw in template_lines:
        match = ENV_LINE_RE.match(raw.strip())
        if not match:
            rendered.append(raw)
            continue
        key = match.group(1)
        seen.add(key)
        rendered.append(f"{key}={values.get(key, match.group(2))}\n")

    if extras:
        remaining = {k: v for k, v in extras.items() if k not in seen}
        if remaining:
            rendered.append("\n# Preserved custom values\n")
            for key in sorted(remaining):
                rendered.append(f"{key}={remaining[key]}\n")
    return "".join(rendered)


def sync_root_env() -> tuple[str, dict[str, str]]:
    template_lines = read_lines(TEMPLATE_PATH)
    template_defaults = {key: "" for key in template_keys(template_lines)}

    if not ROOT_ENV_PATH.exists():
        shutil.copy2(TEMPLATE_PATH, ROOT_ENV_PATH)
        return "created", parse_env(ROOT_ENV_PATH)

    current_values = parse_env(ROOT_ENV_PATH)
    missing = [key for key in template_defaults if key not in current_values]
    if missing:
        if BACKUP_ENV_PATH.exists():
            BACKUP_ENV_PATH.unlink()
        shutil.copy2(ROOT_ENV_PATH, BACKUP_ENV_PATH)
        merged_values = {**current_values}
        rewritten = render_template(template_lines, merged_values, extras=current_values)
        ROOT_ENV_PATH.write_text(rewritten, encoding="utf-8")
        return "merged", parse_env(ROOT_ENV_PATH)

    return "ok", current_values


def root_values_for_target(target: str) -> dict[str, str]:
    policy = load_policy()
    status, current = sync_root_env()
    target_defaults = policy["targets"][target]
    current["ENV_TARGET"] = target
    current["PUBLIC_HOST"] = target_defaults["public_host"]
    current["PUBLIC_SCHEME"] = target_defaults["public_scheme"]
    ROOT_ENV_PATH.write_text(
        render_template(read_lines(TEMPLATE_PATH), current, extras=current),
        encoding="utf-8",
    )
    if status == "created":
        print(f"[env-target] created {ROOT_ENV_PATH}. review serious values before env:init")
    print(
        f"[env-target] target={target} host={current['PUBLIC_HOST']} scheme={current['PUBLIC_SCHEME']}"
    )
    return current


def build_runtime(profile: str, root_values: dict[str, str], policy: dict) -> dict[str, str]:
    profile_cfg = policy["profiles"][profile]
    target_cfg = policy["targets"].get(root_values.get("ENV_TARGET", "local"), policy["targets"]["local"])
    public_host = root_values.get("PUBLIC_HOST", target_cfg["public_host"])
    public_scheme = root_values.get("PUBLIC_SCHEME", target_cfg["public_scheme"])

    is_local_host = public_host == "localhost"

    # URL path prefix for multi-profile routing behind a single proxy.
    # Prod serves at root; dev/test are namespaced so all three can share
    # the public :443 listener. Same mapping for local and server so URLs
    # are consistent across environments.
    base_path = {"prod": "", "dev": "/_dev", "test": "/_test"}[profile]

    # Same-origin under path routing — every profile shares the public host.
    primary_origin = f"{public_scheme}://{public_host}"
    origins: list[str] = [primary_origin]
    if is_local_host and public_scheme == "https":
        origins.append(f"http://{public_host}")

    runtime = {
        "ENVIRONMENT": profile_cfg["environment"],
        "ENV_TARGET": root_values.get("ENV_TARGET", "local"),
        "PUBLIC_HOST": public_host,
        "PUBLIC_SCHEME": public_scheme,
        "NEXT_PUBLIC_API_URL": f"{base_path}/api/v1",
        "NEXT_BASE_PATH": base_path,
        "FORCE_SCRIPT_NAME": base_path,
        # SSR fetches go through the proxy. For local dev (PUBLIC_HOST=localhost)
        # the public host is unreachable from inside the frontend container — it
        # resolves to the container itself, not the host. Use the proxy's docker
        # network alias instead. The self-signed cert lists "proxy" as a SAN so
        # TLS verification succeeds. For server deployments, the public host
        # resolves correctly via real DNS, so we use it directly.
        "SERVER_PROXY_ORIGIN": (
            "https://proxy"
            if root_values.get("ENV_TARGET", "local") == "local"
            else f"{public_scheme}://{public_host}"
        ),
        "MEDIA_ROOT": profile_cfg["media_root"],
    }

    if profile == "prod":
        runtime.update(
            {
                "DJANGO_SECRET_KEY": root_values.get("DJANGO_SECRET_KEY", ""),
                "POSTGRES_DB": root_values.get("POSTGRES_DB", "lattice_prod"),
                "POSTGRES_USER": root_values.get("POSTGRES_USER", "lattice_prod"),
                "POSTGRES_PASSWORD": root_values.get("POSTGRES_PASSWORD", ""),
                "GOOGLE_CLIENT_ID": root_values.get("GOOGLE_CLIENT_ID", ""),
                "GOOGLE_CLIENT_SECRET": root_values.get("GOOGLE_CLIENT_SECRET", ""),
                "NEXT_PUBLIC_GOOGLE_CLIENT_ID": root_values.get(
                    "NEXT_PUBLIC_GOOGLE_CLIENT_ID",
                    root_values.get("GOOGLE_CLIENT_ID", ""),
                ),
                "ADMIN_USERNAME": root_values.get("ADMIN_USERNAME", "Admin"),
                "ADMIN_EMAIL": root_values.get("ADMIN_EMAIL", ""),
                "ADMIN_PASSWORD": root_values.get("ADMIN_PASSWORD", ""),
                "DJANGO_ALLOWED_HOSTS": public_host,
                "DJANGO_CORS_ALLOWED_ORIGINS": ",".join(origins),
                "DJANGO_CSRF_TRUSTED_ORIGINS": ",".join(origins),
                "DJANGO_SECURE_SSL_REDIRECT": "true" if public_scheme == "https" else "false",
                "DJANGO_SESSION_COOKIE_SECURE": "true" if public_scheme == "https" else "false",
                "DJANGO_CSRF_COOKIE_SECURE": "true" if public_scheme == "https" else "false",
            }
        )
    else:
        secure_cookies = "true" if public_scheme == "https" else "false"
        runtime.update(profile_cfg["db_defaults"])
        runtime.update(profile_cfg["app_defaults"])
        runtime.update(
            {
                "GOOGLE_CLIENT_ID": root_values.get("GOOGLE_CLIENT_ID", ""),
                "GOOGLE_CLIENT_SECRET": root_values.get("GOOGLE_CLIENT_SECRET", ""),
                "NEXT_PUBLIC_GOOGLE_CLIENT_ID": root_values.get(
                    "NEXT_PUBLIC_GOOGLE_CLIENT_ID",
                    root_values.get("GOOGLE_CLIENT_ID", ""),
                ),
                "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1"
                if is_local_host
                else public_host,
                "DJANGO_CORS_ALLOWED_ORIGINS": ",".join(origins),
                "DJANGO_CSRF_TRUSTED_ORIGINS": ",".join(origins),
                "DJANGO_SECURE_SSL_REDIRECT": "false",
                "DJANGO_SESSION_COOKIE_SECURE": secure_cookies,
                "DJANGO_CSRF_COOKIE_SECURE": secure_cookies,
            }
        )

    runtime["DATABASE_URL"] = (
        f"postgres://{runtime['POSTGRES_USER']}:{runtime['POSTGRES_PASSWORD']}"
        f"@db:5432/{runtime['POSTGRES_DB']}"
    )
    return runtime


def write_runtime_env(profile: str, values: dict[str, str]) -> None:
    ENV_DIR.mkdir(parents=True, exist_ok=True)
    path = PROFILE_FILE_MAP[profile]
    label = {"dev": "development", "test": "testing", "prod": "production"}[profile]
    lines = [
        f"# Generated by task env:init for {label}\n",
        "# Edit root .env only, then rerun task env:init\n\n",
    ]
    seen: set[str] = set()
    for key in RUNTIME_KEY_ORDER:
        if key in values:
            lines.append(f"{key}={values[key]}\n")
            seen.add(key)
    for key in sorted(values):
        if key not in seen:
            lines.append(f"{key}={values[key]}\n")
    path.write_text("".join(lines), encoding="utf-8")
    print(f"[env-init] wrote {path.relative_to(ROOT)}")


def cmd_prepare(target: str) -> int:
    policy = load_policy()
    status, root_values = sync_root_env()
    if status == "created":
        print(f"[env-init] created {ROOT_ENV_PATH}. fill it out, then rerun task env:init")
        return 2
    if status == "merged":
        print(f"[env-init] updated {ROOT_ENV_PATH} from template and saved {BACKUP_ENV_PATH.name}")

    profiles = ["dev", "test", "prod"] if target == "all" else [target]
    for profile in profiles:
        write_runtime_env(profile, build_runtime(profile, root_values, policy))
    return 0


def validate_profile(profile: str) -> int:
    policy = load_policy()
    env_path = PROFILE_FILE_MAP[profile]
    if not env_path.exists():
        print(f"[env-check] profile={profile} status=error")
        print(f"ERROR ENV-F001: missing generated env file {env_path.relative_to(ROOT)}")
        print("  hint: run task env:init")
        return 1

    status, root_values = sync_root_env()
    if status == "created":
        print(f"[env-check] profile={profile} status=error")
        print("ERROR ENV-F002: root .env was missing and has just been created.")
        print("  hint: fill out .env, rerun task env:init, then retry startup.")
        return 1

    expected = build_runtime(profile, root_values, policy)
    actual = parse_env(env_path)
    validation_keys = policy["validation"]["keys"]
    internal_hosts = set(policy["validation"]["internal_hosts"])

    warnings: list[tuple[str, str, str]] = []
    errors: list[tuple[str, str, str]] = []

    def add(level: str, code: str, message: str, hint: str) -> None:
        bucket = errors if level == "ERROR" else warnings
        bucket.append((code, message, hint))

    for key in [
        "ENVIRONMENT",
        "PUBLIC_HOST",
        "PUBLIC_SCHEME",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "DATABASE_URL",
        "SERVER_PROXY_ORIGIN",
        "MEDIA_ROOT",
    ]:
        if actual.get(key) != expected.get(key):
            level = "ERROR" if profile == "prod" else "WARN"
            add(
                level,
                "ENV-DERIVE",
                f"{key} does not match the derived value for profile {profile}.",
                "rerun task env:init to rewrite generated env files.",
            )

    if profile in {"dev", "test"}:
        defaults = policy["profiles"][profile]["app_defaults"] | policy["profiles"][profile]["db_defaults"]
        for key, default_value in defaults.items():
            if actual.get(key) == default_value:
                add(
                    "WARN",
                    "ENV-DEFAULT",
                    f"{key} is using the {profile} default value.",
                    "replace it in root .env only if you need a stronger local/testing override.",
                )
    else:
        for key, rules in validation_keys.items():
            actual_value = actual.get(key, "")
            placeholder = rules.get("placeholder", "")
            if not actual_value or actual_value == placeholder:
                add(
                    "ERROR",
                    "ENV-PLACEHOLDER",
                    f"{key} is still using its production placeholder.",
                    "set a real value in root .env and rerun task env:init.",
                )
                continue
            min_length = rules.get("min_length")
            if min_length and len(actual_value) < min_length:
                add(
                    "ERROR",
                    "ENV-WEAK",
                    f"{key} does not meet the minimum length requirement.",
                    f"set a value with at least {min_length} characters in root .env.",
                )
            if rules.get("validator") == "email" and "@" not in actual_value:
                add(
                    "ERROR",
                    "ENV-EMAIL",
                    f"{key} is not a valid email address.",
                    "set a valid production email in root .env.",
                )

        allowed_hosts = [part.strip() for part in actual.get("DJANGO_ALLOWED_HOSTS", "").split(",") if part.strip()]
        if not allowed_hosts:
            add("ERROR", "ENV-HOSTS", "DJANGO_ALLOWED_HOSTS is empty.", "set PUBLIC_HOST and rerun task env:init.")
        if any(part in {"localhost", "127.0.0.1"} or part in internal_hosts for part in allowed_hosts):
            add(
                "ERROR",
                "ENV-HOSTS",
                "DJANGO_ALLOWED_HOSTS includes localhost or internal service names.",
                "production hosts must resolve only to the public hostname.",
            )

        for key in ["DJANGO_CORS_ALLOWED_ORIGINS", "DJANGO_CSRF_TRUSTED_ORIGINS"]:
            actual_values = [part.strip() for part in actual.get(key, "").split(",") if part.strip()]
            if not actual_values:
                add("ERROR", "ENV-ORIGINS", f"{key} is empty.", "rerun task env:init after setting PUBLIC_HOST.")
                continue
            if any("localhost" in value or "127.0.0.1" in value or "*" in value for value in actual_values):
                add(
                    "ERROR",
                    "ENV-ORIGINS",
                    f"{key} includes localhost or wildcard entries.",
                    "production trusted origins must only use the public host.",
                )

    status_label = "error" if errors else "warn" if warnings else "ok"
    print(f"[env-check] profile={profile} status={status_label}")
    for code, message, hint in warnings:
        print(f"WARN {code}: {message}")
        print(f"  hint: {hint}")
    for code, message, hint in errors:
        print(f"ERROR {code}: {message}")
        print(f"  hint: {hint}")
    return 1 if errors else 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: env_tools.py <set-target|prepare|check> ...", file=sys.stderr)
        return 1

    command = argv[1]
    if command == "set-target":
        if len(argv) != 3 or argv[2] not in {"local", "server"}:
            print("usage: env_tools.py set-target <local|server>", file=sys.stderr)
            return 1
        root_values_for_target(argv[2])
        return 0

    if command == "prepare":
        if len(argv) != 3 or argv[2] not in {"all", "dev", "test", "prod"}:
            print("usage: env_tools.py prepare <all|dev|test|prod>", file=sys.stderr)
            return 1
        return cmd_prepare(argv[2])

    if command == "check":
        if len(argv) != 3 or argv[2] not in {"dev", "test", "prod"}:
            print("usage: env_tools.py check <dev|test|prod>", file=sys.stderr)
            return 1
        return validate_profile(argv[2])

    print(f"unknown command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
