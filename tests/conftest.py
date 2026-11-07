from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
COPIED = (".claude-plugin", ".agents", ".cursor-plugin", "plugins", "CHANGELOG.md")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A copy of the parts of this repository the checks read, safe to break."""
    for name in COPIED:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, tmp_path / name, ignore=shutil.ignore_patterns("results"))
        else:
            shutil.copy2(source, tmp_path / name)
    return tmp_path


@pytest.fixture
def report() -> dict[str, Any]:
    """A real `mcpscore --json` report (DeepWiki, mcpscore 1.31.1)."""
    return json.loads((FIXTURES / "report-deepwiki.json").read_text(encoding="utf-8"))


def edit_json(path: Path, **changes: Any) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(changes)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
