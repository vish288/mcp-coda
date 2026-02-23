"""Tests for table tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.servers.tables import (
    coda_get_column,
    coda_get_table,
    coda_list_columns,
    coda_list_tables,
)


def _make_ctx(client_mock: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok"),
        "client": client_mock,
    }
    return ctx


class TestListTables:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "t1", "name": "Tasks"}],
                "nextPageToken": "cur2",
            }
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_tables(ctx, doc_id="d1"))
        assert result["total_count"] == 1
        assert result["has_more"] is True
        assert result["next_cursor"] == "cur2"

    async def test_with_table_types_filter(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_tables(ctx, doc_id="d1", table_types="view")
        params = client.get.call_args[1]["params"]
        assert params["tableTypes"] == "view"


class TestGetTable:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "t1", "name": "Tasks", "rowCount": 42})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_table(ctx, doc_id="d1", table_id_or_name="t1"))
        assert result["name"] == "Tasks"
        assert result["rowCount"] == 42


class TestListColumns:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [{"id": "c1", "name": "Status"}]})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_columns(ctx, doc_id="d1", table_id_or_name="t1"))
        assert result["total_count"] == 1
        assert result["items"][0]["name"] == "Status"

    async def test_pagination(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_columns(ctx, doc_id="d1", table_id_or_name="t1", cursor="abc")
        params = client.get.call_args[1]["params"]
        assert params["pageToken"] == "abc"


class TestGetColumn:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "c1", "name": "Status", "type": "select"})
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_get_column(ctx, doc_id="d1", table_id_or_name="t1", column_id_or_name="c1")
        )
        assert result["type"] == "select"
