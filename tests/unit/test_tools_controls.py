"""Tests for control tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.servers.controls import coda_get_control, coda_list_controls


def _make_ctx(client_mock: AsyncMock) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok"),
        "client": client_mock,
    }
    return ctx


class TestListControls:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "ctrl1", "name": "DateFilter", "controlType": "datePicker"}]
            }
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_controls(ctx, doc_id="d1"))
        assert result["total_count"] == 1
        assert result["items"][0]["controlType"] == "datePicker"

    async def test_no_results(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_controls(ctx, doc_id="d1"))
        assert result["total_count"] == 0
        assert result["has_more"] is False


class TestGetControl:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"id": "ctrl1", "name": "DateFilter", "value": "2024-01-01"}
        )
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_get_control(ctx, doc_id="d1", control_id_or_name="DateFilter")
        )
        assert result["value"] == "2024-01-01"
