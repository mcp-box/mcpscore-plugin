# mcpscore

Audit the MCP server you're building with [mcpscore](https://mcpscore.dev),
the Lighthouse for MCP. Ask your agent to "audit my MCP server" or run
`/mcpscore:audit <target>`. The agent runs the mcpscore CLI on a server URL, a
local server file or a stdio command, reports the score with every failed rule
and its spec citation, fixes what it can in your own server code, and
re-audits to show the score before and after.

Requires [uv](https://docs.astral.sh/uv/) (`uvx mcpscore`) or pipx on your
`PATH`. Nothing is sent to mcpscore.dev: the CLI talks only to the server you
audit.

Install in Claude Code:

```text
/plugin install mcpscore --marketplace mcp-box/mcpscore-plugin
```

Codex, Cursor, usage and privacy: https://github.com/mcp-box/mcpscore-plugin
