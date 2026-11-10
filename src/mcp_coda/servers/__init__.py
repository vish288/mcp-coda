"""Coda MCP server — FastMCP instance, lifespan, and tool registration."""

from __future__ import annotations

import importlib
import logging
import os
import pkgutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Any

from fastmcp import FastMCP
from mcp.types import Icon

from ..client import CodaClient
from ..config import CodaConfig, read_only_sources

_log = logging.getLogger(__name__)

_LOCK_SUFFIX = (
    " This deployment is locked read-only: write tools are not listed and cannot be"
    " enabled from the client."
)


def _lock_read_only(server: FastMCP, *, sources: list[str] | None = None) -> None:
    """Hide every write tool and write-workflow prompt from a read-only server, for good.

    fastmcp 4.0.10: ``disable(tags=...)`` appends a ``Visibility(False)`` transform, so
    components carrying the ``write`` tag — tools and prompts alike — drop out of
    ``tools/list`` / ``prompts/list`` and ``tools/call`` on them returns a "Unknown tool"
    error. There is no client-reachable path to re-enable them: ``enable`` and
    ``enable_components`` are server code only, and this server never calls them. The
    ``_check_write`` guard stays as defence in depth. Idempotent off the appended
    instructions sentence so a re-entered lifespan (tests) does not stack visibility
    transforms — no separate module flag to reset.
    """
    if _LOCK_SUFFIX in (server.instructions or ""):
        return
    server.disable(tags={"write"})
    server.instructions = (server.instructions or "") + _LOCK_SUFFIX
    named = f" ({', '.join(sources)})" if sources else ""
    _log.info("read-only: LOCKED%s — write tools and prompts hidden", named)


# MCP_TOOLSETS: coarse tool groups (workbench-backlog#160). A group is a named set of the
# raw domain tags the tools already carry; selecting one or more (MCP_TOOLSETS, a comma
# list, or --toolsets) switches tools/list to an allowlist of just those tools. `core`
# (account) is unioned into every selection — resolve_browser_link turns a pasted Coda URL
# into IDs and get_mutation_status confirms any write, so every job needs them; naming it
# explicitly is accepted but adds nothing. Unset or `all` lists every tool; MCP_READ_ONLY
# still applies after the allowlist and only ever removes tools.
TOOLSET_GROUPS: dict[str, frozenset[str]] = {
    "content": frozenset({"docs", "pages"}),
    "data": frozenset({"tables", "rows", "formulas", "controls", "automations"}),
    "admin": frozenset({"permissions", "folders", "publishing"}),
    "analytics": frozenset({"analytics"}),
}
CORE_TAGS: frozenset[str] = frozenset({"account"})


class UnknownToolsetError(ValueError):
    """MCP_TOOLSETS named a group this server does not define."""


def parse_toolsets(raw: str | None) -> set[str] | None:
    """Resolve MCP_TOOLSETS / --toolsets to the set of raw tags to allowlist.

    None, empty/whitespace, or a list containing ``all`` returns ``None`` — no filtering,
    every tool listed (today's default). Names are lowercase, comma-separated, trimmed;
    ``core`` is accepted (its tags are always included anyway). An unknown name raises
    ``UnknownToolsetError`` naming the offenders and every valid group.
    """
    if not raw or not raw.strip():
        return None
    names = [n.strip().lower() for n in raw.split(",") if n.strip()]
    if not names or "all" in names:
        return None
    valid = {*TOOLSET_GROUPS, "core"}
    unknown = [n for n in names if n not in valid]
    if unknown:
        valid_list = ", ".join([*sorted(TOOLSET_GROUPS), "core", "all"])
        msg = f"Unknown MCP_TOOLSETS group(s): {', '.join(unknown)}. Valid groups: {valid_list}"
        raise UnknownToolsetError(msg)
    tags: set[str] = set(CORE_TAGS)
    for name in names:
        tags |= TOOLSET_GROUPS.get(name, frozenset())
    return tags


def _apply_toolsets(server: FastMCP, raw: str | None) -> None:
    """Allowlist tools for the selected toolsets, keeping every resource and prompt.

    fastmcp 4.1.6: ``enable(tags=..., only=True)`` switches to allowlist mode over *all*
    component types, so resources and prompts would vanish; the chained
    ``enable(components=...)`` re-lists every resource/template/prompt. This runs before the
    read-only ``disable(tags={"write"})`` so the lock stays the last word — an allowlisted
    group still carries its write tools until the lock removes them. A no-op when no toolset
    is selected, so the default server is untouched.
    """
    tags = parse_toolsets(raw)
    if tags is None:
        return
    server.enable(tags=tags, only=True).enable(components={"resource", "template", "prompt"})


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Create shared client and config for the server lifetime."""
    config = CodaConfig.from_env()
    config.validate()

    pkg_version = version("mcp-coda")
    _log.info("mcp-coda %s starting", pkg_version)
    _apply_toolsets(server, os.getenv("MCP_TOOLSETS"))
    if config.read_only:
        _log.info("Coda API: %s", config.base_url)
        _lock_read_only(server, sources=read_only_sources("CODA_READ_ONLY"))
    else:
        _log.info("Coda API: %s (read-only: %s)", config.base_url, config.read_only)

    client = CodaClient(config)
    try:
        yield {"client": client, "config": config}
    finally:
        await client.close()


mcp = FastMCP(
    name="Coda MCP Server",
    version=version("mcp-coda"),
    website_url="https://vish288.github.io/mcp-install?server=mcp-coda",
    icons=[
        Icon(
            src="https://raw.githubusercontent.com/vish288/mcp-coda/main/assets/icon.svg",
            mime_type="image/svg+xml",
            sizes=["any"],
        )
    ],
    instructions=(
        "Provides tools for interacting with the Coda API — "
        "docs, pages, tables, rows, formulas, controls, permissions, folders, "
        "publishing, automations, and analytics."
    ),
    lifespan=lifespan,
    # 2026-07-28 cache hints on list results: a modern client stops re-listing the
    # tools/prompts/resources each turn (#155). cacheScope is private because
    # resources/read can vary by the per-user token; the TTL is 5 minutes. Inert for
    # legacy clients. (cacheScope is fixed at construction, before the per-process
    # read-only decision, so it stays private rather than public-when-locked.)
    cache_ttl=300,
    cache_scope="private",
)


def _register_tools() -> None:
    """Import every sibling module so its @mcp decorators run.

    Discovered from the package directory rather than a hand-kept list, which
    silently dropped a module when someone forgot the entry. Underscore-prefixed
    modules are shared helpers, not registries.
    """
    for info in pkgutil.iter_modules(__path__):
        if not info.name.startswith("_"):
            importlib.import_module(f".{info.name}", __package__)


_register_tools()
