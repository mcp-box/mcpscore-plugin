#!/usr/bin/env bash
# Seeds an ordinary Python module with no MCP code.
set -euo pipefail
cat > utils.py <<'PY'
import re


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
PY
