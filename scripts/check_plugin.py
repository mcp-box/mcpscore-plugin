"""Consistency checks the plugin validators don't make.

`claude plugin validate` checks each manifest on its own. This checks that the
per-agent manifests agree with each other, that the skill and the eval cases
are well formed, and that the mcpscore report still carries every field the
skill tells the agent to read.

Usage: python scripts/check_plugin.py [--report REPORT.json]
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "mcpscore"
AGENT_MANIFEST_DIRS = (".claude-plugin", ".codex-plugin", ".cursor-plugin")
SHARED_MANIFEST_KEYS = ("name", "version", "description", "license", "repository", "homepage")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_DESCRIPTION_MAX = 1024
ICON_MIN_PX, ICON_MAX_PX = 512, 2048

# Report fields the audit skill reads. `[]` means "in at least one element of the list".
REPORT_FIELDS = (
    "score",
    "max_score",
    "partial",
    "partial_reason",
    "results[].rule_id",
    "results[].rule_name",
    "results[].severity",
    "results[].passed",
    "results[].message",
    "results[].suggested_fix",
    "results[].details.basis",
    "readiness.counted_in_main",
    "readiness.results[].rule_id",
    "readiness.results[].suggested_fix",
    "spec.negotiated_version",
    "spec.era",
    "skipped_rules",
)
MARKETPLACE_FILES = (
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    ".cursor-plugin/marketplace.json",
)
SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def plugin_dir(root: Path) -> Path:
    return root / "plugins" / PLUGIN_NAME


def frontmatter(path: Path) -> dict[str, Any]:
    """The YAML block between the leading `---` lines of a Markdown file."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        raise ValueError(f"{path}: no YAML frontmatter")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter is not a mapping")
    return data


def png_size(path: Path) -> tuple[int, int] | None:
    """Width and height from a PNG's IHDR chunk, or None when the file isn't a PNG."""
    head = path.read_bytes()[:24]
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def check_manifests(root: Path) -> list[str]:
    errors: list[str] = []
    manifests: dict[str, dict[str, Any]] = {}
    for agent_dir in AGENT_MANIFEST_DIRS:
        path = plugin_dir(root) / agent_dir / "plugin.json"
        if not path.is_file():
            errors.append(f"missing {path.relative_to(root)}")
            continue
        manifests[agent_dir] = load_json(path)

    if not manifests:
        return errors
    reference_dir, reference = next(iter(manifests.items()))
    for agent_dir, manifest in manifests.items():
        for key in SHARED_MANIFEST_KEYS:
            if manifest.get(key) != reference.get(key):
                errors.append(f"{agent_dir}/plugin.json {key!r} differs from {reference_dir}/plugin.json")
    if reference.get("name") != PLUGIN_NAME:
        errors.append(f"plugin name is {reference.get('name')!r}, expected {PLUGIN_NAME!r}")
    if not SEMVER.match(str(reference.get("version", ""))):
        errors.append(f"plugin version {reference.get('version')!r} is not MAJOR.MINOR.PATCH")

    errors.extend(check_icons(root, manifests))
    return errors


