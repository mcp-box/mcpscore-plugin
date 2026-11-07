#!/usr/bin/env python3
"""Cut a release of the plugin: create the GitHub Release on tag mcpscore--v<version>.

Usage:
    uv run python scripts/release.py [--dry-run] [--yes]
    make release          # same, with a confirmation prompt
    make release-dry-run  # checks only, creates nothing

The version is read from the plugin's manifests. A plugin has no registry:
agents install it from this repository, so a release is a tag that pins the
version and a GitHub Release that says what changed. The tag uses Claude
Code's convention for plugin releases, `{name}--v{version}` (the format
`claude plugin tag` creates).

Checks performed before anything is created:
  1. on `main`, clean working tree, local HEAD in sync with origin/main
  2. `scripts/check_plugin.py` passes: the three plugin.json files agree,
     and the version is a stable X.Y.Z
  3. CHANGELOG.md has a `## [<version>]` section AND its compare link
  4. the tag does not already exist on the remote
  5. CI is green for HEAD (checks, validator, and the live report contract)

The agent evals are not checked here: run `make eval` in the release PR.

Requires: git, gh (authenticated).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, NoReturn

from check_plugin import AGENT_MANIFEST_DIRS, PLUGIN_NAME, SEMVER, check_repo, load_json, plugin_dir

REPO = "mcp-box/mcpscore-plugin"
ROOT = Path(__file__).resolve().parent.parent

REVIEW_BOT_CHECKS = frozenset({"copilot-pull-request-reviewer", "Cursor Bugbot"})
"""Check runs registered by code-review bots: reviews, not CI gates."""

REQUIRED_CHECKS = frozenset({"check", "validate", "live-report"})
"""Jobs that must have run and passed on HEAD: for these only `success` counts.
Other checks may be skipped or neutral."""

LINK_DEFINITION = re.compile(r"^\[[^\]]+\]:\s+\S+\s*$")
"""A Markdown reference-link definition line, e.g. ``[0.1.0]: https://...``."""


def run(*args: str) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=True, cwd=ROOT)  # noqa: S603
    except FileNotFoundError:
        fail(f"required tool not found: {args[0]}: install it and retry")
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        fail(f"command failed: {' '.join(args)}\n  {stderr or e}")
    return (result.stdout or "").strip()


def fail(message: str) -> NoReturn:
    print(f"✗ {message}", file=sys.stderr)
    sys.exit(1)


def ok(message: str) -> None:
    print(f"✓ {message}")


def tag_name(version: str) -> str:
    return f"{PLUGIN_NAME}--v{version}"


def read_version() -> str:
    """The version all three manifests carry; fail if they disagree or it isn't X.Y.Z."""
    versions = {load_json(plugin_dir(ROOT) / d / "plugin.json").get("version") for d in AGENT_MANIFEST_DIRS}
    if len(versions) != 1:
        fail(f"the plugin.json files disagree on the version: {sorted(map(str, versions))}")
    version = str(versions.pop())
    if not SEMVER.match(version):
        fail(f"version {version!r} is not a stable X.Y.Z release")
    return version


def check_git_state() -> str:
    """Verify the repo is releasable from main; return HEAD's sha."""
    branch = run("git", "branch", "--show-current")
    if not branch:
        fail("detached HEAD: check out main to release")
    if branch != "main":
        fail(f"must release from main (currently on '{branch}')")
    if run("git", "status", "--porcelain"):
        fail("working tree is not clean")
    head = run("git", "rev-parse", "HEAD")
    remote_head = run("gh", "api", f"repos/{REPO}/commits/main", "--jq", ".sha")
    if head != remote_head:
        fail(f"local main ({head[:9]}) != origin/main ({remote_head[:9]}): push or pull first")
    ok(f"on main, clean, in sync with origin ({head[:9]})")
    return head


def check_plugin_files() -> None:
    errors = check_repo(ROOT)
    if errors:
        fail("plugin checks failed:\n  " + "\n  ".join(errors))
    ok("plugin checks pass (manifests, marketplaces, skill, evals, changelog)")


def check_changelog(version: str) -> str:
    """Verify the CHANGELOG section and compare link; return the release notes."""
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if re.search(r"^(<{7} |={7}$|>{7} )", changelog, flags=re.MULTILINE):
        fail("CHANGELOG.md contains unresolved merge conflict markers")
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        changelog,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        fail(f"CHANGELOG.md has no '## [{version}]' section")
    expected = expected_compare_link(changelog, version)
    if not re.search(rf"^{re.escape(expected)}$", changelog, flags=re.MULTILINE):
        fail(f"CHANGELOG.md is missing the compare link for {version}; expected exactly:\n  {expected}")
    notes = release_notes(match.group(1))
    if not notes:
        fail(f"CHANGELOG.md's [{version}] section is empty")
    ok(f"CHANGELOG has the [{version}] section and compare link")
    return notes


