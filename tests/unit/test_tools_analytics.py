"""Tests for analytics tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.servers.analytics import (
    coda_get_analytics_updated,
    coda_get_doc_analytics_summary,
    coda_get_pack_analytics_summary,
    coda_list_doc_analytics,
    coda_list_pack_analytics,
    coda_list_pack_formula_analytics,
    coda_list_page_analytics,
)


def _make_ctx(client_mock: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok"),
        "client": client_mock,
    }
    return ctx


class TestListDocAnalytics:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"doc": {"id": "d1"}, "totalViews": 100}],
                "nextPageToken": "cur2",
            }
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_doc_analytics(ctx))
        assert result["total_count"] == 1
        assert result["has_more"] is True

    async def test_with_filters(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_doc_analytics(
            ctx,
            doc_ids=["d1", "d2"],
            since_date="2024-01-01",
            until_date="2024-12-31",
        )
        params = client.get.call_args[1]["params"]
        assert params["docIds"] == "d1,d2"
        assert params["sinceDate"] == "2024-01-01"
        assert params["untilDate"] == "2024-12-31"


class TestGetDocAnalyticsSummary:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"totalViews": 500, "totalCopies": 10})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_doc_analytics_summary(ctx))
        assert result["totalViews"] == 500


class TestListPageAnalytics:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [{"page": {"id": "p1"}, "views": 50}]})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_page_analytics(ctx, doc_id="d1"))
        assert result["total_count"] == 1


class TestListPackAnalytics:
    async def test_with_pack_ids(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_pack_analytics(ctx, pack_ids=[1, 2])
        params = client.get.call_args[1]["params"]
        assert params["packIds"] == "1,2"


class TestGetPackAnalyticsSummary:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"totalInstalls": 200})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_pack_analytics_summary(ctx))
        assert result["totalInstalls"] == 200


class TestListPackFormulaAnalytics:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"items": [{"formulaName": "MyFormula", "invocations": 100}]}
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_pack_formula_analytics(ctx, pack_id=42))
        assert result["total_count"] == 1


class TestGetAnalyticsUpdated:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"updated": "2024-06-15T10:00:00Z"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_analytics_updated(ctx))
        assert "updated" in result
