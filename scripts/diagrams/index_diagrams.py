#!/usr/bin/env python3
"""Generate a PlantUML diagrams index for Docs/diagrams/plantuml."""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path("Docs/diagrams/plantuml")
    index_path = root / "Diagrams-Index.md"
    if not root.exists():
        raise SystemExit("Docs/diagrams/plantuml not found. Run from repo root.")

    lines = [
        "# Diagrams Index",
        "",
        "All paths are relative to `Docs/diagrams/plantuml/`.",
        "",
    ]

    def add_section(title: str) -> None:
        lines.append(f"## {title}")
        lines.append("")

    def add_list(paths: list[Path]) -> None:
        if not paths:
            lines.append("- (none)")
            lines.append("")
            return
        for path in paths:
            lines.append(f"- `{path.as_posix()}`")
        lines.append("")

    backend_class_dir = root / "uml" / "class" / "backend"
    frontend_class_dir = root / "uml" / "class" / "frontend"
    entity_dir = root / "uml" / "entity" / "postgres"
    sequence_dir = root / "sequence" / "api"

    add_section("UML Class Diagrams (Backend)")
    add_list(sorted(backend_class_dir.glob("*.wsd")))

    add_section("UML Class Diagrams (Frontend)")
    add_list(sorted(frontend_class_dir.glob("*.wsd")))

    add_section("UML Entity Diagrams (Postgres)")
    add_list(sorted(entity_dir.glob("*.wsd")))

    add_section("Sequence Diagrams (API, from OTEL traces)")
    if sequence_dir.exists():
        modules = sorted([p for p in sequence_dir.iterdir() if p.is_dir()])
        if not modules:
            lines.append("- (none)")
            lines.append("")
        else:
            for module in modules:
                lines.append(f"### {module.name}")
                lines.append("")
                success = sorted(
                    (module / "success").glob("*.wsd")
                ) if (module / "success").exists() else []
                error = sorted(
                    (module / "error").glob("*.wsd")
                ) if (module / "error").exists() else []
                if success:
                    lines.append("#### success")
                    lines.append("")
                    for path in success:
                        rel = path.relative_to(root).as_posix()
                        lines.append(f"- `{rel}`")
                    lines.append("")
                if error:
                    lines.append("#### error")
                    lines.append("")
                    for path in error:
                        rel = path.relative_to(root).as_posix()
                        lines.append(f"- `{rel}`")
                    lines.append("")
                if not success and not error:
                    lines.append("- (none)")
                    lines.append("")

    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
