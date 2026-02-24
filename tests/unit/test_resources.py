"""Tests for MCP resources."""

from __future__ import annotations

import json
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig


def _get_raw_resource_fn(name: str):
    """Import the resource module and extract the raw async function before decoration.

    The @mcp.resource decorator wraps functions in FunctionResource, which then
    wraps them with without_injected_parameters (stripping ctx). To test the actual
    logic, we need the original unwrapped function that accepts (ctx) or (doc_id, ctx).
    """
    import importlib

    # Temporarily remove the module from cache to re-import fresh
    mod_name = "mcp_coda.servers.resources"
    saved = sys.modules.pop(mod_name, None)

    # Create a mock mcp module that captures the decorated function without wrapping
    captured = {}

    class MockMCP:
        def resource(self, *args, **kwargs):
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn
            return decorator

    # Temporarily replace the mcp instance in the servers package
    import mcp_coda.servers as servers_pkg
    original_mcp = servers_pkg.mcp

    servers_pkg.mcp = MockMCP()
    try:
        # Force re-import with our mock
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        mod = importlib.import_module(mod_name)
    finally:
        # Restore original mcp
        servers_pkg.mcp = original_mcp
        # Restore original module in cache
        if saved is not None:
            sys.modules[mod_name] = saved
        elif mod_name in sys.modules:
            del sys.modules[mod_name]

    return captured[name]


# Get raw undecorated functions for testing
docs_resource = _get_raw_resource_fn("docs_resource")
doc_schema_resource = _get_raw_resource_fn("doc_schema_resource")


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