def release_notes(section: str) -> str:
    """A CHANGELOG section body without the reference-link block the last section runs into."""
    lines = [line for line in section.splitlines() if not LINK_DEFINITION.match(line)]
    return "\n".join(lines).strip()


def expected_compare_link(changelog: str, version: str) -> str:
    """The link for `version`: a comparison with the release below it, or the tag for a first release."""
    headings = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, flags=re.MULTILINE)
    if version not in headings:
        fail(f"CHANGELOG.md has no '## [{version}]' section")
    index = headings.index(version)
    previous = headings[index + 1] if index + 1 < len(headings) else None
    if previous is None:
        return f"[{version}]: https://github.com/{REPO}/releases/tag/{tag_name(version)}"
    return f"[{version}]: https://github.com/{REPO}/compare/{tag_name(previous)}...{tag_name(version)}"


def check_tag_absent(version: str) -> None:
    tag = tag_name(version)
    result = subprocess.run(  # noqa: S603
        ["gh", "api", f"repos/{REPO}/git/ref/tags/{tag}"],  # noqa: S607
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode == 0:
        fail(f"tag {tag} already exists on the remote: bump the version in all three plugin.json files")
    output = (result.stderr or "") + (result.stdout or "")
    if "404" not in output and "Not Found" not in output:
        fail(f"could not verify tag {tag} (gh api error, not a 404):\n  {output.strip()}")
    ok(f"tag {tag} is unused")


def check_ci_green(sha: str) -> None:
    raw = run(
        "gh",
        "api",
        f"repos/{REPO}/commits/{sha}/check-runs",
        "--jq",
        "[.check_runs[] | {name, status, conclusion, started_at, completed_at}]",
    )
    latest: dict[str, dict[str, Any]] = {}
    for check in json.loads(raw):
        if check["name"] in REVIEW_BOT_CHECKS:
            continue
        seen = latest.get(check["name"])
        if seen is None or _when(check) > _when(seen):
            latest[check["name"]] = check
    if not latest:
        fail("no CI check runs found for HEAD: has CI finished?")
    missing = sorted(REQUIRED_CHECKS - set(latest))
    if missing:
        fail(f"required CI checks have not run on HEAD: {', '.join(missing)}")
    bad = [c for c in latest.values() if c["status"] != "completed" or c["conclusion"] not in _green(c["name"])]
    if bad:
        details = ", ".join(f"{c['name']}: {c['conclusion'] or c['status']}" for c in bad)
        fail(f"CI is not green for HEAD: {details}")
    ok(f"CI green for HEAD ({len(latest)} checks)")


def _when(check: dict[str, Any]) -> str:
    return check["completed_at"] or check["started_at"] or ""


def _green(name: str) -> tuple[str, ...]:
    return ("success",) if name in REQUIRED_CHECKS else ("success", "skipped", "neutral")


def create_release(version: str, notes: str, target: str) -> None:
    tag = tag_name(version)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(notes + "\n")
        notes_file = f.name
    try:
        run(
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            REPO,
            "--target",
            target,
            "--title",
            f"{PLUGIN_NAME} {version}",
            "--notes-file",
            notes_file,
            "--latest",
        )
    finally:
        Path(notes_file).unlink(missing_ok=True)
    tagged = run("gh", "api", f"repos/{REPO}/commits/{tag}", "--jq", ".sha")
    if tagged != target:
        fail(f"tag {tag} points at {tagged[:9]}, not {target[:9]}: check the release")
    ok(f"GitHub Release {tag} created at {target[:9]}")


def preflight() -> tuple[str, str, str]:
    """Run every releasable-state check; return (version, head sha, release notes)."""
    version = read_version()
    head = check_git_state()
    check_plugin_files()
    notes = check_changelog(version)
    check_tag_absent(version)
    check_ci_green(head)
    return version, head, notes


def confirm(version: str) -> bool:
    """Ask before creating anything; a closed stdin counts as 'no'."""
    try:
        answer = input(f"Create GitHub Release {tag_name(version)}? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        print("\naborted (no confirmation)")
        return False
    return answer.strip().lower() == "y"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="run all checks, create nothing")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args(argv)

    print(f"Releasing the {PLUGIN_NAME} plugin {read_version()}\n", flush=True)
    version, head, notes = preflight()
    print(f"\n--- release notes (from CHANGELOG) ---\n{notes}\n--------------------------------------\n")

    if args.dry_run:
        ok(f"dry run: all checks passed; would create {tag_name(version)} at {head[:9]}")
        return
    if not args.yes and not confirm(version):
        sys.exit(1)

    # main may have moved while the prompt was open.
    version, head, notes = preflight()
    create_release(version, notes, head)
    print(
        f"\nhttps://github.com/{REPO}/releases/tag/{tag_name(version)}\n"
        f"Install: /plugin install {PLUGIN_NAME} --marketplace {REPO}\n"
        f"Update:  claude plugin marketplace update {PLUGIN_NAME} && claude plugin update {PLUGIN_NAME}@{PLUGIN_NAME}"
    )


if __name__ == "__main__":
    main()
