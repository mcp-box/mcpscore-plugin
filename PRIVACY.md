# Privacy

The mcpscore plugin is a set of instructions for your coding agent. It has no
server of its own and collects nothing.

When the agent follows it, it runs the open-source
[mcpscore CLI](https://github.com/mcp-box/mcpscore) on your machine:

- The CLI connects to the MCP server you ask it to audit, or starts the
  local server command you approve. It sends that server standard MCP requests
  and a few deliberately invalid ones (a foreign `Origin` header, malformed
  JSON) to check how the server handles them.
- When the server points to OAuth discovery documents, the CLI also fetches
  them: the protected-resource metadata named in its `WWW-Authenticate`
  challenge or at its well-known location, and the metadata of the
  authorization server that document lists. They can be on other hosts. These
  requests carry no credential, and the CLI doesn't send them to loopback or
  private addresses unless the audited server is on one.
- The CLI sends nothing to mcpscore.dev and has no telemetry.
- `uvx` or `pipx` downloads the CLI from PyPI.
- Credentials you supply (`MCPSCORE_TOKEN`, `--token`, `--header`, `--oauth`)
  go only to the audited server, and an `--oauth` sign-in to its authorization
  server.
- The report goes to your agent as the CLI's output, on your machine. What your agent's provider receives is governed by that agent's own
  terms.

Questions: open an issue at https://github.com/mcp-box/mcpscore-plugin/issues.
