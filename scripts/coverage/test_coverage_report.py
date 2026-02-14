"""Tests for scripts.coverage.coverage_report."""

from __future__ import annotations

from pathlib import Path

from scripts.coverage import coverage_report as cr


def test_extract_expected_ids_normalizes_wildcards(tmp_path: Path) -> None:
    doc = tmp_path / "FR-01-Auth.md"
    doc.write_text(
        "\n".join(
            [
                "- test_AUTH_UC_01",
                "- test_AUTH_UC_02_*",
                "- test_AUTH_CN_04",
                "- test_REG_UC_01",  # ignored (wrong domain)
            ]
        ),
        encoding="utf-8",
    )
    expected = cr._extract_expected_ids(doc, "AUTH")
    assert expected == {"test_AUTH_UC_01", "test_AUTH_UC_02", "test_AUTH_CN_04"}


def test_parse_junit_test_ids_tracks_seen_and_passed(tmp_path: Path) -> None:
    xml_path = tmp_path / "coverage.junit.xml"
    xml_path.write_text(
        """\
<testsuite tests="3">
  <testcase classname="tests.integration.t" name="test_AUTH_UC_01" />
  <testcase classname="tests.integration.t" name="test_AUTH_UC_02">
    <failure message="boom" />
  </testcase>
  <testcase classname="tests.integration.t" name="test_REG_UC_01">
    <skipped />
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )
    seen, passed = cr._parse_junit_test_ids(xml_path)
    assert seen == {"test_AUTH_UC_01", "test_AUTH_UC_02", "test_REG_UC_01"}
    assert passed == {"test_AUTH_UC_01"}


def test_aggregate_module_coverage() -> None:
    coverage_data = {
        "files": {
            "src/accounts/services.py": {
                "summary": {
                    "num_statements": 10,
                    "missing_lines": 2,
                    "num_branches": 4,
                    "missing_branches": 1,
                }
            },
            "src/accounts/views.py": {
                "summary": {
                    "num_statements": 20,
                    "missing_lines": 5,
                    "num_branches": 6,
                    "missing_branches": 2,
                }
            },
            "src/courses/services.py": {
                "summary": {
                    "num_statements": 8,
                    "missing_lines": 1,
                    "num_branches": 2,
                    "missing_branches": 0,
                }
            },
        }
    }
    rows = {row["name"]: row for row in cr._aggregate_module_coverage(coverage_data)}
    assert rows["accounts"]["statements"] == 30
    assert rows["accounts"]["missing"] == 7
    assert rows["accounts"]["branches"] == 10
    assert rows["accounts"]["branch_missing"] == 3
    assert rows["courses"]["statements"] == 8
    assert rows["courses"]["missing"] == 1


def test_evaluate_gate_global_and_domain() -> None:
    fr_rows = [
        {"fr": "FR-01", "pass_rate": 100.0},
        {"fr": "FR-02", "pass_rate": 50.0},
    ]
    ok_none, _ = cr._evaluate_gate(
        gate_mode="none",
        min_pct=80.0,
        domain=None,
        global_total_pct=10.0,
        fr_rows=fr_rows,
        global_threshold=80.0,
    )
    assert ok_none

    ok_global, _ = cr._evaluate_gate(
        gate_mode="global",
        min_pct=80.0,
        domain=None,
        global_total_pct=79.9,
        fr_rows=fr_rows,
        global_threshold=80.0,
    )
    assert not ok_global

    ok_domain, _ = cr._evaluate_gate(
        gate_mode="domain",
        min_pct=80.0,
        domain="FR-01",
        global_total_pct=0.0,
        fr_rows=fr_rows,
        global_threshold=0.0,
    )
    assert ok_domain

    bad_domain, _ = cr._evaluate_gate(
        gate_mode="domain",
        min_pct=80.0,
        domain="FR-02",
        global_total_pct=0.0,
        fr_rows=fr_rows,
        global_threshold=0.0,
    )
    assert not bad_domain


def test_format_pytest_result_line_supports_standard_and_xdist() -> None:
    width = 120
    standard = (
        "tests/integration/test_accounts_routes.py::TestAccountRoutes::test_AUTH_UC_01 "
        "- ADMIN login via identifier. PASSED [ 25%]\n"
    )
    xdist = (
        "[gw1] [ 94%] PASSED "
        "tests/integration/test_auth_reg_completion.py::TestAuthRegCompletion::test_REG_CN_12 "
        "- All generated codes require explicit expiration input.\n"
    )
    formatted_standard = cr._format_pytest_result_line(standard, width)
    formatted_xdist = cr._format_pytest_result_line(xdist, width)

    assert formatted_standard is not None
    assert formatted_xdist is not None
    assert "[PASSED]" in formatted_standard
    assert "[PASSED]" in formatted_xdist
    assert " | " in formatted_standard
    assert " | " in formatted_xdist


def test_bannerize_line_normalizes_generated_xml_banner() -> None:
    width = 120
    raw = (
        "------------------------------------- generated xml file: "
        "/app/coverage.junit.xml --------------------------------------\n"
    )
    banner = cr._bannerize_line(raw, width)
    assert banner is not None
    plain = cr._strip_ansi(banner.rstrip("\n"))
    assert plain.startswith("-")
    assert plain.endswith("-")
    assert "generated xml file: /app/coverage.junit.xml" in plain


def test_is_xdist_preface_line_detection() -> None:
    preface = (
        "tests/integration/test_accounts_routes.py::TestAccountRoutes::test_AUTH_UC_07_ADMIN "
        "- Admin can approve any role's reset request.\n"
    )
    result = (
        "[gw0] [ 99%] PASSED "
        "tests/integration/test_accounts_routes.py::TestAccountRoutes::test_AUTH_UC_07_ADMIN "
        "- Admin can approve any role's reset request.\n"
    )
    assert cr._is_xdist_preface_line(preface)
    assert not cr._is_xdist_preface_line(result)
