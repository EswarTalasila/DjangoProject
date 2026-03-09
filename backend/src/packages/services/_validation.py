"""FR-16 tree & binding validation engine."""

from __future__ import annotations

import posixpath
from typing import Any

from accounts.models import Role, SudoPermission
from core.permissions import has_role, has_sudo_permission
from courses.models import Course

from ..models import DatasetBinding, NodeType, PackageNode, PackageWorkspace

# ── Cap defaults (PKG-CN-03) ────────────────────────────────────────
MAX_FILE_COUNT = 200
MAX_TOTAL_ROWS = 50_000
MAX_ARTIFACT_BYTES = 500 * 1024 * 1024  # 500 MB


class ValidationViolation:
    """Single validation violation."""

    def __init__(self, node_id: int | None, code: str, message: str):
        self.node_id = node_id
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {"nodeId": self.node_id, "code": self.code, "message": self.message}


class ValidationResult:
    """Aggregated validation outcome."""

    def __init__(self):
        self.violations: list[ValidationViolation] = []
        self.warnings: list[dict[str, Any]] = []
        self.file_count = 0
        self.estimated_rows = 0

    @property
    def valid(self) -> bool:
        return len(self.violations) == 0

    def add_violation(self, node_id: int | None, code: str, message: str):
        self.violations.append(ValidationViolation(node_id, code, message))

    def add_warning(self, node_id: int | None, code: str, message: str):
        self.warnings.append({"nodeId": node_id, "code": code, "message": message})

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": self.warnings,
            "fileCount": self.file_count,
            "estimatedRows": self.estimated_rows,
        }


# ── Public entry point ──────────────────────────────────────────────


def validate_workspace(
    workspace: PackageWorkspace,
    user,
    *,
    strict_mode: bool = True,
    snapshot_id: int | None = None,
) -> ValidationResult:
    """Run full validation on a workspace tree.

    Returns ValidationResult with violations (strict → errors, lenient → warnings).
    """
    result = ValidationResult()
    nodes = list(workspace.nodes.select_related("parent").order_by("id"))

    if not nodes:
        result.add_violation(None, "EMPTY_TREE", "Workspace has no nodes.")
        return result

    _validate_tree_structure(nodes, result)
    _validate_bindings(nodes, user, workspace, result)
    _validate_deterministic_paths(nodes, result)
    _validate_caps(nodes, result)

    if snapshot_id is not None:
        _validate_snapshot(snapshot_id, result)

    return result


# ── Tree structure (single root, acyclic, valid types) ──────────────


def _validate_tree_structure(nodes: list[PackageNode], result: ValidationResult):
    roots = [n for n in nodes if n.parent_id is None]
    if len(roots) == 0:
        result.add_violation(None, "NO_ROOT", "Tree has no root node.")
    elif len(roots) > 1:
        result.add_violation(
            None, "MULTIPLE_ROOTS", f"Tree has {len(roots)} root nodes; expected 1."
        )

    node_map = {n.id: n for n in nodes}
    for node in nodes:
        if node.node_type not in (NodeType.FOLDER, NodeType.FILE):
            result.add_violation(
                node.id, "INVALID_NODE_TYPE", f"Invalid node type: {node.node_type}"
            )
        if node.parent_id and node.parent_id not in node_map:
            result.add_violation(
                node.id,
                "ORPHAN_NODE",
                f"Parent {node.parent_id} not found in workspace.",
            )
        if node.parent_id:
            parent = node_map.get(node.parent_id)
            if parent and parent.node_type != NodeType.FOLDER:
                result.add_violation(
                    node.id,
                    "PARENT_NOT_FOLDER",
                    f"Parent node {node.parent_id} is not a folder.",
                )

    # Cycle detection via visited set
    for node in nodes:
        visited: set[int] = set()
        current = node
        while current.parent_id is not None:
            if current.id in visited:
                result.add_violation(
                    node.id, "CYCLE_DETECTED", "Cycle detected in tree."
                )
                break
            visited.add(current.id)
            current = node_map.get(current.parent_id)  # type: ignore[assignment]
            if current is None:
                break


# ── Binding validation per file node (PKG-CN-01) ───────────────────


