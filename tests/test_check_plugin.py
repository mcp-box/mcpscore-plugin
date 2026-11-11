from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from check_plugin import check_repo, main, png_size

from tests.conftest import ROOT, edit_json

PLUGIN = Path("plugins/mcpscore")
SKILL = PLUGIN / "skills/audit/SKILL.md"


def test_this_repository_passes() -> None:
    assert check_repo(ROOT) == []


def test_copy_passes(repo: Path) -> None:
    assert check_repo(repo) == []


def test_main_exits_zero_on_this_repository(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "passed" in capsys.readouterr().out


@pytest.mark.parametrize("agent_dir", [".codex-plugin", ".cursor-plugin"])
@pytest.mark.parametrize("key", ["version", "description", "name"])
def test_agent_manifests_must_agree(repo: Path, agent_dir: str, key: str) -> None:
    edit_json(repo / PLUGIN / agent_dir / "plugin.json", **{key: "drifted"})
    assert any(f"{agent_dir}/plugin.json {key!r} differs" in e for e in check_repo(repo))


def test_missing_agent_manifest(repo: Path) -> None:
    (repo / PLUGIN / ".cursor-plugin/plugin.json").unlink()
    assert "missing plugins/mcpscore/.cursor-plugin/plugin.json" in check_repo(repo)


def test_version_must_be_semver(repo: Path) -> None:
    for agent_dir in (".claude-plugin", ".codex-plugin", ".cursor-plugin"):
        edit_json(repo / PLUGIN / agent_dir / "plugin.json", version="0.1")
    assert any("is not MAJOR.MINOR.PATCH" in e for e in check_repo(repo))


def test_icon_must_be_a_square_png(repo: Path) -> None:
    (repo / PLUGIN / ".claude-plugin/icon.png").write_bytes(b"not a png")
    assert "plugins/mcpscore/.claude-plugin/icon.png is not a PNG" in check_repo(repo)


def test_png_size_reads_the_header() -> None:
    assert png_size(ROOT / PLUGIN / ".claude-plugin/icon.png") == (512, 512)


@pytest.mark.parametrize(
    "marketplace",
    [".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json", ".cursor-plugin/marketplace.json"],
)
def test_every_marketplace_lists_the_plugin(repo: Path, marketplace: str) -> None:
    edit_json(repo / marketplace, plugins=[])
    assert f"{marketplace} does not list the 'mcpscore' plugin" in check_repo(repo)


def test_marketplace_source_must_point_at_the_plugin(repo: Path) -> None:
    path = repo / ".claude-plugin/marketplace.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["plugins"][0]["source"] = "./plugin"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert any("source './plugin' is not plugins/mcpscore" in e for e in check_repo(repo))


def test_marketplace_description_must_match(repo: Path) -> None:
    path = repo / ".cursor-plugin/marketplace.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["plugins"][0]["description"] = "something else"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert ".cursor-plugin/marketplace.json description differs from plugin.json" in check_repo(repo)


def test_skill_name_must_match_folder(repo: Path) -> None:
    path = repo / SKILL
    path.write_text(path.read_text(encoding="utf-8").replace("name: audit", "name: check", 1), encoding="utf-8")
    assert any("name 'check' does not match its folder" in e for e in check_repo(repo))


def test_skill_needs_frontmatter(repo: Path) -> None:
    (repo / SKILL).write_text("# no frontmatter\n", encoding="utf-8")
    assert any("no YAML frontmatter" in e for e in check_repo(repo))


def test_skill_description_length(repo: Path) -> None:
    path = repo / SKILL
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("description: ", "description: " + "x" * 1100, 1), encoding="utf-8")
    assert any("characters; max 1024" in e for e in check_repo(repo))


def test_skill_must_mention_every_report_field(repo: Path) -> None:
    path = repo / SKILL
    path.write_text(path.read_text(encoding="utf-8").replace("counted_in_main", "counted"), encoding="utf-8")
    assert "skills/audit/SKILL.md never mentions report field 'counted_in_main'" in check_repo(repo)


def test_eval_case_name_must_match_folder(repo: Path) -> None:
    case = repo / PLUGIN / "evals/not-mcp-code/case.yaml"
    case.write_text(case.read_text(encoding="utf-8").replace("name: not-mcp-code", "name: other"), encoding="utf-8")
    assert any("case.yaml name 'other' does not match its folder" in e for e in check_repo(repo))


