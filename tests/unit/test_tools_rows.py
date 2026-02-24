"""Tests for row tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaApiError
from mcp_coda.servers.rows import (
    coda_delete_row as _coda_delete_row,
    coda_delete_rows as _coda_delete_rows,
    coda_get_row as _coda_get_row,
    coda_insert_rows as _coda_insert_rows,
    coda_list_rows as _coda_list_rows,
    coda_push_button as _coda_push_button,
    coda_update_row as _coda_update_row,
)

# Unwrap FunctionTool objects to get the raw async functions
coda_delete_row = _coda_delete_row.fn
coda_delete_rows = _coda_delete_rows.fn
coda_get_row = _coda_get_row.fn
coda_insert_rows = _coda_insert_rows.fn
coda_list_rows = _coda_list_rows.fn
coda_push_button = _coda_push_button.fn
coda_update_row = _coda_update_row.fn


def _make_ctx(client_mock: AsyncMock, read_only: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok", read_only=read_only),
        "client": client_mock,
    }
    return ctx


class TestListRows:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "r1", "values": {"Name": "Alice"}}],
                "nextPageToken": None,
            }
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_rows(ctx, doc_id="d1", table_id_or_name="t1"))
        assert result["total_count"] == 1
        assert result["items"][0]["values"]["Name"] == "Alice"

    async def test_with_query(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_rows(ctx, doc_id="d1", table_id_or_name="t1", query='Status:"Active"')
        call_params = client.get.call_args[1]["params"]
        assert call_params["query"] == 'Status:"Active"'

    async def test_uses_column_names_by_default(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_rows(ctx, doc_id="d1", table_id_or_name="t1")
        call_params = client.get.call_args[1]["params"]
        assert call_params["useColumnNames"] is True

    async def test_with_sort_by(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_rows(ctx, doc_id="d1", table_id_or_name="t1", sort_by="-Created")
        call_params = client.get.call_args[1]["params"]
        assert call_params["sortBy"] == "-Created"

    async def test_with_cursor(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_rows(ctx, doc_id="d1", table_id_or_name="t1", cursor="abc123")
        call_params = client.get.call_args[1]["params"]
        assert call_params["pageToken"] == "abc123"

    async def test_pagination_has_more(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"items": [{"id": "r1"}], "nextPageToken": "next1"}
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_rows(ctx, doc_id="d1", table_id_or_name="t1"))
        assert result["has_more"] is True
        assert result["next_cursor"] == "next1"

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
        result = await coda_list_rows(
            ctx, doc_id="d1", table_id_or_name="t1", response_format="markdown"
        )
        assert "Row 1" in result
        assert "Alice" in result
        assert "2 rows returned" in result

    async def test_markdown_format_empty(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [], "nextPageToken": None})
        ctx = _make_ctx(client)
        result = await coda_list_rows(
            ctx, doc_id="d1", table_id_or_name="t1", response_format="markdown"
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
        result = await coda_list_rows(
            ctx, doc_id="d1", table_id_or_name="t1", response_format="markdown"
        )
        assert "more available" in result
        assert "cursor2" in result

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(500, "ISE", "server error"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_rows(ctx, doc_id="d1", table_id_or_name="t1"))
        assert result["isError"] is True
        assert result["status_code"] == 500


class TestGetRow:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "r1", "values": {"Name": "Bob"}})
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_get_row(ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="r1")
        )
        assert result["values"]["Name"] == "Bob"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no such row"))
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_get_row(ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="bad")
        )
        assert result["isError"] is True


class TestInsertRows:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"requestId": "req-1"})
        ctx = _make_ctx(client)
        rows = [{"cells": [{"column": "Name", "value": "Carol"}]}]
        result = json.loads(
            await coda_insert_rows(ctx, doc_id="d1", table_id_or_name="t1", rows=rows)
        )
        assert result["requestId"] == "req-1"

    async def test_with_key_columns_upsert(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"requestId": "req-2"})
        ctx = _make_ctx(client)
        rows = [{"cells": [{"column": "Email", "value": "a@b.com"}]}]
        await coda_insert_rows(
            ctx, doc_id="d1", table_id_or_name="t1", rows=rows, key_columns=["Email"]
        )
        body = client.post.call_args[1]["json_data"]
        assert body["keyColumns"] == ["Email"]

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(
            await coda_insert_rows(ctx, doc_id="d1", table_id_or_name="t1", rows=[])
        )
        assert "CODA_READ_ONLY" in result["error"]


class TestUpdateRow:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={"requestId": "req-3"})
        ctx = _make_ctx(client)
        cells = [{"column": "Status", "value": "Done"}]
        result = json.loads(
            await coda_update_row(
                ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="r1", cells=cells
            )
        )
        assert result["requestId"] == "req-3"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        cells = [{"column": "Status", "value": "Done"}]
        result = json.loads(
            await coda_update_row(
                ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="r1", cells=cells
            )
        )
        assert result["isError"] is True

    async def test_error(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no row"))
        ctx = _make_ctx(client)
        cells = [{"column": "Status", "value": "Done"}]
        result = json.loads(
            await coda_update_row(
                ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="bad", cells=cells
            )
        )
        assert result["isError"] is True


class TestDeleteRow:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_delete_row(ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="r1")
        )
        assert result["status"] == "deleted"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(
            await coda_delete_row(ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="r1")
        )
        assert result["isError"] is True

    async def test_error(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no row"))
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_delete_row(ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="bad")
        )
        assert result["isError"] is True


class TestDeleteRows:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value={"requestId": "req-5"})
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_delete_rows(
                ctx, doc_id="d1", table_id_or_name="t1", row_ids=["r1", "r2"]
            )
        )
        assert result["requestId"] == "req-5"

    async def test_success_null_response(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_delete_rows(
                ctx, doc_id="d1", table_id_or_name="t1", row_ids=["r1"]
            )
        )
        assert result["status"] == "deleted"
        assert result["row_count"] == 1

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(
            await coda_delete_rows(
                ctx, doc_id="d1", table_id_or_name="t1", row_ids=["r1"]
            )
        )
        assert result["isError"] is True

    async def test_error(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(side_effect=CodaApiError(500, "ISE", "fail"))
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_delete_rows(
                ctx, doc_id="d1", table_id_or_name="t1", row_ids=["r1"]
            )
        )
        assert result["isError"] is True


class TestPushButton:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"requestId": "req-4"})
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_push_button(
                ctx,
                doc_id="d1",
                table_id_or_name="t1",
                row_id_or_name="r1",
                column_id_or_name="Push Me",
            )
        )
        assert result["requestId"] == "req-4"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(
            await coda_push_button(
                ctx,
                doc_id="d1",
                table_id_or_name="t1",
                row_id_or_name="r1",
                column_id_or_name="btn",
            )
        )
        assert result["isError"] is True

    async def test_error(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no button"))
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_push_button(
                ctx,
                doc_id="d1",
                table_id_or_name="t1",
                row_id_or_name="r1",
                column_id_or_name="bad",
            )
        )
        assert result["isError"] is True
