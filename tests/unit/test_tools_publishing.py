"""Tests for publishing tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaApiError
from mcp_coda.servers.publishing import (
    coda_list_categories as _coda_list_categories,
)
from mcp_coda.servers.publishing import (
    coda_publish_doc as _coda_publish_doc,
)
from mcp_coda.servers.publishing import (
    coda_unpublish_doc as _coda_unpublish_doc,
)

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_list_categories = getattr(_coda_list_categories, "fn", _coda_list_categories)
coda_publish_doc = getattr(_coda_publish_doc, "fn", _coda_publish_doc)
coda_unpublish_doc = getattr(_coda_unpublish_doc, "fn", _coda_unpublish_doc)


def _make_ctx(client_mock: AsyncMock, read_only: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok", read_only=read_only),
        "client": client_mock,
    }
    return ctx


class TestListCategories:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"items": [{"name": "Project Management"}, {"name": "Education"}]}
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_categories(ctx))
        assert result["total_count"] == 2

    async def test_empty(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_categories(ctx))
        assert result["total_count"] == 0

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(500, "ISE", "fail"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_categories(ctx))
        assert result["isError"] is True


class TestPublishDoc:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={"browserLink": "https://coda.io/@user/my-doc"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_publish_doc(ctx, doc_id="d1"))
        assert "browserLink" in result

    async def test_with_slug_and_categories(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={})
        ctx = _make_ctx(client)
        await coda_publish_doc(ctx, doc_id="d1", slug="my-doc", category_ids=["cat1", "cat2"])
        body = client.put.call_args[1]["json_data"]
        assert body["slug"] == "my-doc"
        assert body["categoryIds"] == ["cat1", "cat2"]

    async def test_with_mode(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={})
        ctx = _make_ctx(client)
        await coda_publish_doc(ctx, doc_id="d1", mode="view")
        body = client.put.call_args[1]["json_data"]
        assert body["mode"] == "view"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_publish_doc(ctx, doc_id="bad"))
        assert result["isError"] is True

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_publish_doc(ctx, doc_id="d1"))
        assert result["isError"] is True


class TestUnpublishDoc:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = json.loads(await coda_unpublish_doc(ctx, doc_id="d1"))
        assert result["status"] == "unpublished"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_unpublish_doc(ctx, doc_id="d1"))
        assert result["isError"] is True
