"""Tests for analytics tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaApiError
from mcp_coda.servers.analytics import (
    coda_get_analytics_updated as _coda_get_analytics_updated,
)
from mcp_coda.servers.analytics import (
    coda_get_doc_analytics_summary as _coda_get_doc_analytics_summary,
)
from mcp_coda.servers.analytics import (
    coda_get_pack_analytics_summary as _coda_get_pack_analytics_summary,
)
from mcp_coda.servers.analytics import (
    coda_list_doc_analytics as _coda_list_doc_analytics,
)
from mcp_coda.servers.analytics import (
    coda_list_pack_analytics as _coda_list_pack_analytics,
)
from mcp_coda.servers.analytics import (
    coda_list_pack_formula_analytics as _coda_list_pack_formula_analytics,
)
from mcp_coda.servers.analytics import (
    coda_list_page_analytics as _coda_list_page_analytics,
)

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_get_analytics_updated = getattr(_coda_get_analytics_updated, "fn", _coda_get_analytics_updated)
coda_get_doc_analytics_summary = getattr(
    _coda_get_doc_analytics_summary, "fn", _coda_get_doc_analytics_summary
)
coda_get_pack_analytics_summary = getattr(
    _coda_get_pack_analytics_summary, "fn", _coda_get_pack_analytics_summary
)
coda_list_doc_analytics = getattr(_coda_list_doc_analytics, "fn", _coda_list_doc_analytics)
coda_list_pack_analytics = getattr(_coda_list_pack_analytics, "fn", _coda_list_pack_analytics)
coda_list_pack_formula_analytics = getattr(
    _coda_list_pack_formula_analytics, "fn", _coda_list_pack_formula_analytics
)
coda_list_page_analytics = getattr(_coda_list_page_analytics, "fn", _coda_list_page_analytics)


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

    async def test_with_is_published(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_doc_analytics(ctx, is_published=True)
        params = client.get.call_args[1]["params"]
        assert params["isPublished"] is True

    async def test_with_cursor(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_doc_analytics(ctx, cursor="page2")
        params = client.get.call_args[1]["params"]
        assert params["pageToken"] == "page2"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(403, "Forbidden", "no access"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_doc_analytics(ctx))
        assert result["isError"] is True


class TestGetDocAnalyticsSummary:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"totalViews": 500, "totalCopies": 10})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_doc_analytics_summary(ctx))
        assert result["totalViews"] == 500

    async def test_with_filters(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"totalViews": 100})
        ctx = _make_ctx(client)
        await coda_get_doc_analytics_summary(
            ctx, is_published=False, since_date="2024-06-01", until_date="2024-12-31"
        )
        params = client.get.call_args[1]["params"]
        assert params["isPublished"] is False
        assert params["sinceDate"] == "2024-06-01"
        assert params["untilDate"] == "2024-12-31"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(500, "ISE", "fail"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_doc_analytics_summary(ctx))
        assert result["isError"] is True


class TestListPageAnalytics:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [{"page": {"id": "p1"}, "views": 50}]})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_page_analytics(ctx, doc_id="d1"))
        assert result["total_count"] == 1

    async def test_with_filters(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_page_analytics(
            ctx,
            doc_id="d1",
            since_date="2024-01-01",
            until_date="2024-06-30",
            cursor="abc",
        )
        params = client.get.call_args[1]["params"]
        assert params["sinceDate"] == "2024-01-01"
        assert params["untilDate"] == "2024-06-30"
        assert params["pageToken"] == "abc"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_page_analytics(ctx, doc_id="bad"))
        assert result["isError"] is True


class TestListPackAnalytics:
    async def test_with_pack_ids(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_pack_analytics(ctx, pack_ids=[1, 2])
        params = client.get.call_args[1]["params"]
        assert params["packIds"] == "1,2"

    async def test_with_all_filters(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [], "nextPageToken": "p2"})
        ctx = _make_ctx(client)
        await coda_list_pack_analytics(
            ctx,
            is_published=True,
            since_date="2024-01-01",
            until_date="2024-12-31",
            cursor="p1",
        )
        params = client.get.call_args[1]["params"]
        assert params["isPublished"] is True
        assert params["sinceDate"] == "2024-01-01"
        assert params["untilDate"] == "2024-12-31"
        assert params["pageToken"] == "p1"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(403, "Forbidden", "no access"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_pack_analytics(ctx))
        assert result["isError"] is True


class TestGetPackAnalyticsSummary:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"totalInstalls": 200})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_pack_analytics_summary(ctx))
        assert result["totalInstalls"] == 200

    async def test_with_filters(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"totalInstalls": 50})
        ctx = _make_ctx(client)
        await coda_get_pack_analytics_summary(
            ctx,
            pack_ids=[10, 20],
            is_published=True,
            since_date="2024-01-01",
            until_date="2024-12-31",
        )
        params = client.get.call_args[1]["params"]
        assert params["packIds"] == "10,20"
        assert params["isPublished"] is True

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(500, "ISE", "fail"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_pack_analytics_summary(ctx))
        assert result["isError"] is True


class TestListPackFormulaAnalytics:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"items": [{"formulaName": "MyFormula", "invocations": 100}]}
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_pack_formula_analytics(ctx, pack_id=42))
        assert result["total_count"] == 1

    async def test_with_filters(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_pack_formula_analytics(
            ctx,
            pack_id=42,
            since_date="2024-01-01",
            until_date="2024-12-31",
            cursor="c1",
        )
        params = client.get.call_args[1]["params"]
        assert params["sinceDate"] == "2024-01-01"
        assert params["untilDate"] == "2024-12-31"
        assert params["pageToken"] == "c1"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no pack"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_pack_formula_analytics(ctx, pack_id=999))
        assert result["isError"] is True


class TestGetAnalyticsUpdated:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"updated": "2024-06-15T10:00:00Z"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_analytics_updated(ctx))
        assert "updated" in result

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(500, "ISE", "fail"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_analytics_updated(ctx))
        assert result["isError"] is True
