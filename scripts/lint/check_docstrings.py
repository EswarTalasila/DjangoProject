"""Docstring coverage check for backend source files."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import sys


def _iter_python_files(root: Path, exclude: list[str]) -> list[Path]:
    paths = []
    for path in root.rglob("*.py"):
        if any(path.match(pattern) for pattern in exclude):
            continue
        paths.append(path)
    return paths


def _find_missing_docstrings(path: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - treat parse errors as failures
        raise SyntaxError(f"{path}: {exc}") from exc

    missing: list[tuple[int, str]] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            if ast.get_docstring(node) is None:
                kind = "inner class" if self.stack else "class"
                missing.append((node.lineno, f"{kind} {node.name}"))
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if ast.get_docstring(node) is None:
                kind = "method" if self.stack else "function"
                missing.append((node.lineno, f"{kind} {node.name}"))
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if ast.get_docstring(node) is None:
                kind = "method" if self.stack else "function"
                missing.append((node.lineno, f"{kind} {node.name}"))
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

    Visitor().visit(tree)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for missing docstrings.")
    parser.add_argument(
        "--root",
        default="backend/src",
        help="Root directory to scan (default: backend/src).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob patterns to exclude (repeatable).",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"Root path does not exist: {root}")
        return 2

    missing_total = 0
    for path in _iter_python_files(root, args.exclude):
        missing = _find_missing_docstrings(path)
        if missing:
            missing_total += len(missing)
            for line, label in missing:
                print(f"{path}:{line} missing docstring: {label}")

    if missing_total:
        print(f"Docstring coverage failed: {missing_total} missing docstrings.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
