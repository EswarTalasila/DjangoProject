"""Unit tests for packages.services._validation — tree & binding validation engine.

All database access is mocked so tests run without a live database.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _patch_transaction_atomic(monkeypatch):
    monkeypatch.setattr("django.db.transaction.Atomic.__enter__", lambda self: None)
    monkeypatch.setattr("django.db.transaction.Atomic.__exit__", lambda self, exc_type, exc, tb: False)
    monkeypatch.setattr("django.db.transaction.on_commit", lambda func, using=None: func())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node(id, label="n", node_type="FILE", parent_id=None, dataset_binding=None,
          binding_course_id=None, identifiable=False):
    return SimpleNamespace(
        id=id,
        label=label,
        node_type=node_type,
        parent_id=parent_id,
        dataset_binding=dataset_binding,
        binding_course_id=binding_course_id,
        identifiable=identifiable,
        filters=None,
        include_answers=False,
        source_type="LIVE",
        snapshot=None,
    )


def _workspace(nodes_list):
    ws = MagicMock()
    qs = MagicMock()
    qs.select_related.return_value = qs
    qs.order_by.return_value = nodes_list
    ws.nodes = qs
    return ws


def _user(is_staff=False, is_teacher=False, is_researcher=False, has_export_ident=False):
    u = MagicMock()
    u.is_staff = is_staff
    return u


# ---------------------------------------------------------------------------
# ValidationViolation
# ---------------------------------------------------------------------------

class TestValidationViolation:
    def test_to_dict(self):
        """Violation serializes to dict with nodeId, code, and message."""
        from packages.services._validation import ValidationViolation
        v = ValidationViolation(node_id=5, code="BAD", message="oops")
        d = v.to_dict()
        assert d == {"nodeId": 5, "code": "BAD", "message": "oops"}

    def test_to_dict_none_node(self):
        """Violation with None node_id serializes nodeId as null."""
        from packages.services._validation import ValidationViolation
        v = ValidationViolation(node_id=None, code="X", message="y")
        assert v.to_dict()["nodeId"] is None


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

class TestValidationResult:
    def test_initially_valid(self):
        """New ValidationResult starts as valid with empty violations and warnings."""
        from packages.services._validation import ValidationResult
        r = ValidationResult()
        assert r.valid is True
        assert r.violations == []
        assert r.warnings == []

    def test_add_violation_makes_invalid(self):
        """Adding a violation marks the result as invalid."""
        from packages.services._validation import ValidationResult
        r = ValidationResult()
        r.add_violation(1, "CODE", "msg")
        assert r.valid is False
        assert len(r.violations) == 1

    def test_add_warning(self):
        """Adding a warning does not affect validity."""
        from packages.services._validation import ValidationResult
        r = ValidationResult()
        r.add_warning(2, "W", "warn msg")
        assert r.valid is True  # warnings don't affect validity
        assert len(r.warnings) == 1
        assert r.warnings[0] == {"nodeId": 2, "code": "W", "message": "warn msg"}

    def test_to_dict(self):
        """ValidationResult serializes to dict with valid flag, counts, violations, and warnings."""
        from packages.services._validation import ValidationResult
        r = ValidationResult()
        r.file_count = 3
        r.estimated_rows = 100
        r.add_violation(None, "A", "b")
        r.add_warning(1, "W", "w")
        d = r.to_dict()
        assert d["valid"] is False
        assert d["fileCount"] == 3
        assert d["estimatedRows"] == 100
        assert len(d["violations"]) == 1
        assert len(d["warnings"]) == 1


# ---------------------------------------------------------------------------
# compute_node_path
# ---------------------------------------------------------------------------

class TestComputeNodePath:
    def test_single_node(self):
        """Single root node returns its label as the path."""
        from packages.services._validation import compute_node_path
        n = _node(1, label="root", node_type="FOLDER")
        assert compute_node_path(n, {1: n}) == "root"

    def test_nested_path(self):
        """Child node path includes parent folder label separated by slash."""
        from packages.services._validation import compute_node_path
        root = _node(1, label="data", node_type="FOLDER")
        child = _node(2, label="roster.csv", node_type="FILE", parent_id=1)
        node_map = {1: root, 2: child}
        assert compute_node_path(child, node_map) == "data/roster.csv"

    def test_deep_nesting(self):
        """Deeply nested node produces full slash-separated path from root."""
        from packages.services._validation import compute_node_path
        a = _node(1, label="a", node_type="FOLDER")
        b = _node(2, label="b", node_type="FOLDER", parent_id=1)
        c = _node(3, label="c.csv", node_type="FILE", parent_id=2)
        node_map = {1: a, 2: b, 3: c}
        assert compute_node_path(c, node_map) == "a/b/c.csv"


# ---------------------------------------------------------------------------
# validate_workspace — empty tree
# ---------------------------------------------------------------------------

class TestValidateWorkspaceEmpty:
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_empty_tree(self, mock_role, mock_sudo):
        """Empty workspace tree produces EMPTY_TREE violation."""
        from packages.services._validation import validate_workspace
        ws = _workspace([])
        user = _user()
        result = validate_workspace(ws, user)
        assert not result.valid
        codes = [v.code for v in result.violations]
        assert "EMPTY_TREE" in codes


# ---------------------------------------------------------------------------
# validate_workspace — tree structure
# ---------------------------------------------------------------------------

class TestValidateTreeStructure:
    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_no_root(self, mock_role, mock_sudo, mock_course_objs):
        """Tree with no root-level node produces NO_ROOT violation."""
        from packages.services._validation import validate_workspace
        # A node with a parent but no root
        n = _node(1, label="orphan", node_type="FILE", parent_id=999, dataset_binding="ROSTER", binding_course_id=1)
        mock_course_objs.filter.return_value.exists.return_value = True
        ws = _workspace([n])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "NO_ROOT" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_multiple_roots(self, mock_role, mock_sudo, mock_course_objs):
        """Tree with multiple root nodes produces MULTIPLE_ROOTS violation."""
        from packages.services._validation import validate_workspace
        r1 = _node(1, label="root1", node_type="FOLDER")
        r2 = _node(2, label="root2", node_type="FOLDER")
        ws = _workspace([r1, r2])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "MULTIPLE_ROOTS" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_invalid_node_type(self, mock_role, mock_sudo, mock_course_objs):
        """Node with unrecognized type produces INVALID_NODE_TYPE violation."""
        from packages.services._validation import validate_workspace
        n = _node(1, label="bad", node_type="INVALID")
        ws = _workspace([n])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "INVALID_NODE_TYPE" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_orphan_node(self, mock_role, mock_sudo, mock_course_objs):
        """Node whose parent_id references a nonexistent node produces ORPHAN_NODE violation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        orphan = _node(2, label="o", node_type="FILE", parent_id=999, dataset_binding="ROSTER", binding_course_id=1)
        mock_course_objs.filter.return_value.exists.return_value = True
        ws = _workspace([root, orphan])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "ORPHAN_NODE" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_parent_not_folder(self, mock_role, mock_sudo, mock_course_objs):
        """Node whose parent is a FILE produces PARENT_NOT_FOLDER violation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        file_parent = _node(2, label="f", node_type="FILE", parent_id=1, dataset_binding="ROSTER", binding_course_id=1)
        child = _node(3, label="c", node_type="FILE", parent_id=2, dataset_binding="ROSTER", binding_course_id=1)
        mock_course_objs.filter.return_value.exists.return_value = True
        ws = _workspace([root, file_parent, child])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "PARENT_NOT_FOLDER" in codes


# ---------------------------------------------------------------------------
# validate_workspace — binding validation
# ---------------------------------------------------------------------------

class TestValidateBindings:
    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_missing_binding(self, mock_role, mock_sudo, mock_course_objs):
        """File node without a dataset binding produces MISSING_BINDING violation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1, dataset_binding=None)
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "MISSING_BINDING" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_invalid_binding(self, mock_role, mock_sudo, mock_course_objs):
        """File node with unrecognized binding value produces INVALID_BINDING violation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1, dataset_binding="NONSENSE")
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "INVALID_BINDING" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_missing_course_id_for_roster(self, mock_role, mock_sudo, mock_course_objs):
        """Roster binding without a course ID produces MISSING_COURSE_ID violation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1,
                          dataset_binding="ROSTER", binding_course_id=None)
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "MISSING_COURSE_ID" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_course_not_found(self, mock_role, mock_sudo, mock_course_objs):
        """Binding referencing a nonexistent course produces COURSE_NOT_FOUND violation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1,
                          dataset_binding="ROSTER", binding_course_id=99)
        mock_course_objs.filter.return_value.exists.return_value = False
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "COURSE_NOT_FOUND" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=True)
    def test_identifiable_denied_for_researcher(self, mock_role, mock_sudo, mock_course_objs):
        """Researcher without export permission requesting identifiable data gets IDENTIFIABLE_DENIED."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1,
                          dataset_binding="ROSTER", binding_course_id=1, identifiable=True)
        mock_course_objs.filter.return_value.exists.return_value = True
        user = _user()
        # has_role returns True for RESEARCHER, has_sudo_permission returns False
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, user)
        codes = [v.code for v in result.violations]
        assert "IDENTIFIABLE_DENIED" in codes


