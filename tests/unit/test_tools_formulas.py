"""Tests for formula tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.servers.formulas import coda_get_formula, coda_list_formulas


def _make_ctx(client_mock: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok"),
        "client": client_mock,
    }
    return ctx


class TestListFormulas:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"items": [{"id": "f1", "name": "TotalBudget", "value": 5000}]}
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_formulas(ctx, doc_id="d1"))
        assert result["total_count"] == 1
        assert result["items"][0]["value"] == 5000

    async def test_pagination(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [], "nextPageToken": "next"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_formulas(ctx, doc_id="d1"))
        assert result["has_more"] is True


class TestGetFormula:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "f1", "name": "TotalBudget", "value": 5000})
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_get_formula(ctx, doc_id="d1", formula_id_or_name="TotalBudget")
        )
        assert result["name"] == "TotalBudget"
