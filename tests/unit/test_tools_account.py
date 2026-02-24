"""Tests for account tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaApiError, CodaAuthError
from mcp_coda.servers.account import (
    coda_get_mutation_status as _coda_get_mutation_status,
)
from mcp_coda.servers.account import (
    coda_rate_limit_budget as _coda_rate_limit_budget,
)
from mcp_coda.servers.account import (
    coda_resolve_browser_link as _coda_resolve_browser_link,
)
from mcp_coda.servers.account import (
    coda_whoami as _coda_whoami,
)

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_get_mutation_status = getattr(_coda_get_mutation_status, "fn", _coda_get_mutation_status)
coda_rate_limit_budget = getattr(_coda_rate_limit_budget, "fn", _coda_rate_limit_budget)
coda_resolve_browser_link = getattr(_coda_resolve_browser_link, "fn", _coda_resolve_browser_link)
coda_whoami = getattr(_coda_whoami, "fn", _coda_whoami)


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

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(400, "Bad Request", "invalid url"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_resolve_browser_link(ctx, url="not-a-url"))
        assert result["isError"] is True


class TestMutationStatus:
    async def test_completed(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"completed": True})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_mutation_status(ctx, request_id="req-1"))
        assert result["completed"] is True
        client.get.assert_called_once_with("/mutationStatus/req-1")

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no such request"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_mutation_status(ctx, request_id="bad"))
        assert result["isError"] is True


class TestRateLimitBudget:
    async def test_success(self) -> None:
        client = AsyncMock()
        budget_mock = MagicMock()
        budget_mock.remaining.return_value = {"reads": 95, "writes": 8}
        client.budget = budget_mock
        ctx = _make_ctx(client)
        result = json.loads(await coda_rate_limit_budget(ctx))
        assert result["reads"] == 95
        assert result["writes"] == 8

    async def test_error(self) -> None:
        client = AsyncMock()
        budget_mock = MagicMock()
        budget_mock.remaining.side_effect = RuntimeError("budget unavailable")
        client.budget = budget_mock
        ctx = _make_ctx(client)
        result = json.loads(await coda_rate_limit_budget(ctx))
        assert result["isError"] is True
