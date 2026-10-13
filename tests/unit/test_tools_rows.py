"""Behaviour tests for row tools the wire contract does not pin.

Happy-path passthrough, `test_error`, `test_read_only_blocked` and simple
param-echo tests duplicated `test_tool_contract.py` and were removed. What
remains asserts behaviour the contract table does not: the `use_column_names`
default, the markdown branch (empty / populated / has-more) and the
null-response shape of `coda_delete_rows`.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from mcp_coda.servers.rows import (
    coda_delete_rows as _coda_delete_rows,
)
from mcp_coda.servers.rows import (
    coda_list_rows as _coda_list_rows,
)
from tests.conftest import _body, _make_ctx, _md

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_delete_rows = getattr(_coda_delete_rows, "fn", _coda_delete_rows)
coda_list_rows = getattr(_coda_list_rows, "fn", _coda_list_rows)


class TestListRows:
    async def test_uses_column_names_by_default(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_rows(ctx, doc_id="d1", table_id_or_name="t1")
        call_params = client.get.call_args[1]["params"]
        assert call_params["useColumnNames"] is True

    async def test_markdown_format(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [
                    {"id": "r1", "name": "Row 1", "values": {"Name": "Alice", "Age": 30}},
                    {"id": "r2", "name": "Row 2", "values": {"Name": "Bob", "Age": 25}},
                ],
                "nextPageToken": None,
            }
        )
        ctx = _make_ctx(client)
        result = _md(
            await coda_list_rows(
                ctx, doc_id="d1", table_id_or_name="t1", response_format="markdown"
            )
        )
        assert "Row 1" in result
        assert "Alice" in result
        assert "2 rows returned" in result

    async def test_markdown_format_empty(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [], "nextPageToken": None})
        ctx = _make_ctx(client)
        result = _md(
            await coda_list_rows(
                ctx, doc_id="d1", table_id_or_name="t1", response_format="markdown"
            )
        )
        assert "*No rows found.*" in result

    async def test_markdown_format_has_more(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "r1", "name": "Row 1", "values": {"X": 1}}],
                "nextPageToken": "cursor2",
            }
        )
        ctx = _make_ctx(client)
        result = _md(
            await coda_list_rows(
                ctx, doc_id="d1", table_id_or_name="t1", response_format="markdown"
            )
        )
        assert "more available" in result
        assert "cursor2" in result


class TestDeleteRows:
    async def test_success_null_response(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = _body(
            await coda_delete_rows(ctx, doc_id="d1", table_id_or_name="t1", row_ids=["r1"])
        )
        assert result["status"] == "deleted"
        assert result["row_count"] == 1
