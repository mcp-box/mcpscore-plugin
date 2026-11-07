# Privacy

The mcpscore plugin is a set of instructions for your coding agent. It has no
server of its own and collects nothing.

When the agent follows it, it runs the open-source
[mcpscore CLI](https://github.com/mcp-box/mcpscore) on your machine:

- The CLI connects only to the MCP server you ask it to audit, or starts the
  local server command you approve. It sends that server standard MCP requests
  and a few deliberately invalid ones (a foreign `Origin` header, malformed
  JSON) to check how the server handles them.
- The CLI sends nothing to mcpscore.dev and has no telemetry.
- `uvx` or `pipx` downloads the CLI from PyPI.
- Credentials you supply (`--token`, `--header`, `--oauth`) go only to the
  audited server and its authorization server.
- The report is written to a temporary file on your machine and read by your
  agent. What your agent's provider receives is governed by that agent's own
  terms.

Questions: open an issue at https://github.com/mcp-box/mcpscore-plugin/issues.
