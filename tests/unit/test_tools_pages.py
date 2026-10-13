"""Behaviour tests for page tools the wire contract does not pin.

Happy-path passthrough, `test_error` and `test_read_only_blocked` duplicated
`test_tool_contract.py` and were removed. What remains asserts omitted-param
defaults and response shaping the contract table does not cover: the `content`
format default, the `insert_mode` default, the name-only update that omits
`contentUpdate`, and the `export` default output format.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from mcp_coda.servers.pages import (
    coda_create_page as _coda_create_page,
)
from mcp_coda.servers.pages import (
    coda_export_page as _coda_export_page,
)
from mcp_coda.servers.pages import (
    coda_update_page as _coda_update_page,
)
from tests.conftest import _body, _make_ctx

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_create_page = getattr(_coda_create_page, "fn", _coda_create_page)
coda_export_page = getattr(_coda_export_page, "fn", _coda_export_page)
coda_update_page = getattr(_coda_update_page, "fn", _coda_update_page)


class TestCreatePage:
    async def test_content_defaults_to_html(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p4"})
        ctx = _make_ctx(client)
        await coda_create_page(ctx, doc_id="d1", name="Page", content="<p>Hi</p>")
        body = client.post.call_args[1]["json_data"]
        assert body["pageContent"]["canvasContent"]["format"] == "html"


class TestUpdatePage:
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


class TestExportPage:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "exp1", "status": "complete"})
        ctx = _make_ctx(client)
        result = _body(await coda_export_page(ctx, doc_id="d1", page_id_or_name="p1"))
        assert result["status"] == "complete"
        body = client.post.call_args[1]["json_data"]
        assert body["outputFormat"] == "markdown"
