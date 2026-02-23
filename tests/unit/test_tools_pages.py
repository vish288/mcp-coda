"""Tests for page tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.servers.pages import (
    coda_create_page,
    coda_delete_page,
    coda_get_page,
    coda_get_page_content,
    coda_list_pages,
    coda_update_page,
)


def _make_ctx(client_mock: AsyncMock, read_only: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok", read_only=read_only),
        "client": client_mock,
    }
    return ctx


class TestListPages:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "p1", "name": "Home"}],
            }
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_pages(ctx, doc_id="d1"))
        assert result["total_count"] == 1
        assert result["items"][0]["name"] == "Home"


class TestGetPage:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "p1", "name": "Home"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_page(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["id"] == "p1"


class TestCreatePage:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p2", "name": "New Page"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_create_page(ctx, doc_id="d1", name="New Page"))
        assert result["id"] == "p2"

    async def test_with_content(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p2"})
        ctx = _make_ctx(client)
        await coda_create_page(
            ctx, doc_id="d1", name="Page", content="# Hello", content_format="markdown"
        )
        body = client.post.call_args[1]["json_data"]
        assert body["pageContent"]["content"] == "# Hello"
        assert body["pageContent"]["contentFormat"] == "markdown"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_create_page(ctx, doc_id="d1", name="Blocked"))
        assert "CODA_READ_ONLY" in result["error"]


class TestUpdatePage:
    async def test_content_update(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={"id": "p1"})
        ctx = _make_ctx(client)
        await coda_update_page(
            ctx,
            doc_id="d1",
            page_id_or_name="p1",
            content="Updated text",
            content_format="markdown",
            insert_mode="replace",
        )
        body = client.put.call_args[1]["json_data"]
        assert body["contentUpdate"]["insertionMode"] == "replace"


class TestGetPageContent:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"content": "# Title"})
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_get_page_content(
                ctx, doc_id="d1", page_id_or_name="p1", output_format="markdown"
            )
        )
        assert result["content"] == "# Title"


class TestDeletePage:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = json.loads(await coda_delete_page(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["status"] == "deleted"