def test_eval_case_needs_graders(repo: Path) -> None:
    for grader in (repo / PLUGIN / "evals/use-not-build/graders").iterdir():
        grader.unlink()
    assert "plugins/mcpscore/evals/use-not-build has no graders" in check_repo(repo)


def test_eval_results_folder_is_not_a_case(repo: Path) -> None:
    (repo / PLUGIN / "evals/results/2026-11-11T11-03-58-269Z").mkdir(parents=True)
    assert check_repo(repo) == []


def test_eval_scaffold_must_be_executable(repo: Path) -> None:
    (repo / PLUGIN / "evals/not-mcp-code/scaffold.sh").chmod(0o644)
    assert "plugins/mcpscore/evals/not-mcp-code/scaffold.sh is not executable" in check_repo(repo)


def test_changelog_needs_unreleased(repo: Path) -> None:
    path = repo / "CHANGELOG.md"
    path.write_text(path.read_text(encoding="utf-8").replace("## [Unreleased]", "## Next"), encoding="utf-8")
    assert "CHANGELOG.md has no [Unreleased] section" in check_repo(repo)


def test_manifest_version_cannot_trail_the_changelog(repo: Path) -> None:
    path = repo / "CHANGELOG.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n## [9.0.0] - 2026-11-07\n", encoding="utf-8")
    assert any("older than CHANGELOG.md's latest release" in e for e in check_repo(repo))


@pytest.mark.parametrize(
    ("name", "line", "message"),
    [
        (
            "plugins/mcpscore/skills/audit/SKILL.md",
            "uvx mcpscore@latest <target> --json",
            "an option after <target> goes to the server under --stdio",
        ),
        ("README.md", "1. Runs `mcpscore <target> --json` on a server", "an option after <target>"),
        (
            "plugins/mcpscore/skills/audit/SKILL.md",
            'you pass `--token "$TOKEN"`, or a header',
            "--token with a variable puts the token in the process list",
        ),
        ("plugins/mcpscore/README.md", "mcpscore https://x.example/mcp --token $TOKEN", "--token with a variable"),
        ("README.md", 'mcpscore --token="$TOKEN" https://x.example/mcp', "--token with a variable"),
        ("README.md", "mcpscore --token=${TOKEN} https://x.example/mcp", "--token with a variable"),
        ("README.md", '"Bash(uvx mcpscore@latest:*)"', "a wildcard permission rule for mcpscore"),
        ("README.md", '"Bash(uvx mcpscore@latest --json https://:*)"', "a wildcard permission rule for mcpscore"),
        ("plugins/mcpscore/README.md", "allow `Bash(pipx run mcpscore *)`", "a wildcard permission rule for mcpscore"),
        (
            "README.md",
            '"Bash(uvx mcpscore@latest * https://your-server.example/mcp)"',
            "a wildcard permission rule for mcpscore",
        ),
        (
            "README.md",
            '"Bash(uvx mcpscore@latest --json https://*.example/mcp)"',
            "a wildcard permission rule for mcpscore",
        ),
        ("README.md", '"Bash(* mcpscore --json https://your-server.example/mcp)"', "a wildcard permission rule"),
        ("SECURITY.md", "allow `Bash(uvx mcpscore@latest:*)`", "a wildcard permission rule for mcpscore"),
        (
            "plugins/mcpscore/skills/audit/SKILL.md",
            "the rule `Bash(uvx mcpscore@latest:*)` covers it",
            "a wildcard permission rule for mcpscore",
        ),
    ],
)
def test_commands_keep_options_before_the_target_and_tokens_off_the_command_line(
    repo: Path, name: str, line: str, message: str
) -> None:
    path = repo / name
    if not path.exists():
        shutil.copy2(ROOT / name, path)
    path.write_text(path.read_text(encoding="utf-8") + "\n" + line + "\n", encoding="utf-8")
    assert any(message in error for error in check_repo(repo))


def test_options_before_the_target_pass(repo: Path) -> None:
    path = repo / "plugins/mcpscore/skills/audit/SKILL.md"
    safe = (
        "\nuvx mcpscore@latest --json <target>\nexport MCPSCORE_TOKEN; mcpscore --token-file x <target>\n"
        '"Bash(uvx mcpscore@latest --json https://your-server.example/mcp)"\n'
    )
    path.write_text(path.read_text(encoding="utf-8") + safe, encoding="utf-8")
    assert check_repo(repo) == []
