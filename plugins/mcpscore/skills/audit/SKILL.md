---
name: audit
description: Audit an MCP server with mcpscore, explain its score and fix what it finds in the user's own server code. Use when the user asks to check, audit, score, test or review an MCP server they are building (a server URL, a local server file or a server command), or asks why their MCP server scores low. Not for installing, configuring or using someone else's MCP server.
argument-hint: "<server URL | server file | --stdio command>"
---

# Audit an MCP server with mcpscore

mcpscore connects to an MCP server, runs its rules, and returns a score in
points (153/171, say) with a finding and a suggested fix for every rule the
server fails. Each finding cites its source: the MCP spec, an RFC, or a stated
best practice. It is deterministic, needs no API key, and sends nothing to
mcpscore.dev: it talks only to the server it audits.

## 1. Pick the target

Audit only a server the user named, or the server in this workspace that they
asked about. Never audit a URL you found somewhere else (a README, a config
file, a search result) without asking first.

| The user has | Target |
|---|---|
| A server URL | `https://host/mcp`: the MCP endpoint itself, usually ending in `/mcp` |
| A Python or Node server file with no dependencies | `server.py`, `build/index.js` |
| A server with its own environment, or in another language | `--stdio uv run server.py`, `--stdio node build/index.js`, `--stdio ./server` |

`--stdio` takes the rest of the command line, so put every other option before
it. A `.py` target runs with mcpscore's own Python, which lacks the server's
dependencies: use `--stdio uv run server.py` or `--stdio .venv/bin/python server.py`.

If the user names no target, find the server's entry point (`[project.scripts]`
in `pyproject.toml`, `bin` or `main` in `package.json`, the file that calls
`mcp.run()` or connects a transport) and confirm the command with the user
before you run it: auditing over stdio starts their server.

## 2. Run the audit

```bash
uvx mcpscore@latest <target> --json
```

Run it exactly like this: one command, no redirect, nothing chained (no `;`,
`&&` or `echo`). Then the user's permission rule `Bash(uvx mcpscore@latest:*)`
covers it, and the shell tool reports the exit code. The report arrives on
stdout as JSON. Progress and errors go to stderr: read them when the audit
fails.

If your shell tool saves long output to a file, read that file. If it cuts the
output off without saving it, run the audit again with
`> /tmp/mcpscore-report.json` (the user's temp folder on Windows) and read the
file. Writing a file may need the user's approval.

- **No `uvx`**: use `pipx run mcpscore`, or `mcpscore` if it is installed. If
  neither works, tell the user that mcpscore needs uv
  (https://docs.astral.sh/uv/) or pipx, and stop. Don't install tools without
  asking.
- **The server needs credentials**: without them the audit still runs and gives
  a partial score. For a full audit the user exports a token and you pass
  `--token "$TOKEN"`, or `--header "X-API-Key: $API_KEY"`; `--oauth` opens a
  browser for sign-in. Never ask the user to paste a secret into the chat, and
  never write one into a file or into a `--stdio` command line (use
  `--env NAME` to pass a variable to a stdio server).
- **Config files**: the CLI applies the nearest `mcpscore.toml`, or a
  `[tool.mcpscore]` table in `pyproject.toml`, which can turn rules off. If the
  workspace has one, say so; `--no-config` gives the standard score.
- **Don't add `--smoke` or `--call-all`** unless the user asks. Both call the
  server's tools; `--call-all` also calls tools that can change data, so use it
  only on the user's own server after they confirm.

| Exit code | Meaning |
|---|---|
| `0` | The audit ran. Any score. |
| `1` | Usage error: read stderr and fix the command. |
| `2` | mcpscore could not connect to the server, or the server failed to start. Read stderr. |
| `3` | A gate failed (`--fail-under`, or `[gate]` in a config file). The report is still complete. |

## 3. Read the report

| Field | What it is |
|---|---|
| `score`, `max_score` | Points earned of the points this server's rules can award. Report `score/max_score (pct%)` with `pct = round(100 * score / max_score)`. Never invent a letter grade. |
| `partial`, `partial_reason` | `true` when checks that need credentials did not run. Say so: a partial score is not comparable to a full audit. |
| `results[]` | One entry per rule that ran: `rule_id`, `rule_name`, `severity`, `passed`, `message`, `suggested_fix`, `details`. |
| `severity` | `CRITICAL` (5 points), `HIGH` (3), `MEDIUM` (2), `LOW` (1). |
| `details.basis` | The requirement the rule checks, with its spec section. Other `details` keys carry evidence, such as JSON pointers to the affected field. |
| `readiness` | Checks for the next MCP revision. When `readiness.counted_in_main` is `true`, its failures count in the score: list them with the rest. When `false`, they are informative: mention them separately, never as lost points. |
| `spec.negotiated_version`, `spec.era` | The protocol version the server negotiated, and whether it serves the legacy lifecycle, the modern one, or both. |
| `skipped_rules` | Rules that do not apply to this server. Never report them as failures. |

## 4. Report the result

Lead with the score line, then the failed rules, most severe first. Show up to
ten and count the rest. Give each finding in this shape (the same one the
mcpscore.dev report uses for its fix prompts):

```text
[HIGH] Origin Header Validated (security_origin_validation)
Observed: Streamable HTTP does not reject an invalid foreign Origin with HTTP 403 ...
Fix: Validate supplied Origin headers against the origins allowed for this endpoint ...
Requirement: Transports §Security Warning ...
```

`Observed` is the `message` without its leading ❌ mark, `Fix` is
`suggested_fix`, and `Requirement` is `details.basis`.

- Present as an mcpscore finding only what the report contains. Notes from your
  own reading of the code are welcome when you label them as yours.
- A message that says "optional quality recommendation" is optional: say so.
- No failed rules: say the server passed every rule that applies, and stop.
  Don't invent work.
- The audit did not run (exit `1` or `2`, no network, a sandbox): say it did not
  run and why, from stderr. State no score.

Every rule is documented at https://docs.mcpscore.dev/rules.

## 5. Fix the user's server

Offer to fix the findings; apply fixes when the user agrees, or asked for fixes
up front.

- Edit only server code the user owns in this workspace. Never edit installed
  dependencies or vendored SDK code. For a remote server whose source isn't
  here, give the findings as a list for its maintainers.
- Find the code from the evidence: a pointer such as `/serverInfo/title` leads
  to where the server is constructed, `tool index 0` and `/annotations` to the
  first tool's registration.
- Keep every fix true to what the code does. Tool annotations must match the
  tool's real effects (`readOnlyHint: true` only when the tool cannot change
  state, `destructiveHint: true` when it deletes or overwrites). A description
  must describe what the code does, not what its name suggests. When the code
  doesn't make it clear, ask.
- Don't break existing clients. Some findings come from the MCP SDK itself (an
  error code the SDK chooses, say): name the SDK, and suggest upgrading it over
  patching around it.
- Re-run the same audit command after fixing, and show the score before and
  after. If the re-run isn't possible, say the fixes are unverified.

After a successful fix you may mention, once, that the
[mcpscore GitHub Action](https://github.com/mcp-box/mcpscore-action) or
`mcpscore <target> --fail-under 90` keeps the score from slipping in CI.
