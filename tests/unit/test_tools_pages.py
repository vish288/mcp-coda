"""Tests for page tools."""

from __future__ import annotations

from unittest.mock import AsyncMock

from mcp_coda.exceptions import CodaApiError
from mcp_coda.servers.pages import (
    coda_create_page as _coda_create_page,
)
from mcp_coda.servers.pages import (
    coda_delete_page as _coda_delete_page,
)
from mcp_coda.servers.pages import (
    coda_delete_page_content as _coda_delete_page_content,
)
from mcp_coda.servers.pages import (
    coda_export_page as _coda_export_page,
)
from mcp_coda.servers.pages import (
    coda_get_export_status as _coda_get_export_status,
)
from mcp_coda.servers.pages import (
    coda_get_page as _coda_get_page,
)
from mcp_coda.servers.pages import (
    coda_get_page_content as _coda_get_page_content,
)
from mcp_coda.servers.pages import (
    coda_list_pages as _coda_list_pages,
)
from mcp_coda.servers.pages import (
    coda_update_page as _coda_update_page,
)
from tests.conftest import _body, _err_body, _make_ctx

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_create_page = getattr(_coda_create_page, "fn", _coda_create_page)
coda_delete_page = getattr(_coda_delete_page, "fn", _coda_delete_page)
coda_delete_page_content = getattr(_coda_delete_page_content, "fn", _coda_delete_page_content)
coda_export_page = getattr(_coda_export_page, "fn", _coda_export_page)
coda_get_export_status = getattr(_coda_get_export_status, "fn", _coda_get_export_status)
coda_get_page = getattr(_coda_get_page, "fn", _coda_get_page)
coda_get_page_content = getattr(_coda_get_page_content, "fn", _coda_get_page_content)
coda_list_pages = getattr(_coda_list_pages, "fn", _coda_list_pages)
coda_update_page = getattr(_coda_update_page, "fn", _coda_update_page)


