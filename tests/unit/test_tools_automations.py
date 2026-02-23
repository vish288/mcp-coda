"""Tests for automation tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.servers.automations import coda_trigger_automation


def _make_ctx(client_mock: AsyncMock, read_only: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok", read_only=read_only),
        "client": client_mock,
    }
    return ctx


class TestTriggerAutomation:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"requestId": "req1"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_trigger_automation(ctx, doc_id="d1", rule_id="r1"))
        assert result["requestId"] == "req1"

    async def test_with_payload(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"requestId": "req1"})
        ctx = _make_ctx(client)
        await coda_trigger_automation(ctx, doc_id="d1", rule_id="r1", payload={"key": "value"})
        body = client.post.call_args[1]["json_data"]
        assert body["message"] == {"key": "value"}

    async def test_without_payload(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"requestId": "req1"})
        ctx = _make_ctx(client)
        await coda_trigger_automation(ctx, doc_id="d1", rule_id="r1")
        body = client.post.call_args[1]["json_data"]
        assert "message" not in body

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_trigger_automation(ctx, doc_id="d1", rule_id="r1"))
        assert result["isError"] is True
        assert "CODA_READ_ONLY" in result["error"]
