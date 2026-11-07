"""scripts/release.py: the preflight checks and the release it creates."""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING, Any

import pytest
import release

from tests.conftest import edit_json

if TYPE_CHECKING:
    from pathlib import Path

FIRST = "https://github.com/mcp-box/mcpscore-plugin/releases/tag/mcpscore--v0.1.0"
COMPARE = "https://github.com/mcp-box/mcpscore-plugin/compare/mcpscore--v0.1.0...mcpscore--v0.2.0"


@pytest.fixture
def root(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(release, "ROOT", repo)
    return repo


def write_changelog(root: Path, text: str) -> None:
    (root / "CHANGELOG.md").write_text(text, encoding="utf-8")


TWO_RELEASES = (
    "# Changelog\n\n## [Unreleased]\n\n## [0.2.0] - 2026-12-01\n\n### Fixed\n\n- Second.\n\n"
    "## [0.1.0] - 2026-11-07\n\n### Added\n\n- First.\n\n"
    "[Unreleased]: https://github.com/mcp-box/mcpscore-plugin/compare/mcpscore--v0.2.0...HEAD\n"
    f"[0.2.0]: {COMPARE}\n"
    f"[0.1.0]: {FIRST}\n"
)


def test_tag_follows_claude_codes_plugin_convention() -> None:
    assert release.tag_name("0.1.0") == "mcpscore--v0.1.0"


class TestVersion:
    def test_reads_the_manifest_version(self, root: Path) -> None:
        expected = json.loads((root / "plugins/mcpscore/.claude-plugin/plugin.json").read_text(encoding="utf-8"))
        assert release.read_version() == expected["version"]

    def test_manifests_that_disagree_stop_the_release(self, root: Path) -> None:
        edit_json(root / "plugins/mcpscore/.cursor-plugin/plugin.json", version="9.9.9")
        with pytest.raises(SystemExit):
            release.read_version()

    @pytest.mark.parametrize("version", ["0.1", "0.1.0-rc.1", "v0.1.0", "01.0.0"])
    def test_only_stable_versions_release(self, root: Path, version: str) -> None:
        for agent in ("claude", "codex", "cursor"):
            edit_json(root / f"plugins/mcpscore/.{agent}-plugin/plugin.json", version=version)
        with pytest.raises(SystemExit):
            release.read_version()


class TestChangelog:
    def test_first_release_notes_exclude_the_link_block(self, root: Path) -> None:
        text = f"# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-11-07\n\n- First.\n\n[0.1.0]: {FIRST}\n"
        write_changelog(root, text)
        assert release.check_changelog("0.1.0") == "- First."

    def test_later_release_links_the_comparison(self, root: Path) -> None:
        write_changelog(root, TWO_RELEASES)
        assert release.check_changelog("0.2.0") == "### Fixed\n\n- Second."

    @pytest.mark.parametrize(
        "wrong",
        [
            "[0.2.0]: https://example.com",
            "[0.2.0]: https://github.com/mcp-box/mcpscore-plugin/compare/v0.1.0...v0.2.0",
            "[0.2.0]: https://github.com/mcp-box/mcpscore-action/compare/mcpscore--v0.1.0...mcpscore--v0.2.0",
        ],
    )
    def test_a_wrong_compare_link_stops_the_release(self, root: Path, wrong: str) -> None:
        write_changelog(root, TWO_RELEASES.replace(f"[0.2.0]: {COMPARE}", wrong))
        with pytest.raises(SystemExit):
            release.check_changelog("0.2.0")

    def test_no_section_stops_the_release(self, root: Path) -> None:
        write_changelog(root, TWO_RELEASES)
        with pytest.raises(SystemExit):
            release.check_changelog("0.3.0")

    def test_an_empty_section_stops_the_release(self, root: Path) -> None:
        write_changelog(root, f"# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-11-07\n\n[0.1.0]: {FIRST}\n")
        with pytest.raises(SystemExit):
            release.check_changelog("0.1.0")

    def test_conflict_markers_stop_the_release(self, root: Path) -> None:
        write_changelog(root, "<<<<<<< HEAD\n" + TWO_RELEASES)
        with pytest.raises(SystemExit):
            release.check_changelog("0.2.0")


def test_this_repositorys_changelog_is_ready_for_its_version() -> None:
    version = release.read_version()
    assert release.check_changelog(version)


class TestPluginChecks:
    def test_pass_on_this_repository(self, root: Path) -> None:
        release.check_plugin_files()

    def test_a_broken_manifest_stops_the_release(self, root: Path) -> None:
        shutil.rmtree(root / "plugins/mcpscore/.codex-plugin")
        with pytest.raises(SystemExit):
            release.check_plugin_files()


def fake_run(monkeypatch: pytest.MonkeyPatch, answers: dict[str, str]) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []

    def run(*args: str) -> str:
        calls.append(args)
        return answers[" ".join(args)]

    monkeypatch.setattr(release, "run", run)
    return calls


class TestGitState:
    SYNCED = {  # noqa: RUF012
        "git branch --show-current": "main",
        "git status --porcelain": "",
        "git rev-parse HEAD": "abc123",
        f"gh api repos/{release.REPO}/commits/main --jq .sha": "abc123",
    }

    def test_clean_synced_main_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_run(monkeypatch, self.SYNCED)
        assert release.check_git_state() == "abc123"

    @pytest.mark.parametrize(
        "change",
        [
            {"git branch --show-current": "feat/x"},
            {"git branch --show-current": ""},
            {"git status --porcelain": " M CHANGELOG.md"},
            {f"gh api repos/{release.REPO}/commits/main --jq .sha": "def456"},
        ],
    )
    def test_anything_else_stops_the_release(self, monkeypatch: pytest.MonkeyPatch, change: dict[str, str]) -> None:
        fake_run(monkeypatch, {**self.SYNCED, **change})
        with pytest.raises(SystemExit):
            release.check_git_state()


class Completed:
    def __init__(self, returncode: int, stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = ""
        self.stderr = stderr


class TestTagAbsent:
    def test_a_404_means_unused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(release.subprocess, "run", lambda *a, **k: Completed(1, "gh: Not Found (HTTP 404)"))
        release.check_tag_absent("0.1.0")

    def test_an_existing_tag_stops_the_release(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(release.subprocess, "run", lambda *a, **k: Completed(0))
        with pytest.raises(SystemExit):
            release.check_tag_absent("0.1.0")

    def test_another_error_stops_the_release(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(release.subprocess, "run", lambda *a, **k: Completed(1, "HTTP 500"))
        with pytest.raises(SystemExit):
            release.check_tag_absent("0.1.0")


def check_run(name: str, conclusion: str | None = "success", when: str = "2") -> dict[str, Any]:
    status = "completed" if conclusion else "in_progress"
    return {"name": name, "status": status, "conclusion": conclusion, "started_at": when, "completed_at": when}


ALL_GREEN = [check_run(name) for name in sorted(release.REQUIRED_CHECKS)]


class TestCiGreen:
    def runs(self, monkeypatch: pytest.MonkeyPatch, runs: list[dict[str, Any]]) -> None:
        monkeypatch.setattr(release, "run", lambda *a: json.dumps(runs))

    def test_green(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.runs(monkeypatch, [*ALL_GREEN, check_run("canary", "skipped"), check_run("Analyze (python)")])
        release.check_ci_green("abc")

    def test_a_missing_required_check_stops_the_release(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.runs(monkeypatch, [r for r in ALL_GREEN if r["name"] != "live-report"])
        with pytest.raises(SystemExit):
            release.check_ci_green("abc")

    def test_a_skipped_required_check_stops_the_release(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.runs(monkeypatch, [check_run(r["name"], "skipped") if r["name"] == "validate" else r for r in ALL_GREEN])
        with pytest.raises(SystemExit):
            release.check_ci_green("abc")

    def test_review_bots_are_not_gates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.runs(monkeypatch, [*ALL_GREEN, check_run("copilot-pull-request-reviewer", None)])
        release.check_ci_green("abc")

    def test_the_latest_run_of_a_check_counts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.runs(monkeypatch, [check_run("check", "failure", when="1"), *ALL_GREEN])
        release.check_ci_green("abc")

    def test_red_stops_the_release(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.runs(monkeypatch, [*ALL_GREEN, check_run("Analyze (python)", "failure")])
        with pytest.raises(SystemExit):
            release.check_ci_green("abc")

    def test_no_runs_stop_the_release(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.runs(monkeypatch, [])
        with pytest.raises(SystemExit):
            release.check_ci_green("abc")


class TestCreateRelease:
    def test_creates_the_tagged_release_at_head(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, ...]] = []

        def run(*args: str) -> str:
            calls.append(args)
            return "abc123" if args[:2] == ("gh", "api") else ""

        monkeypatch.setattr(release, "run", run)
        release.create_release("0.1.0", "- First.", "abc123")
        create = calls[0]
        assert create[:4] == ("gh", "release", "create", "mcpscore--v0.1.0")
        assert create[create.index("--target") + 1] == "abc123"

    def test_a_tag_on_another_commit_is_reported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(release, "run", lambda *a: "def456" if a[:2] == ("gh", "api") else "")
        with pytest.raises(SystemExit):
            release.create_release("0.1.0", "- First.", "abc123")


class TestMain:
    @pytest.fixture
    def preflight(self, monkeypatch: pytest.MonkeyPatch) -> list[str]:
        created: list[str] = []
        monkeypatch.setattr(release, "read_version", lambda: "0.1.0")
        monkeypatch.setattr(release, "preflight", lambda: ("0.1.0", "abc123", "- First."))
        monkeypatch.setattr(release, "create_release", lambda version, notes, target: created.append(version))
        return created

    def test_dry_run_creates_nothing(self, preflight: list[str]) -> None:
        release.main(["--dry-run"])
        assert preflight == []

    def test_no_confirmation_creates_nothing(self, preflight: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("builtins.input", lambda _prompt: "n")
        with pytest.raises(SystemExit):
            release.main([])
        assert preflight == []

    def test_closed_stdin_creates_nothing(self, preflight: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
        def eof(_prompt: str) -> str:
            raise EOFError

        monkeypatch.setattr("builtins.input", eof)
        with pytest.raises(SystemExit):
            release.main([])
        assert preflight == []

    def test_yes_creates_the_release(self, preflight: list[str]) -> None:
        release.main(["--yes"])
        assert preflight == ["0.1.0"]