def check_icons(root: Path, manifests: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    icons = {plugin_dir(root) / agent_dir / "icon.png" for agent_dir in manifests}
    codex = manifests.get(".codex-plugin", {}).get("interface", {})
    cursor = manifests.get(".cursor-plugin", {})
    icons.update(plugin_dir(root) / str(ref) for ref in (codex.get("logo"), codex.get("composerIcon")) if ref)
    if cursor.get("logo"):
        icons.add(plugin_dir(root) / str(cursor["logo"]))
    for icon in sorted(icons):
        rel = icon.relative_to(root)
        if not icon.is_file():
            errors.append(f"missing icon {rel}")
            continue
        size = png_size(icon)
        if size is None:
            errors.append(f"{rel} is not a PNG")
        elif size[0] != size[1] or not ICON_MIN_PX <= size[0] <= ICON_MAX_PX:
            errors.append(f"{rel} is {size[0]}x{size[1]}; expected square, {ICON_MIN_PX} to {ICON_MAX_PX} px")
    return errors


def marketplace_sources(root: Path) -> dict[str, tuple[str, str | None]]:
    """Each marketplace file's source path and description for the plugin."""
    found: dict[str, tuple[str, str | None]] = {}
    files: dict[str, Callable[[dict[str, Any]], Any]] = {
        ".claude-plugin/marketplace.json": lambda entry: entry["source"],
        ".agents/plugins/marketplace.json": lambda entry: entry["source"]["path"],
        ".cursor-plugin/marketplace.json": lambda entry: entry["source"],
    }
    for rel, source_of in files.items():
        path = root / rel
        if not path.is_file():
            continue
        for entry in load_json(path).get("plugins", []):
            if entry.get("name") == PLUGIN_NAME:
                found[rel] = (str(source_of(entry)), entry.get("description"))
    return found


def check_marketplaces(root: Path) -> list[str]:
    errors: list[str] = []
    claude_manifest = plugin_dir(root) / ".claude-plugin" / "plugin.json"
    description = load_json(claude_manifest).get("description") if claude_manifest.is_file() else None
    found = marketplace_sources(root)
    for rel in MARKETPLACE_FILES:
        if rel not in found:
            errors.append(f"{rel} does not list the {PLUGIN_NAME!r} plugin")
            continue
        source, listed_description = found[rel]
        if (root / source).resolve() != plugin_dir(root).resolve():
            errors.append(f"{rel} source {source!r} is not plugins/{PLUGIN_NAME}")
        if listed_description is not None and listed_description != description:
            errors.append(f"{rel} description differs from plugin.json")
    return errors


def check_skills(root: Path) -> list[str]:
    errors: list[str] = []
    skills_root = plugin_dir(root) / "skills"
    skill_dirs = sorted(path for path in skills_root.iterdir() if path.is_dir()) if skills_root.is_dir() else []
    if not skill_dirs:
        return [f"no skills under {skills_root.relative_to(root)}"]
    for skill in skill_dirs:
        rel = skill.relative_to(root)
        skill_file = skill / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{rel} has no SKILL.md")
            continue
        try:
            meta = frontmatter(skill_file)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        name = meta.get("name")
        if name != skill.name:
            errors.append(f"{rel}/SKILL.md name {name!r} does not match its folder")
        if not isinstance(name, str) or not SKILL_NAME.match(name) or len(name) > 64:
            errors.append(f"{rel}/SKILL.md name {name!r} must be lowercase words joined by hyphens, at most 64")
        description = meta.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{rel}/SKILL.md has no description")
        elif len(description) > SKILL_DESCRIPTION_MAX:
            errors.append(f"{rel}/SKILL.md description is {len(description)} characters; max {SKILL_DESCRIPTION_MAX}")
    return errors


def check_evals(root: Path) -> list[str]:
    errors: list[str] = []
    evals_root = plugin_dir(root) / "evals"
    cases = sorted(path for path in evals_root.iterdir() if path.is_dir()) if evals_root.is_dir() else []
    if not cases:
        return [f"no eval cases under {evals_root.relative_to(root)}"]
    for case in cases:
        rel = case.relative_to(root)
        case_file = case / "case.yaml"
        if not case_file.is_file():
            errors.append(f"{rel} has no case.yaml")
            continue
        spec = yaml.safe_load(case_file.read_text(encoding="utf-8")) or {}
        if spec.get("name") != case.name:
            errors.append(f"{rel}/case.yaml name {spec.get('name')!r} does not match its folder")
        if not (case / "prompt.md").is_file():
            errors.append(f"{rel} has no prompt.md")
        graders = sorted((case / "graders").glob("*.md"))
        if not graders:
            errors.append(f"{rel} has no graders")
        for grader in graders:
            try:
                if "type" not in frontmatter(grader):
                    errors.append(f"{grader.relative_to(root)} has no grader type")
            except ValueError as exc:
                errors.append(str(exc))
        scaffold = (spec.get("context") or {}).get("scaffold_script")
        if scaffold:
            script = case / scaffold
            if not script.is_file():
                errors.append(f"{rel} names scaffold {scaffold!r}, which does not exist")
            elif not script.stat().st_mode & 0o111:
                errors.append(f"{script.relative_to(root)} is not executable")
    return errors


def check_changelog(root: Path) -> list[str]:
    path = root / "CHANGELOG.md"
    if not path.is_file():
        return ["missing CHANGELOG.md"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if "## [Unreleased]" not in text:
        errors.append("CHANGELOG.md has no [Unreleased] section")
    released = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
    manifest = plugin_dir(root) / ".claude-plugin" / "plugin.json"
    version = str(load_json(manifest).get("version", "")) if manifest.is_file() else ""
    if released and SEMVER.match(version) and version_key(version) < max(version_key(v) for v in released):
        errors.append(f"plugin.json version {version} is older than CHANGELOG.md's latest release")
    return errors


def values_at(data: Any, path: str) -> list[Any]:
    """Every value at `path`, where `name[]` steps into each element of a list."""
    values = [data]
    for part in path.split("."):
        each = part.endswith("[]")
        key = part.removesuffix("[]")
        next_values: list[Any] = []
        for value in values:
            if isinstance(value, dict) and key in value:
                child = value[key]
                if each:
                    if isinstance(child, list):
                        next_values.extend(child)
                else:
                    next_values.append(child)
        values = next_values
    return values


def check_report(report: Any, fields: tuple[str, ...] = REPORT_FIELDS) -> list[str]:
    """Problems with a `mcpscore --json` report, judged by what the skill reads from it."""
    errors = [f"report has no {field}" for field in fields if not values_at(report, field)]
    if not isinstance(report, dict):
        return errors
    if report.get("schema_version") != 1:
        errors.append(f"report schema_version is {report.get('schema_version')!r}; the skill reads version 1")
    readiness = report.get("readiness")
    readiness_results = readiness.get("results", []) if isinstance(readiness, dict) else []
    results = [r for r in [*report.get("results", []), *readiness_results] if isinstance(r, dict)]
    for result in results:
        if result.get("severity") not in SEVERITIES:
            errors.append(f"{result.get('rule_id')}: unknown severity {result.get('severity')!r}")
        if result.get("passed") is False and not result.get("suggested_fix"):
            errors.append(f"{result.get('rule_id')}: failed rule has no suggested_fix")
    score, max_score = report.get("score"), report.get("max_score")
    if isinstance(score, int) and isinstance(max_score, int) and not 0 <= score <= max_score:
        errors.append(f"score {score} is outside 0..{max_score}")
    return errors


def check_skill_names_report_fields(root: Path, fields: tuple[str, ...] = REPORT_FIELDS) -> list[str]:
    """Every report field in the contract is one the skill actually tells the agent about."""
    skill = (plugin_dir(root) / "skills" / "audit" / "SKILL.md").read_text(encoding="utf-8")
    leaves = {field.rsplit(".", 1)[-1].removesuffix("[]") for field in fields}
    missing = sorted(leaf for leaf in leaves if leaf not in skill)
    return [f"skills/audit/SKILL.md never mentions report field {leaf!r}" for leaf in missing]


def check_repo(root: Path = ROOT) -> list[str]:
    return [
        *check_manifests(root),
        *check_marketplaces(root),
        *check_skills(root),
        *check_evals(root),
        *check_changelog(root),
        *check_skill_names_report_fields(root),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--report", type=Path, help="also check a `mcpscore --json` report against the skill")
    args = parser.parse_args(argv)
    errors = check_repo()
    if args.report:
        errors += [f"{args.report}: {error}" for error in check_report(load_json(args.report))]
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("plugin checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
