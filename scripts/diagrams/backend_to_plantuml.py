#!/usr/bin/env python3
"""Generate PlantUML class diagrams from backend Python modules."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Iterable


SKIP_FILES = {"__init__.py", "manage.py", "apps.py"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="backend/src")
    parser.add_argument("--out", required=True)
    parser.add_argument("--packages", default="")
    args = parser.parse_args()

    root = Path(args.root)
    package_filter = {name.strip() for name in args.packages.split(",") if name.strip()}
    modules = collect_modules(root, package_filter)

    packages: dict[str, list[list[str]]] = {}
    relations: list[str] = []

    for module in modules:
        if module.name == "models.py":
            continue
        rel_path = module.relative_to(root)
        package_name = rel_path.parts[0] if rel_path.parts else "root"
        items = parse_module(module, package_name)
        if not items:
            continue
        packages.setdefault(package_name, []).extend(items)

    lines: list[str] = ["@startuml", "hide circle", "skinparam classAttributeIconSize 0", ""]
    for package, items in sorted(packages.items()):
        lines.append(f'package "{package}" {{')
        for item in items:
            lines.extend(item)
        lines.append("}")
        lines.append("")

    lines.extend(relations)
    lines.append("@enduml")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


def collect_modules(root: Path, package_filter: set[str]) -> list[Path]:
    modules: list[Path] = []
    for path in root.rglob("*.py"):
        if "migrations" in path.parts:
            continue
        if path.name in SKIP_FILES:
            continue
        if package_filter:
            rel_path = path.relative_to(root)
            package_name = rel_path.parts[0] if rel_path.parts else "root"
            if package_name not in package_filter:
                continue
        modules.append(path)
    return modules


def parse_module(path: Path, package_name: str) -> list[list[str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    items: list[list[str]] = []
    if path.name.endswith("services.py"):
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        if functions:
            items.append(render_module_functions(functions, f"{package_name}Services", "Service"))
    if path.name.endswith("repositories.py"):
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        if functions:
            items.append(render_module_functions(functions, f"{package_name}Repository", "Repository"))

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            items.append(render_class(node))

    return items


def render_module_functions(nodes: Iterable[ast.FunctionDef], name: str, stereotype: str) -> list[str]:
    lines = [f'class {name} <<{stereotype}>> {{']
    for func in nodes:
        signature = format_signature(func, drop_first=False)
        lines.append(f"  +{signature}")
    lines.append("}")
    return lines


def render_class(node: ast.ClassDef) -> list[str]:
    lines = [f'class {node.name} {{']
    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            signature = format_signature(item)
            lines.append(f"  +{signature}")
    lines.append("}")
    return lines


def format_signature(func: ast.FunctionDef, drop_first: bool = True) -> str:
    params = []
    for idx, arg in enumerate(func.args.args):
        if drop_first and idx == 0 and arg.arg in {"self", "cls"}:
            continue
        annotation = format_annotation(arg.annotation)
        params.append(f"{arg.arg}: {annotation}")
    params_text = ", ".join(params)
    return_type = format_annotation(func.returns)
    return f"{func.name}({params_text}): {return_type}"


def format_annotation(node: ast.AST | None) -> str:
    if node is None:
        return "Any"
    try:
        return ast.unparse(node)
    except Exception:
        return "Any"


if __name__ == "__main__":
    raise SystemExit(main())
