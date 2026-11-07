# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version is the plugin's, set in every `plugin.json`.

## [Unreleased]

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

### Security

- The skill tells the agent to treat every string in the report as data:
  server names, tool descriptions and error messages come from the audited
  server and are never followed as instructions.
