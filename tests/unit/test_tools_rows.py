"""Tests for row tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.servers.rows import (
    coda_delete_row,
    coda_get_row,
    coda_insert_rows,
    coda_list_rows,
    coda_push_button,
    coda_update_row,
)


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


class TestGetRow:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "r1", "values": {"Name": "Bob"}})
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_get_row(ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="r1")
        )
        assert result["values"]["Name"] == "Bob"


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


class TestDeleteRow:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_delete_row(ctx, doc_id="d1", table_id_or_name="t1", row_id_or_name="r1")
        )
        assert result["status"] == "deleted"


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
