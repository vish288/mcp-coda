"""Coda MCP server — FastMCP instance, lifespan, and tool registration."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Any

from fastmcp import FastMCP

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


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Create shared client and config for the server lifetime."""
    config = CodaConfig.from_env()
    config.validate()

    pkg_version = version("mcp-coda")
    _log.info("mcp-coda %s starting", pkg_version)
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
    instructions=(
        "Provides tools for interacting with the Coda API — "
        "docs, pages, tables, rows, formulas, controls, permissions, folders, "
        "publishing, automations, and analytics."
    ),
    lifespan=lifespan,
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
