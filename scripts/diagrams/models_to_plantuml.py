#!/usr/bin/env python3
"""Generate a PlantUML class diagram from Django models."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

import django
from django.apps import apps
from django.db import models


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--apps", default="")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    backend_src = repo_root / "backend" / "src"
    if not backend_src.exists():
        backend_src = repo_root / "src"
    sys.path.insert(0, str(backend_src))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    app_filter = {name.strip() for name in args.apps.split(",") if name.strip()}
    diagram = build_diagram(app_filter)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(diagram, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


def build_diagram(app_filter: set[str]) -> str:
    models_list = list(apps.get_models())
    if app_filter:
        models_list = [model for model in models_list if model._meta.app_label in app_filter]

    packages: dict[str, list[type[models.Model]]] = {}
    for model in models_list:
        packages.setdefault(model._meta.app_label, []).append(model)

    lines: list[str] = ["@startuml", "hide circle", "skinparam classAttributeIconSize 0", ""]

    for app_label, model_group in sorted(packages.items()):
        lines.append(f'package "{app_label}" {{')
        for model in sorted(model_group, key=lambda m: m.__name__):
            lines.extend(render_model(model))
        lines.append("}")
        lines.append("")

    relations = collect_relations(models_list)
    lines.extend(relations)
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def render_model(model: type[models.Model]) -> Iterable[str]:
    lines: list[str] = [f'class {model.__name__} <<Model>> {{']
    for field in model._meta.fields:
        if field.auto_created and not field.concrete:
            continue
        lines.append(f"  +{field.name}: {field_type(field)}")
    for field in model._meta.many_to_many:
        if field.auto_created:
            continue
        lines.append(f"  +{field.name}: {field_type(field)}")
    lines.append("}")
    return lines


def field_type(field: models.Field) -> str:
    if isinstance(field, models.ForeignKey):
        return field.related_model.__name__
    if isinstance(field, models.OneToOneField):
        return field.related_model.__name__
    if isinstance(field, models.ManyToManyField):
        return f"List[{field.related_model.__name__}]"
    return field.get_internal_type()


def collect_relations(models_list: list[type[models.Model]]) -> list[str]:
    relations: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for model in models_list:
        for field in model._meta.fields:
            if isinstance(field, models.ForeignKey):
                relations.extend(
                    relation_line(
                        model.__name__,
                        field.related_model.__name__,
                        "0..*",
                        "1",
                        field.name,
                        seen,
                    )
                )
            elif isinstance(field, models.OneToOneField):
                relations.extend(
                    relation_line(
                        model.__name__,
                        field.related_model.__name__,
                        "1",
                        "1",
                        field.name,
                        seen,
                    )
                )
        for field in model._meta.many_to_many:
            if field.auto_created:
                continue
            relations.extend(
                relation_line(
                    model.__name__,
                    field.related_model.__name__,
                    "*",
                    "*",
                    field.name,
                    seen,
                )
            )
    return relations


def relation_line(
    left: str,
    right: str,
    left_card: str,
    right_card: str,
    label: str,
    seen: set[tuple[str, str, str]],
) -> list[str]:
    key = tuple(sorted((left, right)) + [label])
    if key in seen:
        return []
    seen.add(key)
    return [f'{left} "{left_card}" -- "{right_card}" {right} : {label}']


if __name__ == "__main__":
    raise SystemExit(main())
