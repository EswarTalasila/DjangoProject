"""Workflow test entry point.

Run all workflow tests in a predictable order:
python -m tests.integration.workflow_suite
"""

from __future__ import annotations

from pathlib import Path

import pytest

WORKFLOW_FILES = [
    "test_workflows.py",
    "test_workflows_extended.py",
]


def run() -> int:
    """Test that run."""
    base = Path(__file__).resolve().parent
    files = [str(base / name) for name in WORKFLOW_FILES]
    return pytest.main(files)


if __name__ == "__main__":
    raise SystemExit(run())
