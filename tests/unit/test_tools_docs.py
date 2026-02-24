"""Tests for doc tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaApiError, CodaNotFoundError
from mcp_coda.servers.docs import (
    coda_create_doc as _coda_create_doc,
)
from mcp_coda.servers.docs import (
    coda_delete_doc as _coda_delete_doc,
)
from mcp_coda.servers.docs import (
    coda_get_doc as _coda_get_doc,
)
from mcp_coda.servers.docs import (
    coda_list_docs as _coda_list_docs,
)
from mcp_coda.servers.docs import (
    coda_update_doc as _coda_update_doc,
)

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_create_doc = getattr(_coda_create_doc, "fn", _coda_create_doc)
coda_delete_doc = getattr(_coda_delete_doc, "fn", _coda_delete_doc)
coda_get_doc = getattr(_coda_get_doc, "fn", _coda_get_doc)
coda_list_docs = getattr(_coda_list_docs, "fn", _coda_list_docs)
coda_update_doc = getattr(_coda_update_doc, "fn", _coda_update_doc)


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

    async def test_with_is_owner_filter(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_docs(ctx, is_owner=True)
        call_params = client.get.call_args[1]["params"]
        assert call_params["isOwner"] is True

    async def test_with_folder_id_filter(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_docs(ctx, folder_id="fl1")
        call_params = client.get.call_args[1]["params"]
        assert call_params["folderId"] == "fl1"

    async def test_with_cursor(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_docs(ctx, cursor="abc")
        call_params = client.get.call_args[1]["params"]
        assert call_params["pageToken"] == "abc"

    async def test_markdown_format(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "d1", "name": "My Doc"}],
                "nextPageToken": None,
            }
        )
        ctx = _make_ctx(client)
        result = await coda_list_docs(ctx, response_format="markdown")
        assert "**My Doc**" in result
        assert "1 items returned" in result

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(500, "ISE", "fail"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_docs(ctx))
        assert result["isError"] is True


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

    async def test_with_source_doc(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "d3"})
        ctx = _make_ctx(client)
        await coda_create_doc(ctx, title="Copy", source_doc="d1")
        body = client.post.call_args[1]["json_data"]
        assert body["sourceDoc"] == "d1"

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

    async def test_with_icon(self) -> None:
        client = AsyncMock()
        client.patch = AsyncMock(return_value={"id": "d1"})
        ctx = _make_ctx(client)
        await coda_update_doc(ctx, doc_id="d1", icon_name="rocket")
        body = client.patch.call_args[1]["json_data"]
        assert body["icon"]["name"] == "rocket"
        assert body["icon"]["type"] == "name"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_update_doc(ctx, doc_id="d1", title="Blocked"))
        assert result["isError"] is True

    async def test_error(self) -> None:
        client = AsyncMock()
        client.patch = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_update_doc(ctx, doc_id="bad", title="X"))
        assert result["isError"] is True


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