class TestListPages:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "p1", "name": "Home"}],
            }
        )
        ctx = _make_ctx(client)
        result = _body(await coda_list_pages(ctx, doc_id="d1"))
        assert result["total_count"] == 1
        assert result["items"][0]["name"] == "Home"

    async def test_with_cursor(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_pages(ctx, doc_id="d1", cursor="abc")
        params = client.get.call_args[1]["params"]
        assert params["pageToken"] == "abc"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = _err_body(await coda_list_pages(ctx, doc_id="bad"))
        assert result["error"]


class TestGetPage:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "p1", "name": "Home"})
        ctx = _make_ctx(client)
        result = _body(await coda_get_page(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["id"] == "p1"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no page"))
        ctx = _make_ctx(client)
        result = _err_body(await coda_get_page(ctx, doc_id="d1", page_id_or_name="bad"))
        assert result["error"]


class TestCreatePage:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p2", "name": "New Page"})
        ctx = _make_ctx(client)
        result = _body(await coda_create_page(ctx, doc_id="d1", name="New Page"))
        assert result["id"] == "p2"

    async def test_with_content(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p2"})
        ctx = _make_ctx(client)
        await coda_create_page(
            ctx, doc_id="d1", name="Page", content="# Hello", content_format="markdown"
        )
        body = client.post.call_args[1]["json_data"]
        assert body["pageContent"]["type"] == "canvas"
        assert body["pageContent"]["canvasContent"]["content"] == "# Hello"
        assert body["pageContent"]["canvasContent"]["format"] == "markdown"

    async def test_with_parent_and_subtitle(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p3"})
        ctx = _make_ctx(client)
        await coda_create_page(
            ctx,
            doc_id="d1",
            name="Sub Page",
            parent_page_id="p1",
            subtitle="A subtitle",
        )
        body = client.post.call_args[1]["json_data"]
        assert body["parentPageId"] == "p1"
        assert body["subtitle"] == "A subtitle"

    async def test_content_defaults_to_html(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p4"})
        ctx = _make_ctx(client)
        await coda_create_page(ctx, doc_id="d1", name="Page", content="<p>Hi</p>")
        body = client.post.call_args[1]["json_data"]
        assert body["pageContent"]["canvasContent"]["format"] == "html"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = _err_body(await coda_create_page(ctx, doc_id="d1", name="Blocked"))
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
        assert body["contentUpdate"]["canvasContent"]["format"] == "markdown"
        assert body["contentUpdate"]["canvasContent"]["content"] == "Updated text"

    async def test_content_update_defaults_to_replace(self) -> None:
        """insert_mode omitted → insertionMode 'replace' (overwrite), not append.

        Append silently grows the page on every edit; replace is the safe
        default the docstring promises.
        """
        client = AsyncMock()
        client.put = AsyncMock(return_value={"id": "p1"})
        ctx = _make_ctx(client)
        await coda_update_page(ctx, doc_id="d1", page_id_or_name="p1", content="New text")
        body = client.put.call_args[1]["json_data"]
        assert body["contentUpdate"]["insertionMode"] == "replace"

    async def test_name_only_update(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={"id": "p1", "name": "Renamed"})
        ctx = _make_ctx(client)
        result = _body(
            await coda_update_page(ctx, doc_id="d1", page_id_or_name="p1", name="Renamed")
        )
        assert result["name"] == "Renamed"
        body = client.put.call_args[1]["json_data"]
        assert body["name"] == "Renamed"
        assert "contentUpdate" not in body

    async def test_subtitle_update(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={"id": "p1"})
        ctx = _make_ctx(client)
        await coda_update_page(ctx, doc_id="d1", page_id_or_name="p1", subtitle="New subtitle")
        body = client.put.call_args[1]["json_data"]
        assert body["subtitle"] == "New subtitle"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = _err_body(
            await coda_update_page(ctx, doc_id="d1", page_id_or_name="p1", name="Blocked")
        )
        assert result["error"]

    async def test_error(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no page"))
        ctx = _make_ctx(client)
        result = _err_body(
            await coda_update_page(ctx, doc_id="d1", page_id_or_name="bad", name="X")
        )
        assert result["error"]


class TestGetPageContent:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"content": "# Title"})
        ctx = _make_ctx(client)
        result = _body(
            await coda_get_page_content(
                ctx, doc_id="d1", page_id_or_name="p1", output_format="markdown"
            )
        )
        assert result["content"] == "# Title"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no page"))
        ctx = _make_ctx(client)
        result = _err_body(await coda_get_page_content(ctx, doc_id="d1", page_id_or_name="bad"))
        assert result["error"]


class TestDeletePage:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = _body(await coda_delete_page(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["status"] == "deleted"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = _err_body(await coda_delete_page(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["error"]

    async def test_error(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no page"))
        ctx = _make_ctx(client)
        result = _err_body(await coda_delete_page(ctx, doc_id="d1", page_id_or_name="bad"))
        assert result["error"]


class TestDeletePageContent:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = _body(await coda_delete_page_content(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["status"] == "content_deleted"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = _err_body(await coda_delete_page_content(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["error"]

    async def test_error(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(side_effect=CodaApiError(500, "ISE", "fail"))
        ctx = _make_ctx(client)
        result = _err_body(await coda_delete_page_content(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["error"]


class TestExportPage:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "exp1", "status": "complete"})
        ctx = _make_ctx(client)
        result = _body(await coda_export_page(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["status"] == "complete"
        body = client.post.call_args[1]["json_data"]
        assert body["outputFormat"] == "markdown"

    async def test_html_format(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "exp2"})
        ctx = _make_ctx(client)
        await coda_export_page(ctx, doc_id="d1", page_id_or_name="p1", output_format="html")
        body = client.post.call_args[1]["json_data"]
        assert body["outputFormat"] == "html"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no page"))
        ctx = _make_ctx(client)
        result = _err_body(await coda_export_page(ctx, doc_id="d1", page_id_or_name="bad"))
        assert result["error"]


class TestGetExportStatus:
    async def test_calls_export_status_path_no_params(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "req-1", "status": "inProgress"})
        ctx = _make_ctx(client)
        await coda_get_export_status(ctx, doc_id="d1", page_id_or_name="p1", request_id="req-1")
        assert client.get.call_args[0][0] == "/docs/d1/pages/p1/export/req-1"
        # No query params — the request_id is a path segment.
        assert client.get.call_args == (("/docs/d1/pages/p1/export/req-1",), {})

    async def test_complete_passes_download_link(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "id": "req-1",
                "status": "complete",
                "downloadLink": "https://coda.io/blob/x",
            }
        )
        ctx = _make_ctx(client)
        result = _body(
            await coda_get_export_status(ctx, doc_id="d1", page_id_or_name="p1", request_id="req-1")
        )
        assert result["status"] == "complete"
        assert result["downloadLink"] == "https://coda.io/blob/x"

    async def test_failed_passes_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"status": "failed", "error": "too big"})
        ctx = _make_ctx(client)
        result = _body(
            await coda_get_export_status(ctx, doc_id="d1", page_id_or_name="p1", request_id="req-1")
        )
        assert result["status"] == "failed"
        assert result["error"] == "too big"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "expired"))
        ctx = _make_ctx(client)
        result = _err_body(
            await coda_get_export_status(ctx, doc_id="d1", page_id_or_name="p1", request_id="gone")
        )
        assert result["error"]
        assert result["status_code"] == 404
