"""Tests for MCP resources."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.servers.resources import doc_schema_resource, docs_resource


def _make_ctx(client_mock: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok"),
        "client": client_mock,
    }
    return ctx


class TestDocsResource:
    async def test_returns_doc_list(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [
                    {
                        "id": "d1",
                        "name": "My Doc",
                        "owner": "user@example.com",
                        "browserLink": "https://coda.io/d/d1",
                        "updatedAt": "2024-01-01",
                    }
                ]
            }
        )
        ctx = _make_ctx(client)
        result = json.loads(await docs_resource(ctx))
        assert len(result) == 1
        assert result[0]["id"] == "d1"
        assert result[0]["name"] == "My Doc"

    async def test_error_handling(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=Exception("connection failed"))
        ctx = _make_ctx(client)
        result = json.loads(await docs_resource(ctx))
        assert "error" in result


class TestDocSchemaResource:
    async def test_returns_schema(self) -> None:
        client = AsyncMock()
        # First call: list tables
        # Second call: list columns for table t1
        client.get = AsyncMock(
            side_effect=[
                {"items": [{"id": "t1", "name": "Tasks", "tableType": "table", "rowCount": 10}]},
                {
                    "items": [
                        {
                            "id": "c1",
                            "name": "Status",
                            "format": {"type": "select"},
                            "calculated": False,
                            "display": True,
                        }
                    ]
                },
            ]
        )
        ctx = _make_ctx(client)
        result = json.loads(await doc_schema_resource("d1", ctx))
        assert len(result) == 1
        assert result[0]["name"] == "Tasks"
        assert result[0]["columns"][0]["name"] == "Status"
        assert result[0]["columns"][0]["type"] == "select"

    async def test_error_handling(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=Exception("not found"))
        ctx = _make_ctx(client)
        result = json.loads(await doc_schema_resource("bad_id", ctx))
        assert "error" in result
