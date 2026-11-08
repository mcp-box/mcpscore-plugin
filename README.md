# mcpscore for coding agents

[![CI](https://github.com/mcp-box/mcpscore-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/mcp-box/mcpscore-plugin/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/mcp-box/mcpscore-plugin.svg)](LICENSE)

Audit the MCP server you're building without leaving Claude Code, Codex or
Cursor. Ask "audit my MCP server" and the agent runs
[mcpscore](https://mcpscore.dev), explains the score and each failed rule with
its spec citation, fixes what it can in your own server code, and re-audits to
show the score before and after.

## Install

| Agent                             | Install                                                                                              |
|-----------------------------------|------------------------------------------------------------------------------------------------------|
| Claude Code                       | `/plugin install mcpscore --marketplace mcp-box/mcpscore-plugin`                                     |
| Codex                             | `codex plugin marketplace add mcp-box/mcpscore-plugin`, then `codex plugin add mcpscore@mcpscore`    |
| Cursor                            | copy `plugins/mcpscore` to `~/.cursor/plugins/local/mcpscore`, then run **Developer: Reload Window** |
| Any agent that reads Agent Skills | copy `plugins/mcpscore/skills/audit` to your agent's skills folder                                   |

The skill runs the mcpscore CLI with [uv](https://docs.astral.sh/uv/)
(`uvx mcpscore`), so uv must be on your `PATH`. pipx works too.

To let the agent run audits without asking each time, allow the command. In
Claude Code, add this to `permissions.allow` in your settings:

```json
"Bash(uvx mcpscore@latest:*)"
```

## Use

```text
Audit my MCP server at https://example.com/mcp
Check the MCP server in this folder and fix what you safely can
/mcpscore:audit --stdio uv run server.py
```

The skill:

1. Runs `mcpscore --json <target>` on a server URL, a local server file, or a
   server command (`--stdio`). It audits only a server you named, and asks
   before starting a local server it found in your workspace.
2. Reports the score in points (`153/171 (89%)`) and the failed rules, most
   severe first, each with what was observed, the fix, and the requirement it
   comes from.
3. With your go-ahead, fixes your own server code, keeping tool annotations
   and descriptions true to what the code does.
4. Re-audits and shows the score before and after.

It never calls your server's tools unless you ask (`--smoke`), and it never
writes a credential into a file. For a server behind a bearer token, export
`MCPSCORE_TOKEN` before you start the agent: mcpscore reads it from the
environment, so the token stays off the command line.

## Privacy

The plugin sends nothing to mcpscore.dev. The CLI talks to the server you
audit, and fetches the public OAuth discovery documents that server points to,
which can be on other hosts. See [PRIVACY.md](PRIVACY.md).

## Security

Report vulnerabilities privately; see [SECURITY.md](SECURITY.md).

## Development

```bash
make install   # uv sync --all-groups
make all       # what CI runs: lint, types, tests, plugin validation, workflow audit
make eval      # the agent eval suite: runs real Claude sessions on your account
```

`plugins/mcpscore/` is the plugin. The repository root holds the marketplace
manifests for each agent (`.claude-plugin/`, `.agents/plugins/`,
`.cursor-plugin/`). `scripts/check_plugin.py` keeps those manifests, the skill,
and the mcpscore report fields the skill reads consistent with each other.

## License

MIT. See [LICENSE](LICENSE).
