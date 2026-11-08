# Privacy

The mcpscore plugin is a set of instructions for your coding agent. It has no
server of its own and collects nothing.

When the agent follows it, it runs the open-source
[mcpscore CLI](https://github.com/mcp-box/mcpscore) on your machine:

- The CLI connects to the MCP server you ask it to audit, or starts the
  local server command you approve. It sends that server standard MCP requests
  and a few deliberately invalid ones (a foreign `Origin` header, malformed
  JSON) to check how the server handles them.
- When the server advertises an OAuth authorization server, the CLI also
  fetches that authorization server's public metadata, which can be on
  another host. That request carries no credential.
- The CLI sends nothing to mcpscore.dev and has no telemetry.
- `uvx` or `pipx` downloads the CLI from PyPI.
- Credentials you supply (`MCPSCORE_TOKEN`, `--token`, `--header`, `--oauth`)
  go only to the audited server, and an `--oauth` sign-in to its authorization
  server.
- The report goes to your agent as the CLI's output, on your machine. What your agent's provider receives is governed by that agent's own
  terms.

Questions: open an issue at https://github.com/mcp-box/mcpscore-plugin/issues.
