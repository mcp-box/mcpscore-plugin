# Security Policy

## Supported versions

Only the latest release of the plugin receives security fixes.

| Version | Supported |
|---------|-----------|
| latest  | ✅         |
| older   | ❌         |

## Reporting a vulnerability

Please **do not open a public issue** for security vulnerabilities.

Report them privately through
[GitHub Security Advisories](https://github.com/mcp-box/mcpscore-plugin/security/advisories/new).

We aim to acknowledge reports within 48 hours and will keep you informed of
the fix's progress. Credit is given in the release notes unless you prefer
to remain anonymous.

## Scope

The plugin is a set of instructions for a coding agent; the agent runs the
[mcpscore CLI](https://github.com/mcp-box/mcpscore) on your machine. In scope
here:

- Instructions in the skill that lead an agent to run a command, audit a
  server, call a server's tools, or edit code the user didn't ask for.
- Instructions that expose a credential: in a command line, a file, the chat,
  or a request to a server other than the one audited.
- Text from an audited server (its name, tool names, descriptions, error
  messages) that gets an agent following the skill to act on it as
  instructions.
- The marketplace and plugin manifests, and this repository's workflows.

Vulnerabilities in the mcpscore CLI itself, such as how it connects to or
parses a server, belong in the
[mcpscore security policy](https://github.com/mcp-box/mcpscore/security/policy).

Allow mcpscore in your agent's permissions only as one exact command, never
with a wildcard: the CLI can start any command (`--stdio`), read a token from
any file and call a server's tools, and a wildcard rule would let injected
text use all of that without a prompt.

Treat audit targets as untrusted. Auditing over stdio starts the server's
code on your machine, so audit only servers whose code you are willing to run.
