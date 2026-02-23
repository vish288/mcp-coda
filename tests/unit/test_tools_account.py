"""Tests for account tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaAuthError
from mcp_coda.servers.account import (
    coda_get_mutation_status,
    coda_resolve_browser_link,
    coda_whoami,
)


def _make_ctx(client_mock: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok"),
        "client": client_mock,
    }
    return ctx


class TestWhoami:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"name": "Test User", "loginId": "test@example.com"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_whoami(ctx))
        assert result["name"] == "Test User"
        client.get.assert_called_once_with("/whoami")

    async def test_auth_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaAuthError(401, "bad token"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_whoami(ctx))
        assert "error" in result
        assert result["status_code"] == 401


class TestResolveBrowserLink:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"type": "doc", "docId": "abc123"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_resolve_browser_link(ctx, url="https://coda.io/d/abc123"))
        assert result["type"] == "doc"
        assert result["docId"] == "abc123"


class TestMutationStatus:
    async def test_completed(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"completed": True})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_mutation_status(ctx, request_id="req-1"))
        assert result["completed"] is True
        client.get.assert_called_once_with("/mutationStatus/req-1")
