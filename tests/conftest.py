"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx
from fastmcp import Client, FastMCP

from mcp_coda.client import CodaClient
from mcp_coda.config import CodaConfig
from mcp_coda.servers import mcp

TEST_BASE_URL = "https://coda.io/apis/v1"
TEST_TOKEN = "test-coda-token"


@pytest.fixture
def config() -> CodaConfig:
    return CodaConfig(token=TEST_TOKEN, base_url=TEST_BASE_URL)


def _make_ctx(client_mock: AsyncMock | None = None, read_only: bool = False) -> MagicMock:
    """Mock Context whose lifespan_context carries a config and a (mock) client.

    The unit layer calls `FunctionTool.fn` directly with this ctx, bypassing
    FastMCP; the contract layer goes through `tool_client` instead.
    """
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok", read_only=read_only),
        "client": MagicMock() if client_mock is None else client_mock,
    }
    return ctx


@asynccontextmanager
async def _serve(*, read_only: bool) -> AsyncIterator[tuple[Client, respx.MockRouter]]:
    """The real `mcp` with its lifespan swapped for a client aimed at respx."""
    config = CodaConfig(token=TEST_TOKEN, base_url=TEST_BASE_URL, read_only=read_only)
    client = CodaClient(config)

    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
        try:
            yield {"client": client, "config": config}
        finally:
            await client.close()

    original = mcp._lifespan
    mcp._lifespan = lifespan
    try:
        with respx.mock(base_url=TEST_BASE_URL) as router:
            async with Client(mcp) as mcp_client:
                yield mcp_client, router
    finally:
        mcp._lifespan = original


@pytest.fixture
async def tool_client() -> AsyncIterator[tuple[Client, respx.MockRouter]]:
    """FastMCP client over the real server with respx-mocked HTTP."""
    async with _serve(read_only=False) as pair:
        yield pair


@pytest.fixture
async def readonly_client() -> AsyncIterator[tuple[Client, respx.MockRouter]]:
    """Same as `tool_client`, with CODA_READ_ONLY semantics on."""
    async with _serve(read_only=True) as pair:
        yield pair
