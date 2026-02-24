"""Coda MCP server — FastMCP instance, lifespan, and tool registration."""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from ..client import CodaClient
from ..config import CodaConfig


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Create shared client and config for the server lifetime."""
    config = CodaConfig.from_env()
    config.validate()
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
    """Import tool and resource modules so decorators execute."""
    _modules = [
        ".account",
        ".docs",
        ".pages",
        ".tables",
        ".rows",
        ".formulas",
        ".controls",
        ".automations",
        ".permissions",
        ".publishing",
        ".folders",
        ".analytics",
        ".resources",
        ".prompts",
    ]
    for module in _modules:
        importlib.import_module(module, __package__)


_register_tools()