# ---------------------------------------------------------------------------
# validate_workspace — teacher scope
# ---------------------------------------------------------------------------

class TestValidateTeacherScope:
    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role")
    def test_teacher_scope_denied(self, mock_role, mock_sudo, mock_course_objs):
        """Teacher accessing a course they do not own produces SCOPE_DENIED violation."""
        from packages.services._validation import validate_workspace
        # has_role returns True for TEACHER, False for RESEARCHER
        def role_side_effect(user, role):
            from accounts.models import Role
            return role == Role.TEACHER
        mock_role.side_effect = role_side_effect

        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1,
                          dataset_binding="ROSTER", binding_course_id=1)
        mock_course_objs.filter.return_value.exists.return_value = True

        teacher_profile = MagicMock()
        mock_course = MagicMock()
        mock_course.teacher_profile = MagicMock()  # different profile
        mock_course_objs.get.return_value = mock_course

        user = _user()
        user.teacher_profile = teacher_profile
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, user)
        codes = [v.code for v in result.violations]
        assert "SCOPE_DENIED" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role")
    def test_teacher_scope_allowed(self, mock_role, mock_sudo, mock_course_objs):
        """Teacher accessing their own course does not produce SCOPE_DENIED."""
        from packages.services._validation import validate_workspace
        def role_side_effect(user, role):
            from accounts.models import Role
            return role == Role.TEACHER
        mock_role.side_effect = role_side_effect

        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1,
                          dataset_binding="ROSTER", binding_course_id=1)
        mock_course_objs.filter.return_value.exists.return_value = True

        teacher_profile = MagicMock()
        mock_course = MagicMock()
        mock_course.teacher_profile = teacher_profile
        mock_course_objs.get.return_value = mock_course

        user = _user()
        user.teacher_profile = teacher_profile
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, user)
        codes = [v.code for v in result.violations]
        assert "SCOPE_DENIED" not in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role")
    def test_teacher_scope_course_does_not_exist(self, mock_role, mock_sudo, mock_course_objs):
        """Teacher scope check with nonexistent course skips SCOPE_DENIED gracefully."""
        from packages.services._validation import validate_workspace
        from courses.models import Course
        def role_side_effect(user, role):
            from accounts.models import Role
            return role == Role.TEACHER
        mock_role.side_effect = role_side_effect

        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1,
                          dataset_binding="ROSTER", binding_course_id=1)
        # Course.objects.filter(...).exists() returns False
        mock_course_objs.filter.return_value.exists.return_value = False
        # Course.objects.get raises DoesNotExist
        mock_course_objs.get.side_effect = Course.DoesNotExist

        user = _user()
        user.teacher_profile = MagicMock()
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, user)
        codes = [v.code for v in result.violations]
        # COURSE_NOT_FOUND from binding check, but no SCOPE_DENIED (DoesNotExist is pass)
        assert "COURSE_NOT_FOUND" in codes
        assert "SCOPE_DENIED" not in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role")
    def test_teacher_scope_generic_exception(self, mock_role, mock_sudo, mock_course_objs):
        """Generic exception during scope check defaults to SCOPE_DENIED."""
        from packages.services._validation import validate_workspace
        def role_side_effect(user, role):
            from accounts.models import Role
            return role == Role.TEACHER
        mock_role.side_effect = role_side_effect

        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="f.csv", node_type="FILE", parent_id=1,
                          dataset_binding="ROSTER", binding_course_id=1)
        mock_course_objs.filter.return_value.exists.return_value = True
        # Course.objects.get raises a generic exception
        mock_course_objs.get.side_effect = RuntimeError("db error")

        user = _user()
        user.teacher_profile = MagicMock()
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, user)
        codes = [v.code for v in result.violations]
        assert "SCOPE_DENIED" in codes


