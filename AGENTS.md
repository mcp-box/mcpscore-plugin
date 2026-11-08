# mcpscore-plugin

The mcpscore plugin for coding agents: one Agent Skill (`audit`) that runs the
published mcpscore CLI, plus a manifest for each agent. Public repository.

## Layout

- `plugins/mcpscore/`: the plugin. `skills/audit/SKILL.md` is the product;
  everything else wraps it.
- `plugins/mcpscore/.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`: one
  `plugin.json` per agent. `name`, `version`, `description`, `license`,
  `repository` and `homepage` must match across all three (`make check`).
- `.claude-plugin/`, `.agents/plugins/`, `.cursor-plugin/` at the root: the
  marketplace each agent installs from.
- `plugins/mcpscore/evals/`: `claude plugin eval` cases.
- `scripts/check_plugin.py`: cross-file checks the agents' validators don't make.

## Rules

- **The plugin calls the published CLI** (`uvx mcpscore@latest`) and never
  vendors or imports engine code, so plugin and engine release independently.
- **The report fields the skill reads are a contract.** They are listed in
  `REPORT_FIELDS` in `scripts/check_plugin.py`. When the skill starts reading a
  new field, add it there; `make check` fails if the skill stops mentioning one,
  and the `Report contract` workflow fails if the published CLI stops emitting
  one. Refresh `tests/fixtures/report-deepwiki.json` with
  `uvx mcpscore@latest https://mcp.deepwiki.com/mcp --json` when the engine's
  report changes on purpose.
- **Nothing from the private `project/` repo goes here.**
- **Gate**: `make all` mirrors CI (ruff, pyright, pytest, `make check`,
  `claude plugin validate` pinned in the Makefile, zizmor pinned). The live
  contract test (`make test-live`) and the evals (`make eval`) are not in
  `make all`: one needs the network, the other runs paid Claude sessions.
- **Evals are a release gate, not a PR gate.** Run `make eval` before tagging a
  version and record the result in the PR. The eval sandbox may block the
  network, so graders accept an honest "the audit did not run" with no score.
- **Versioning**: installed copies are cached by version, so a change users
  should get needs a new version. Bump `version` in all three `plugin.json`
  files together and move `[Unreleased]` to a `## [X.Y.Z] - <date>` section
  with its compare link at the bottom.
- **Releasing** (Alex's): run `make eval` in the release PR, merge, then on a
  clean, synced `main`: `make release-dry-run`, then `make release`.
  `scripts/release.py` checks the plugin files, the CHANGELOG section and its
  link, that the tag is unused and that CI is green on HEAD, then creates the
  GitHub Release on tag `mcpscore--vX.Y.Z` (Claude Code's plugin tag format).
