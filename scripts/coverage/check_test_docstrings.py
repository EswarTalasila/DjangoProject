#!/usr/bin/env python3
"""Check that all backend test methods have docstrings.

Scans all test_*.py files under backend/tests/ and reports any test
method (def test_*) that is missing a docstring. These docstrings
populate the description column in the pretty test output table.

Exit codes:
  0 — all test methods have docstrings
  1 — one or more test methods are missing docstrings
"""

from __future__ import annotations

import ast
from pathlib import Path


def _find_test_files(root: Path) -> list[Path]:
    return sorted(root.rglob("test_*.py"))


def _check_file(path: Path) -> list[str]:
    """Return list of 'file:line funcname' strings for tests missing docstrings."""
    missing: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return missing

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("test_"):
                continue
            docstring = ast.get_docstring(node)
            if not docstring:
                missing.append(f"{path}:{node.lineno} {node.name}")
    return missing


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    test_root = root / "backend" / "tests"

    if not test_root.exists():
        # Running inside Docker where backend/tests is at /app/tests
        test_root = Path("/app/tests")

    if not test_root.exists():
        print("[docstring-check] test directory not found, skipping")
        return 0

    all_missing: list[str] = []
    for test_file in _find_test_files(test_root):
        all_missing.extend(_check_file(test_file))

    if not all_missing:
        print(f"\n\033[32m[docstring-check]\033[0m all test methods have docstrings")
        return 0

    print(f"\n\033[33m[docstring-check]\033[0m {len(all_missing)} test method(s) missing docstrings:")
    for entry in all_missing:
        print(f"  \033[33m⚠\033[0m {entry}")
    print()
    print("  Docstrings populate the description column in the test output table.")
    print("  Add a one-line docstring to each flagged method.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
