"""Shared test fixtures."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import respx
from fastmcp import Client, FastMCP
from fastmcp.tools import ToolResult

from mcp_coda.client import CodaClient
from mcp_coda.config import CodaConfig
from mcp_coda.servers import mcp

TEST_BASE_URL = "https://coda.io/apis/v1"
TEST_TOKEN = "test-coda-token"


def _err_body(res: ToolResult) -> dict[str, Any]:
    """Assert a `.fn`-level call failed and return its JSON error body.

    Expected failures come back as `ToolResult(is_error=True)` whose text is the
    `_err` JSON and which carries no `structuredContent`.
    """
    assert isinstance(res, ToolResult)
    assert res.is_error is True
    assert res.structured_content is None
    return json.loads(res.content[0].text)


def _body(res: ToolResult) -> dict[str, Any]:
    """Assert a `.fn`-level success result and return its JSON object.

    Success tools return a `ToolResult` whose text is the pretty JSON and whose
    `structuredContent` is the same object; this pins that the two agree (the
    `{"result": "<json>"}` wrapper is gone).
    """
    assert isinstance(res, ToolResult)
    assert res.is_error is False
    body = json.loads(res.content[0].text)
    assert res.structured_content == body
    return body


def _md(res: ToolResult) -> str:
    """Markdown / plain-text success result: return its text.

    These carry no `structuredContent` (the text is not JSON).
    """
    assert isinstance(res, ToolResult)
    assert res.is_error is False
    assert res.structured_content is None
    return res.content[0].text


@pytest.fixture
def config() -> CodaConfig:
    return CodaConfig(token=TEST_TOKEN, base_url=TEST_BASE_URL)


def _make_ctx(client_mock: AsyncMock | None = None, read_only: bool = False) -> MagicMock:
    """Mock Context whose lifespan_context carries a config and a (mock) client.

    The unit layer calls `FunctionTool.fn` directly with this ctx, bypassing
    FastMCP; the contract layer goes through `tool_client` instead.
    """
    ctx = MagicMock()
    ctx.lifespan_context = {
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
