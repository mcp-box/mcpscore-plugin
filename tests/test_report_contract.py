"""The skill reads specific fields from `mcpscore --json`; these tests pin that contract."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

import pytest
from check_plugin import check_report, main, values_at

from tests.conftest import FIXTURES

LIVE_TARGET = "https://mcp.deepwiki.com/mcp"


def test_recorded_report_satisfies_the_skill(report: dict[str, Any]) -> None:
    assert check_report(report) == []


def test_main_checks_a_report_file() -> None:
    assert main(["--report", str(FIXTURES / "report-deepwiki.json")]) == 0


@pytest.mark.parametrize("field", ["score", "readiness.counted_in_main", "spec.era"])
def test_missing_field_is_reported(report: dict[str, Any], field: str) -> None:
    *parents, leaf = field.split(".")
    node = report
    for parent in parents:
        node = node[parent]
    del node[leaf]
    assert f"report has no {field}" in check_report(report)


def test_list_field_missing_from_every_element(report: dict[str, Any]) -> None:
    for result in report["results"]:
        result.pop("rule_name")
    assert "report has no results[].rule_name" in check_report(report)


def test_failed_rule_without_a_fix(report: dict[str, Any]) -> None:
    failed = next(r for r in report["results"] if not r["passed"])
    del failed["suggested_fix"]
    assert f"{failed['rule_id']}: failed rule has no suggested_fix" in check_report(report)


def test_unknown_severity(report: dict[str, Any]) -> None:
    report["results"][0]["severity"] = "INFO"
    assert any("unknown severity 'INFO'" in e for e in check_report(report))


def test_new_schema_version_is_flagged(report: dict[str, Any]) -> None:
    report["schema_version"] = 2
    assert any("schema_version is 2" in e for e in check_report(report))


def test_score_out_of_range(report: dict[str, Any]) -> None:
    report["score"] = report["max_score"] + 1
    assert any("is outside 0.." in e for e in check_report(report))


def test_values_at_steps_into_lists() -> None:
    data = {"a": [{"b": {"c": 1}}, {"b": {}}, {"x": 2}]}
    assert values_at(data, "a[].b.c") == [1]
    assert values_at(data, "a[].x") == [2]
    assert values_at(data, "missing[].x") == []


@pytest.mark.live
def test_published_cli_still_satisfies_the_skill() -> None:
    """Audit a live server with the latest mcpscore from PyPI and check the report."""
    uvx = shutil.which("uvx")
    if uvx is None:
        pytest.fail("uvx is not on PATH")
    run = subprocess.run(
        [uvx, "mcpscore@latest", LIVE_TARGET, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        check=False,
    )
    assert run.returncode == 0, run.stderr[-2000:]
    assert check_report(json.loads(run.stdout)) == []
