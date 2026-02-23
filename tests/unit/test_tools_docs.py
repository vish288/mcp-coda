"""Tests for doc tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaNotFoundError
from mcp_coda.servers.docs import (
    coda_create_doc,
    coda_delete_doc,
    coda_get_doc,
    coda_list_docs,
    coda_update_doc,
)


def _make_ctx(client_mock: AsyncMock, read_only: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok", read_only=read_only),
        "client": client_mock,
    }
    return ctx


class TestListDocs:
    async def test_success_with_pagination(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "d1", "name": "Doc 1"}],
                "nextPageToken": "cursor-2",
            }
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_docs(ctx, limit=10))
        assert result["total_count"] == 1
        assert result["has_more"] is True
        assert result["next_cursor"] == "cursor-2"

    async def test_no_more_pages(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [{"id": "d1"}]})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_docs(ctx))
        assert result["has_more"] is False
        assert result["next_cursor"] is None

    async def test_with_query_filter(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_docs(ctx, query="sprint")
        call_params = client.get.call_args[1]["params"]
        assert call_params["query"] == "sprint"


class TestGetDoc:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "d1", "name": "My Doc"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_doc(ctx, doc_id="d1"))
        assert result["name"] == "My Doc"

    async def test_not_found(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaNotFoundError("no such doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_doc(ctx, doc_id="nope"))
        assert result["status_code"] == 404
        assert result["isError"] is True


class TestCreateDoc:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "d2", "name": "New Doc"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_create_doc(ctx, title="New Doc"))
        assert result["id"] == "d2"

    async def test_with_folder(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "d2"})
        ctx = _make_ctx(client)
        await coda_create_doc(ctx, title="Doc", folder_id="f1")
        body = client.post.call_args[1]["json_data"]
        assert body["folderId"] == "f1"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_create_doc(ctx, title="Blocked"))
        assert "CODA_READ_ONLY" in result["error"]


class TestUpdateDoc:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.patch = AsyncMock(return_value={"id": "d1", "name": "Renamed"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_update_doc(ctx, doc_id="d1", title="Renamed"))
        assert result["name"] == "Renamed"


class TestDeleteDoc:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = json.loads(await coda_delete_doc(ctx, doc_id="d1"))
        assert result["status"] == "deleted"
        assert result["doc_id"] == "d1"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_delete_doc(ctx, doc_id="d1"))
        assert "CODA_READ_ONLY" in result["error"]
