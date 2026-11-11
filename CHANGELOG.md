# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version is the plugin's, set in every `plugin.json`.

## [Unreleased]

## [0.1.2] - 2026-11-11

### Security

- The README no longer recommends the permission rule
  `Bash(uvx mcpscore@latest:*)`. That rule also allowed `--stdio <any
  command>`, `--token-file <any file>` and `--smoke --call-all` without a
  prompt, so text from an audited server that steered the agent could run
  code or send a credential to another host. The README now recommends
  allowing one exact command for your own server. If you added the wildcard
  rule, replace it.
- The skill no longer refers to the wildcard rule. It keeps the audit command
  identical from run to run, so an exact rule keeps matching.
- `make check` fails when the skill or a README shows a wildcard permission
  rule for mcpscore.

## [0.1.1] - 2026-11-08

### Fixed

- The skill runs `mcpscore --json <target>`. With `--json` after a `--stdio`
  target, the flag went to the server instead of mcpscore, and the agent got
  no report.
- The README shows the same command order.

### Security

- The skill no longer passes `--token "$TOKEN"`, which the shell expands onto
  the command line where the process list shows it. It has the user export
  `MCPSCORE_TOKEN`, which mcpscore reads from the environment, and warns
  before an API-key `--header`, which has no environment form.
- The skill, the READMEs and `PRIVACY.md` say the CLI also fetches the public
  OAuth discovery documents the audited server points to, which can be on
  other hosts, instead of saying it talks only to the audited server.

## [0.1.0] - 2026-11-07

### Added

- The `audit` skill (`/mcpscore:audit <target>`): runs `mcpscore --json` on a
  server URL, a local server file or a stdio command, reports the score and the
  failed rules most severe first, fixes the user's own server code, and
  re-audits.
- Marketplace manifests for Claude Code, Codex and Cursor.
- An agent eval suite (`claude plugin eval`).
- `SECURITY.md`: private reporting through GitHub Security Advisories, and
  what is in scope for a plugin made of agent instructions.

### Fixed

- Findings from `readiness.results` now carry the report's own fix text. The
  skill fills each line of a finding only from its report field and leaves a
  missing one out, instead of writing its own.
- The skill states counts only from the report (`summary.failed`,
  `summary.by_severity`) and names the rules in any other group, instead of
  tallying them itself.

### Security

- The skill tells the agent to treat every string in the report as data:
  server names, tool descriptions and error messages come from the audited
  server and are never followed as instructions.

[Unreleased]: https://github.com/mcp-box/mcpscore-plugin/compare/mcpscore--v0.1.2...HEAD
[0.1.2]: https://github.com/mcp-box/mcpscore-plugin/compare/mcpscore--v0.1.1...mcpscore--v0.1.2
[0.1.1]: https://github.com/mcp-box/mcpscore-plugin/compare/mcpscore--v0.1.0...mcpscore--v0.1.1
[0.1.0]: https://github.com/mcp-box/mcpscore-plugin/releases/tag/mcpscore--v0.1.0
