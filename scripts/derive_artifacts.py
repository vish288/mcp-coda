#!/usr/bin/env python3
"""Derive gemini-extension.json and llms.txt from their sources.

Both files stay committed (Gemini CLI installs the extension straight from the
repo; llms.txt is fetched from main), but hand-editing two files that restate
data already in server.json / pyproject.toml / llms-full.txt lets them drift.
This script is the single source of truth:

  * gemini-extension.json <- server.json (name, version, required env vars)
    plus the package description from pyproject.toml. server.json's own
    description is the registry blurb and intentionally differs, so it is not
    used here.
  * llms.txt <- the leading prefix of llms-full.txt, up to the first section
    (## Setup Examples) that belongs only to the full document.

release.yml runs it after the version bump so the generated files carry the new
version; tests/unit/test_derived_artifacts.py fails if either committed file
diverges from what this produces.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER_JSON = ROOT / "server.json"
PYPROJECT = ROOT / "pyproject.toml"
LLMS_FULL = ROOT / "llms-full.txt"
GEMINI = ROOT / "gemini-extension.json"
LLMS = ROOT / "llms.txt"

# The first llms-full.txt section that llms.txt (the concise index) omits.
_LLMS_SPLIT = "\n## Setup Examples"


def _pyproject_description() -> str:
    match = re.search(r'^description = "(.*)"', PYPROJECT.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        msg = "pyproject.toml has no description line"
        raise SystemExit(msg)
    return match.group(1)


def derive_gemini() -> str:
    """gemini-extension.json content, byte-for-byte, from server.json + pyproject."""
    server = json.loads(SERVER_JSON.read_text(encoding="utf-8"))
    package = server["packages"][0]
    name = package["identifier"]
    settings = [
        {
            "name": env["name"],
            "description": env["description"],
            "required": env["isRequired"],
            "sensitive": env["isSecret"],
        }
        for env in package["environmentVariables"]
        if env["isRequired"]
    ]
    extension = {
        "name": name,
        "version": server["version"],
        "description": _pyproject_description(),
        "mcpServers": {name: {"command": "uvx", "args": [name]}},
        "settings": settings,
    }
    return json.dumps(extension, indent=2, ensure_ascii=False) + "\n"


def derive_llms_txt() -> str:
    """llms.txt content: the prefix of llms-full.txt before its full-only sections."""
    full = LLMS_FULL.read_text(encoding="utf-8")
    idx = full.find(_LLMS_SPLIT)
    if idx == -1:
        msg = (
            f"llms-full.txt has no {_LLMS_SPLIT.strip()!r} section — llms.txt is no "
            "longer a clean prefix of it; update scripts/derive_artifacts.py."
        )
        raise SystemExit(msg)
    return full[:idx]


def main() -> None:
    GEMINI.write_text(derive_gemini(), encoding="utf-8")
    LLMS.write_text(derive_llms_txt(), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
