#!/usr/bin/env bash
# Seeds a small FastMCP notes server whose tools lack annotations and whose server lacks a title.
set -euo pipefail
cat > pyproject.toml <<'TOML'
[project]
name = "notes-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["mcp>=1.20"]
TOML
cat > server.py <<'PY'
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notes")
NOTES: dict[str, str] = {}


@mcp.tool()
def add_note(name: str, text: str) -> str:
    """Save a note under a name, replacing any note with that name."""
    NOTES[name] = text
    return f"saved {name}"


@mcp.tool()
def read_note(name: str) -> str:
    """Return the text of the note with this name."""
    return NOTES.get(name, "no such note")


@mcp.tool()
def delete_note(name: str) -> str:
    """Delete the note with this name."""
    NOTES.pop(name, None)
    return f"deleted {name}"


if __name__ == "__main__":
    mcp.run()
PY