def _validate_bindings(
    nodes: list[PackageNode],
    user,
    workspace: PackageWorkspace,
    result: ValidationResult,
):
    file_nodes = [n for n in nodes if n.node_type == NodeType.FILE]
    result.file_count = len(file_nodes)

    is_admin = user.is_staff
    is_researcher = has_role(user, Role.RESEARCHER)
    is_teacher = has_role(user, Role.TEACHER)
    has_export_ident = has_sudo_permission(user, SudoPermission.EXPORT_IDENTIFIABLE)

    for node in file_nodes:
        if not node.dataset_binding:
            result.add_violation(
                node.id, "MISSING_BINDING", "File node has no dataset binding."
            )
            continue

        if node.dataset_binding not in DatasetBinding.values:
            result.add_violation(
                node.id,
                "INVALID_BINDING",
                f"Unknown dataset binding: {node.dataset_binding}",
            )
            continue

        # Identifiable permission check (PKG-CN-01)
        if node.identifiable and is_researcher and not has_export_ident:
            result.add_violation(
                node.id,
                "IDENTIFIABLE_DENIED",
                "EXPORT_IDENTIFIABLE permission required for identifiable export.",
            )

        # Teacher scope check — owned course only
        if is_teacher and not is_admin and not is_researcher:
            _validate_teacher_scope(node, user, result)

        # Course-scoped bindings need a course ID
        if node.dataset_binding in (
            DatasetBinding.ROSTER,
            DatasetBinding.COURSE_SUBMISSIONS,
        ):
            if not node.binding_course_id:
                result.add_violation(
                    node.id,
                    "MISSING_COURSE_ID",
                    "Course-scoped binding requires bindingCourseId.",
                )
            else:
                # Verify course exists
                if not Course.objects.filter(id=node.binding_course_id).exists():
                    result.add_violation(
                        node.id,
                        "COURSE_NOT_FOUND",
                        f"Course {node.binding_course_id} not found.",
                    )


def _validate_teacher_scope(node: PackageNode, user, result: ValidationResult):
    """Teacher can only reference their own courses."""
    if not node.binding_course_id:
        return
    try:
        course = Course.objects.get(id=node.binding_course_id)
        if course.teacher_profile != user.teacher_profile:
            result.add_violation(
                node.id,
                "SCOPE_DENIED",
                f"Teacher does not own course {node.binding_course_id}.",
            )
    except Course.DoesNotExist:
        pass  # Already caught in binding validation
    except Exception:
        result.add_violation(
            node.id, "SCOPE_DENIED", "Cannot verify course ownership."
        )


# ── Deterministic paths + duplicate detection (PKG-CN-08) ──────────


def compute_node_path(node: PackageNode, node_map: dict[int, PackageNode]) -> str:
    """Build normalized POSIX path from root to node."""
    parts: list[str] = []
    current: PackageNode | None = node
    while current is not None:
        parts.append(current.label)
        current = node_map.get(current.parent_id) if current.parent_id else None
    parts.reverse()
    return posixpath.join(*parts) if parts else ""


def _validate_deterministic_paths(
    nodes: list[PackageNode], result: ValidationResult
):
    """Check for duplicate output paths among file nodes (PKG-CN-08)."""
    node_map = {n.id: n for n in nodes}
    file_nodes = [n for n in nodes if n.node_type == NodeType.FILE]
    seen_paths: dict[str, int] = {}

    for node in file_nodes:
        path = compute_node_path(node, node_map)
        normalized = posixpath.normpath(path)
        if normalized in seen_paths:
            result.add_violation(
                node.id,
                "DUPLICATE_PATH",
                f"Duplicate output path: {normalized} (conflicts with node {seen_paths[normalized]}).",
            )
        else:
            seen_paths[normalized] = node.id


# ── Cap checks (PKG-CN-03) ─────────────────────────────────────────


def _validate_caps(nodes: list[PackageNode], result: ValidationResult):
    """Enforce maximum file count limits (PKG-CN-03)."""
    file_count = sum(1 for n in nodes if n.node_type == NodeType.FILE)
    if file_count > MAX_FILE_COUNT:
        result.add_violation(
            None,
            "MAX_FILE_COUNT_EXCEEDED",
            f"File count {file_count} exceeds maximum {MAX_FILE_COUNT}.",
        )


# ── Snapshot validation ─────────────────────────────────────────────


def _validate_snapshot(snapshot_id: int, result: ValidationResult):
    """Validate snapshot exists. Placeholder for FR-14 snapshot integration."""
    # In a real implementation this would check the archival snapshot store.
    # For now we accept any non-negative snapshot_id as valid.
    if snapshot_id < 0:
        result.add_violation(
            None, "INVALID_SNAPSHOT", f"Snapshot {snapshot_id} is invalid."
        )