# ---------------------------------------------------------------------------
# validate_workspace — duplicate paths
# ---------------------------------------------------------------------------

class TestValidateDeterministicPaths:
    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_duplicate_path(self, mock_role, mock_sudo, mock_course_objs):
        """Two file nodes with identical paths produce DUPLICATE_PATH violation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        f1 = _node(2, label="same.csv", node_type="FILE", parent_id=1,
                    dataset_binding="ROSTER", binding_course_id=1)
        f2 = _node(3, label="same.csv", node_type="FILE", parent_id=1,
                    dataset_binding="ROSTER", binding_course_id=1)
        mock_course_objs.filter.return_value.exists.return_value = True
        ws = _workspace([root, f1, f2])
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "DUPLICATE_PATH" in codes


# ---------------------------------------------------------------------------
# validate_workspace — cap checks
# ---------------------------------------------------------------------------

class TestValidateCaps:
    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_max_file_count_exceeded(self, mock_role, mock_sudo, mock_course_objs):
        """Exceeding maximum file count produces MAX_FILE_COUNT_EXCEEDED violation."""
        from packages.services._validation import validate_workspace, MAX_FILE_COUNT
        root = _node(0, label="root", node_type="FOLDER")
        nodes = [root]
        for i in range(1, MAX_FILE_COUNT + 2):
            nodes.append(_node(i, label=f"f{i}.csv", node_type="FILE", parent_id=0,
                               dataset_binding="ROSTER", binding_course_id=1))
        mock_course_objs.filter.return_value.exists.return_value = True
        ws = _workspace(nodes)
        result = validate_workspace(ws, _user())
        codes = [v.code for v in result.violations]
        assert "MAX_FILE_COUNT_EXCEEDED" in codes


# ---------------------------------------------------------------------------
# validate_workspace — snapshot validation
# ---------------------------------------------------------------------------

class TestValidateSnapshot:
    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_negative_snapshot_id(self, mock_role, mock_sudo, mock_course_objs):
        """Negative snapshot_id produces INVALID_SNAPSHOT violation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        ws = _workspace([root])
        result = validate_workspace(ws, _user(), snapshot_id=-1)
        codes = [v.code for v in result.violations]
        assert "INVALID_SNAPSHOT" in codes

    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_valid_snapshot_id(self, mock_role, mock_sudo, mock_course_objs):
        """Positive snapshot_id does not produce INVALID_SNAPSHOT violation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        ws = _workspace([root])
        result = validate_workspace(ws, _user(), snapshot_id=10)
        codes = [v.code for v in result.violations]
        assert "INVALID_SNAPSHOT" not in codes


# ---------------------------------------------------------------------------
# validate_workspace — valid tree
# ---------------------------------------------------------------------------

class TestValidateWorkspaceValid:
    @patch("packages.services._validation.Course.objects")
    @patch("packages.services._validation.has_sudo_permission", return_value=False)
    @patch("packages.services._validation.has_role", return_value=False)
    def test_valid_workspace(self, mock_role, mock_sudo, mock_course_objs):
        """Well-formed workspace with valid bindings passes validation."""
        from packages.services._validation import validate_workspace
        root = _node(1, label="root", node_type="FOLDER")
        file_node = _node(2, label="roster.csv", node_type="FILE", parent_id=1,
                          dataset_binding="ROSTER", binding_course_id=1)
        mock_course_objs.filter.return_value.exists.return_value = True
        ws = _workspace([root, file_node])
        result = validate_workspace(ws, _user())
        assert result.valid is True
        assert result.file_count == 1
