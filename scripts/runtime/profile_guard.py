#!/usr/bin/env python3
"""Profile-aware startup diagnostics runner for Task commands."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time


def run(cmd: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=capture,
        check=False,
    )


def backend_status(compose_bin: str, service: str) -> tuple[bool, bool]:
    """Return (running, restarting) state for backend service."""
    container_id = run(f"{compose_bin} ps -q {service}", capture=True).stdout.strip()
    if not container_id:
        return False, False

    state = run(
        f"docker inspect -f '{{{{.State.Running}}}} {{{{.State.Restarting}}}}' {container_id}",
        capture=True,
    ).stdout.strip()
    if not state:
        return False, False

    parts = state.split()
    if len(parts) != 2:
        return False, False
    return parts[0].lower() == "true", parts[1].lower() == "true"


def parse_reason(logs: str) -> str:
    match = re.search(r"ERROR (ENV-[A-Z0-9]+): ([^\n]+)", logs)
    if match:
        return f"{match.group(1)} {match.group(2)}"

    match = re.search(r"Invalid production[^[]+", logs)
    if match:
        return match.group(0).strip()

    match = re.search(r"CommandError:\s*(.+)", logs)
    if match:
        return match.group(1).strip()

    return ""


def hint_for_reason(reason: str, profile: str) -> str:
    if "ADMIN_EMAIL" in reason:
        return "Set ADMIN_EMAIL to a non-default address in .env."
    if "ADMIN_PASSWORD" in reason:
        return "Set ADMIN_PASSWORD to a strong non-default value (>=12 chars)."
    if "DJANGO_SECRET_KEY" in reason:
        return "Set DJANGO_SECRET_KEY to a unique random secret."
    if "DJANGO_DEBUG" in reason:
        return "Remove DJANGO_DEBUG=true for production profile."
    if "DJANGO_ALLOWED_HOSTS" in reason:
        return "Set DJANGO_ALLOWED_HOSTS to real hostnames only (no localhost)."
    if "DJANGO_CORS_ALLOWED_ORIGINS" in reason:
        return "Set explicit trusted CORS origins (no wildcard/localhost)."
    if "DATABASE_URL" in reason:
        return "Set DATABASE_URL with non-default credentials and non-local host."
    if "OAuth" in reason:
        return "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
    if "OTEL" in reason:
        return "For production OTEL, set OTLP endpoint and clear OTEL_TRACE_FILE."
    return f"Review .env values for {profile} profile."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run concise profile startup diagnostics."
    )
    parser.add_argument(
        "--profile",
        required=True,
        choices=["development", "testing", "production"],
        help="Profile to validate diagnostics for.",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=10,
        help="Max seconds to wait for backend container to enter running state.",
    )
    parser.add_argument(
        "--service",
        default="backend",
        help="Compose service name to validate (default: backend).",
    )
    args = parser.parse_args()

    # Auto-detect whether sudo is needed for docker
    check = subprocess.run("docker info", shell=True, capture_output=True, check=False)
    compose_bin = "docker compose" if check.returncode == 0 else "sudo docker compose"
    deadline = time.time() + args.wait
    while time.time() < deadline:
        running, restarting = backend_status(compose_bin, args.service)
        if running and not restarting:
            break
        time.sleep(1)

    running, restarting = backend_status(compose_bin, args.service)
    if not running or restarting:
        logs = run(f"{compose_bin} logs --tail=200 {args.service}", capture=True).stdout
        reason = parse_reason(logs)

        print(f"[env-check] profile={args.profile} status=error")
        print("ERROR ENV-P001: backend failed startup validation.")
        if reason:
            print(f"  reason: {reason}")
            print(f"  hint: {hint_for_reason(reason, args.profile)}")
        else:
            print(f"  hint: run 'docker compose logs --tail=120 {args.service}' for details.")
        return 1

    strict_flag = "--strict" if args.profile == "production" else ""
    result = run(
        f"{compose_bin} exec -T {args.service} python src/manage.py env_report --profile {args.profile} {strict_flag}".strip(),
        capture=True,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode == 0:
        return 0

    logs = run(f"{compose_bin} logs --tail=200 {args.service}", capture=True).stdout
    reason = parse_reason(f"{result.stdout}\n{result.stderr}\n{logs}")
    print(f"[env-check] profile={args.profile} status=error")
    if args.profile == "production":
        print("ERROR ENV-P001: backend failed startup validation.")
    else:
        print("ERROR ENV-P002: environment diagnostics could not execute cleanly.")
    if reason:
        print(f"  reason: {reason}")
        print(f"  hint: {hint_for_reason(reason, args.profile)}")
    else:
        print(f"  hint: run 'docker compose logs --tail=120 {args.service}' for details.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
