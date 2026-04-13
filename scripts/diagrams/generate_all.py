#!/usr/bin/env python3
"""Generate PlantUML diagrams for the rewrite."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
import shutil
import sys


DEFAULT_APPS = "accounts,courses,assessments,assignments,submissions,visualizations,exports"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apps", default=DEFAULT_APPS)
    parser.add_argument("--out-dir", default="Docs/diagrams/plantuml")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    uml_dir = out_dir / "uml"
    class_dir = uml_dir / "class"
    backend_class_dir = class_dir / "backend"
    frontend_class_dir = class_dir / "frontend"
    entity_dir = uml_dir / "entity" / "postgres"
    backend_class_dir.mkdir(parents=True, exist_ok=True)
    frontend_class_dir.mkdir(parents=True, exist_ok=True)
    entity_dir.mkdir(parents=True, exist_ok=True)

    apps = [name.strip() for name in args.apps.split(",") if name.strip()]
    python_cmd = sys.executable or "python3"

    run(
        [
            python_cmd,
            "scripts/diagrams/models_to_plantuml.py",
            "--out",
            str(entity_dir / "postgres-all.wsd"),
            "--apps",
            ",".join(apps),
        ]
    )
    for app in apps:
        run(
            [
                python_cmd,
                "scripts/diagrams/models_to_plantuml.py",
                "--out",
                str(entity_dir / f"postgres-{app}.wsd"),
                "--apps",
                app,
            ]
        )
    backend_root = Path("backend/src")
    if not backend_root.exists():
        backend_root = Path("src")

    run(
        [
            python_cmd,
            "scripts/diagrams/backend_to_plantuml.py",
            "--root",
            str(backend_root),
            "--out",
            str(backend_class_dir / "backend-services.wsd"),
            "--packages",
            ",".join(apps),
        ]
    )
    for app in apps:
        run(
            [
                python_cmd,
                "scripts/diagrams/backend_to_plantuml.py",
                "--root",
                str(backend_root),
                "--out",
                str(backend_class_dir / f"backend-{app}.wsd"),
                "--packages",
                app,
            ]
        )

    if _can_render_frontend(repo_root=Path.cwd()):
        run(
            [
                "node",
                "scripts/diagrams/frontend_to_plantuml.mjs",
                "--out",
                str(frontend_class_dir / "frontend-classes.wsd"),
            ]
        )
    else:
        print("Skipping frontend diagrams (node or typescript not available).")

    return 0


def run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def _can_render_frontend(repo_root: Path) -> bool:
    if not shutil.which("node"):
        return False
    return (repo_root / "frontend" / "node_modules" / "typescript").exists()


if __name__ == "__main__":
    raise SystemExit(main())
