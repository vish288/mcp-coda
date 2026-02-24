"""Tests for control tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaApiError
from mcp_coda.servers.controls import (
    coda_get_control as _coda_get_control,
)
from mcp_coda.servers.controls import (
    coda_list_controls as _coda_list_controls,
)

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_get_control = getattr(_coda_get_control, "fn", _coda_get_control)
coda_list_controls = getattr(_coda_list_controls, "fn", _coda_list_controls)


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

    async def test_with_cursor(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_controls(ctx, doc_id="d1", cursor="abc")
        params = client.get.call_args[1]["params"]
        assert params["pageToken"] == "abc"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_controls(ctx, doc_id="bad"))
        assert result["isError"] is True


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

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no control"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_control(ctx, doc_id="d1", control_id_or_name="bad"))
        assert result["isError"] is True
