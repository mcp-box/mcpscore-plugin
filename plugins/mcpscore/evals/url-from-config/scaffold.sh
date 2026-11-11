#!/usr/bin/env bash
# Seeds an app with no MCP server of its own: the only MCP endpoint is a vendor URL in a client config.
set -euo pipefail
cat > README.md <<'MD'
# Helpdesk dashboard

A small web dashboard for the support team. The assistant panel reads product
docs through our docs vendor's MCP server, configured in `.mcp.json`.

    npm install
    npm run dev
MD
cat > .mcp.json <<'JSON'
{
  "mcpServers": {
    "vendor-docs": {
      "type": "http",
      "url": "https://mcp.docs-vendor.example/mcp"
    }
  }
}
JSON
cat > package.json <<'JSON'
{
  "name": "helpdesk-dashboard",
  "version": "0.3.0",
  "private": true,
  "scripts": { "dev": "vite" },
  "dependencies": { "react": "^19.0.0", "vite": "^7.0.0" }
}
JSON
