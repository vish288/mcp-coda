"""MCP_TOOLSETS: coarse tool groups (workbench-backlog#160).

``MCP_TOOLSETS`` (or ``--toolsets``) selects named groups of the raw domain tags the tools
already carry, switching ``tools/list`` to an allowlist of just those tools so a client with
a tool budget sees fewer. The ``core`` tags (account) are unioned into every selection.
Resources and prompts stay listed regardless, and ``MCP_READ_ONLY`` still applies after the
selection and only ever removes tools. Unset or ``all`` lists every tool; an unknown group
exits 2 with the valid list.

Each case boots a real ``Client(mcp)`` so the env → lifespan → ``_apply_toolsets`` wiring is
exercised, and restores the module-level server's visibility transforms afterwards.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner
from fastmcp import Client

from mcp_coda import main
from mcp_coda.servers import CORE_TAGS, TOOLSET_GROUPS, UnknownToolsetError, mcp, parse_toolsets

_FRAME_TAGS = {"coda", "read", "write"}

# Per group: (tools listed, tools listed under read-only). Measured against the server.
_EXPECTED = {
    "content": (17, 10),
    "data": (19, 13),
    "admin": (17, 10),
    "analytics": (10, 10),
}
_CORE = (3, 3)
_ALL_TOOLS = 54
_ALL_TOOLS_RO = 34


async def _boot(
    monkeypatch, toolsets: str | None, *, read_only: bool = False
) -> tuple[set[str], int, int]:
    monkeypatch.setenv("CODA_API_TOKEN", "t")
    monkeypatch.delenv("CODA_READ_ONLY", raising=False)
    monkeypatch.delenv("MCP_READ_ONLY", raising=False)
    monkeypatch.delenv("MCP_TOOLSETS", raising=False)
    if toolsets is not None:
        monkeypatch.setenv("MCP_TOOLSETS", toolsets)
    if read_only:
        monkeypatch.setenv("MCP_READ_ONLY", "true")
    tx = len(mcp._transforms)
    instructions = mcp.instructions
    try:
        async with Client(mcp) as client:
            tools = {t.name for t in await client.list_tools()}
            res = len(await client.list_resources())
            prm = len(await client.list_prompts())
        return tools, res, prm
    finally:
        del mcp._transforms[tx:]
        mcp.instructions = instructions


@pytest.fixture(scope="module")
async def baseline_counts() -> tuple[int, int]:
    """Resource and prompt counts with no toolset selected — the invariant every case holds."""
    env = {"CODA_API_TOKEN": "t", "MCP_READ_ONLY": "", "MCP_TOOLSETS": ""}
    with patch.dict("os.environ", env, clear=False):
        async with Client(mcp) as client:
            return len(await client.list_resources()), len(await client.list_prompts())


# ── the group map ──────────────────────────────────────────────────────


async def test_every_domain_tag_belongs_to_exactly_one_group():
    all_tools = await mcp._list_tools()
    domain_tags = {t for tool in all_tools for t in (set(tool.tags) - _FRAME_TAGS)}
    for tool in all_tools:
        assert len(set(tool.tags) - _FRAME_TAGS) == 1, tool.name
    group_tags = [tag for tags in TOOLSET_GROUPS.values() for tag in tags]
    assert len(group_tags) == len(set(group_tags)), "a tag appears in two groups"
    assert not (set(group_tags) & CORE_TAGS), "core overlaps a selectable group"
    assert set(group_tags) | CORE_TAGS == domain_tags


# ── selection ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("group", sorted(_EXPECTED))
async def test_group_lists_expected_tools(monkeypatch, baseline_counts, group):
    tools, res, prm = await _boot(monkeypatch, group)
    assert len(tools) == _EXPECTED[group][0]
    assert (res, prm) == baseline_counts


async def test_core_alone_lists_core_tools(monkeypatch):
    tools, _, _ = await _boot(monkeypatch, "core")
    assert len(tools) == _CORE[0]


@pytest.mark.parametrize("raw", [None, "", "  ", "all", "content,all"])
async def test_unset_or_all_lists_everything(monkeypatch, baseline_counts, raw):
    tools, res, prm = await _boot(monkeypatch, raw)
    assert len(tools) == _ALL_TOOLS
    assert (res, prm) == baseline_counts


async def test_core_is_unioned_into_every_selection(monkeypatch):
    core_tools, _, _ = await _boot(monkeypatch, "core")
    content_tools, _, _ = await _boot(monkeypatch, "content")
    assert core_tools < content_tools


# ── read-only still wins after the allowlist ──────────────────────────────


@pytest.mark.parametrize("group", sorted(_EXPECTED))
async def test_group_plus_read_only_drops_writes(monkeypatch, group):
    all_tools = await mcp._list_tools()
    write_names = {t.name for t in all_tools if "write" in t.tags}
    tools, _, _ = await _boot(monkeypatch, group, read_only=True)
    assert len(tools) == _EXPECTED[group][1]
    assert not (tools & write_names)


async def test_all_read_only_count(monkeypatch):
    tools, _, _ = await _boot(monkeypatch, None, read_only=True)
    assert len(tools) == _ALL_TOOLS_RO


# ── parsing / validation ──────────────────────────────────────────────────


@pytest.mark.parametrize("raw", [None, "", "   ", "all", "ALL", " content , all "])
def test_parse_none_means_no_filter(raw):
    assert parse_toolsets(raw) is None


def test_parse_trims_lowercases_and_unions_core():
    assert parse_toolsets(" Content ") == set(TOOLSET_GROUPS["content"]) | set(CORE_TAGS)


def test_parse_core_alone_is_just_core():
    assert parse_toolsets("core") == set(CORE_TAGS)


def test_parse_unknown_raises_with_valid_list():
    with pytest.raises(UnknownToolsetError) as exc:
        parse_toolsets("content,bogus")
    message = str(exc.value)
    assert "bogus" in message
    for name in [*TOOLSET_GROUPS, "core", "all"]:
        assert name in message


def test_cli_unknown_toolset_exits_2():
    with patch.dict("os.environ", {"CODA_API_TOKEN": "t"}, clear=False):
        result = CliRunner().invoke(main, ["--toolsets", "bogus"])
    assert result.exit_code == 2
    assert "bogus" in result.output
    assert "content" in result.output
