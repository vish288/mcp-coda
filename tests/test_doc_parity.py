"""Keep the docs honest about the code.

Tool counts, per-category inventory tables, tool names and version strings are
duplicated across README.md, AGENTS.md, llms.txt, llms-full.txt, server.json and
gemini-extension.json. They have silently drifted before. Every number below is
re-derived from the source tree, never hardcoded.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVERS = ROOT / "src" / "mcp_coda" / "servers"

# Modules that are not tool domains.
_NON_TOOL_MODULES = {"__init__", "_helpers", "resources", "prompts"}


def _tools_by_module() -> dict[str, list[str]]:
    """Map domain module name -> registered coda_* tool names, from the source."""
    found: dict[str, list[str]] = {}
    for path in sorted(SERVERS.glob("*.py")):
        if path.stem in _NON_TOOL_MODULES:
            continue
        names = re.findall(r"^async def (coda_\w+)", path.read_text(encoding="utf-8"), re.MULTILINE)
        if names:
            found[path.stem] = names
    return found


TOOLS_BY_MODULE = _tools_by_module()
ALL_TOOLS = {name for names in TOOLS_BY_MODULE.values() for name in names}
TOOL_TOTAL = len(ALL_TOOLS)


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


# Docs link to sibling MCP servers and quote *their* inventories; those numbers
# describe other repos and must not be checked against this one.
_SIBLING_REPOS = ("mcp-gitlab", "mcp-atlassian", "mcp-argocd")


def _read_self(name: str) -> str:
    """File contents with lines describing sibling projects removed."""
    return "\n".join(
        line
        for line in _read(name).splitlines()
        if not any(repo in line for repo in _SIBLING_REPOS)
    )


def test_source_scan_found_tools() -> None:
    """Guard the guard — an empty scan would make every assertion below vacuous."""
    assert TOOL_TOTAL > 0
    assert len(ALL_TOOLS) == sum(len(v) for v in TOOLS_BY_MODULE.values()), "duplicate tool names"


@pytest.mark.parametrize(
    ("filename", "pattern"),
    [
        ("README.md", r"## Tools \((\d+)\)"),
        ("README.md", r"\*\*(\d+) tools\*\*"),
        ("AGENTS.md", r"## Tool inventory \((\d+)\)"),
        ("AGENTS.md", r"(\d+) tools, \d+ resources"),
        ("llms.txt", r"(\d+) tools, \d+ resources"),
        ("llms-full.txt", r"## Tools \((\d+)\)"),
    ],
)
def test_stated_tool_total_matches_code(filename: str, pattern: str) -> None:
    matches = re.findall(pattern, _read_self(filename))
    assert matches, f"{filename}: no tool total matching {pattern!r} — doc restructured?"
    for stated in matches:
        assert int(stated) == TOOL_TOTAL, f"{filename} claims {stated} tools, code has {TOOL_TOTAL}"


@pytest.mark.parametrize("filename", ["README.md", "AGENTS.md"])
def test_inventory_table_counts_match_code(filename: str) -> None:
    """Each `| Category | N |` row must match that module's real tool count."""
    seen: dict[str, int] = {}
    for line in _read(filename).splitlines():
        row = re.match(r"\|\s*\*{0,2}(\w+)\*{0,2}\s*\|\s*(\d+)\s*\|", line)
        if row and row.group(1).lower() in TOOLS_BY_MODULE:
            seen[row.group(1).lower()] = int(row.group(2))

    assert seen, f"{filename}: inventory table not found — doc restructured?"
    assert set(seen) == set(TOOLS_BY_MODULE), (
        f"{filename} covers {sorted(seen)}, code has {sorted(TOOLS_BY_MODULE)}"
    )
    for module, stated in seen.items():
        actual = len(TOOLS_BY_MODULE[module])
        assert stated == actual, f"{filename}: {module} says {stated}, code has {actual}"


def test_llms_full_section_counts_match_code() -> None:
    """`### Rows (7)` headings must match the real per-module counts."""
    seen = {
        m.group(1).lower(): int(m.group(2))
        for m in re.finditer(r"^### (\w+) \((\d+)\)", _read("llms-full.txt"), re.MULTILINE)
        if m.group(1).lower() in TOOLS_BY_MODULE
    }
    assert set(seen) == set(TOOLS_BY_MODULE)
    for module, stated in seen.items():
        actual = len(TOOLS_BY_MODULE[module])
        assert stated == actual, f"llms-full.txt: {module} says {stated}, code has {actual}"


@pytest.mark.parametrize("filename", ["README.md", "AGENTS.md", "llms-full.txt"])
def test_documented_tool_names_exist(filename: str) -> None:
    """No doc may name a coda_* tool that is not registered."""
    referenced = set(re.findall(r"`(coda_\w+)`", _read(filename)))
    assert not referenced - ALL_TOOLS, (
        f"{filename} references unregistered tools: {sorted(referenced - ALL_TOOLS)}"
    )


def test_readme_documents_every_tool() -> None:
    """The README tool tables are the public inventory — none may be missing."""
    documented = set(re.findall(r"`(coda_\w+)`", _read("README.md")))
    assert not ALL_TOOLS - documented, f"README omits: {sorted(ALL_TOOLS - documented)}"


def test_resource_and_prompt_counts_match_code() -> None:
    resources = len(re.findall(r"@mcp\.resource\(", (SERVERS / "resources.py").read_text()))
    prompts = len(re.findall(r"@mcp\.prompt\(", (SERVERS / "prompts.py").read_text()))
    for filename in ("README.md", "AGENTS.md", "llms.txt", "llms-full.txt"):
        text = _read_self(filename)
        for stated in re.findall(r"(\d+) resources", text):
            assert int(stated) == resources, f"{filename}: {stated} resources, code has {resources}"
        for stated in re.findall(r"(\d+) prompts", text):
            assert int(stated) == prompts, f"{filename}: {stated} prompts, code has {prompts}"


def test_version_strings_agree_with_pyproject() -> None:
    version = re.search(r'^version = "([^"]+)"', _read("pyproject.toml"), re.MULTILINE)
    assert version, "pyproject.toml has no version"
    expected = version.group(1)

    server = json.loads(_read("server.json"))
    assert server["version"] == expected
    assert server["packages"][0]["version"] == expected
    assert json.loads(_read("gemini-extension.json"))["version"] == expected

    for filename in ("llms.txt", "llms-full.txt"):
        stated = re.search(r"^- \*\*Version\*\*: (.+)$", _read(filename), re.MULTILINE)
        assert stated, f"{filename} has no **Version** line"
        assert stated.group(1).strip() == expected, f"{filename}: {stated.group(1)} != {expected}"


def test_no_reference_to_deleted_models_package() -> None:
    """The models/ package was removed — nothing may still point at it."""
    assert not (ROOT / "src" / "mcp_coda" / "models").exists()
    offenders = [
        f"{path.relative_to(ROOT)}:{i}"
        for path in [ROOT / n for n in ("README.md", "AGENTS.md", "llms.txt", "llms-full.txt")]
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"mcp_coda[./]models|models/", line)
    ]
    assert not offenders, f"stale references to the deleted models package: {offenders}"
