"""Tests for the misc tools — automations, formulas, controls, publishing."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from mcp_coda.exceptions import CodaApiError
from mcp_coda.servers.misc import (
    coda_get_control as _coda_get_control,
)
from mcp_coda.servers.misc import (
    coda_get_formula as _coda_get_formula,
)
from mcp_coda.servers.misc import (
    coda_list_categories as _coda_list_categories,
)
from mcp_coda.servers.misc import (
    coda_list_controls as _coda_list_controls,
)
from mcp_coda.servers.misc import (
    coda_list_formulas as _coda_list_formulas,
)
from mcp_coda.servers.misc import (
    coda_publish_doc as _coda_publish_doc,
)
from mcp_coda.servers.misc import (
    coda_trigger_automation as _coda_trigger_automation,
)
from mcp_coda.servers.misc import (
    coda_unpublish_doc as _coda_unpublish_doc,
)
from tests.conftest import _make_ctx

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_trigger_automation = getattr(_coda_trigger_automation, "fn", _coda_trigger_automation)
coda_list_formulas = getattr(_coda_list_formulas, "fn", _coda_list_formulas)
coda_get_formula = getattr(_coda_get_formula, "fn", _coda_get_formula)
coda_list_controls = getattr(_coda_list_controls, "fn", _coda_list_controls)
coda_get_control = getattr(_coda_get_control, "fn", _coda_get_control)
coda_list_categories = getattr(_coda_list_categories, "fn", _coda_list_categories)
coda_publish_doc = getattr(_coda_publish_doc, "fn", _coda_publish_doc)
coda_unpublish_doc = getattr(_coda_unpublish_doc, "fn", _coda_unpublish_doc)


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
        assert body == {"key": "value"}

    async def test_without_payload(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"requestId": "req1"})
        ctx = _make_ctx(client)
        await coda_trigger_automation(ctx, doc_id="d1", rule_id="r1")
        body = client.post.call_args[1]["json_data"]
        assert body == {}

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_trigger_automation(ctx, doc_id="d1", rule_id="r1"))
        assert result["isError"] is True
        assert "CODA_READ_ONLY" in result["error"]


class TestListFormulas:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"items": [{"id": "f1", "name": "TotalBudget", "value": 5000}]}
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_formulas(ctx, doc_id="d1"))
        assert result["total_count"] == 1
        assert result["items"][0]["value"] == 5000

    async def test_pagination(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [], "nextPageToken": "next"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_formulas(ctx, doc_id="d1"))
        assert result["has_more"] is True

    async def test_with_cursor(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_formulas(ctx, doc_id="d1", cursor="c1")
        params = client.get.call_args[1]["params"]
        assert params["pageToken"] == "c1"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_formulas(ctx, doc_id="bad"))
        assert result["isError"] is True


class TestGetFormula:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "f1", "name": "TotalBudget", "value": 5000})
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_get_formula(ctx, doc_id="d1", formula_id_or_name="TotalBudget")
        )
        assert result["name"] == "TotalBudget"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no formula"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_formula(ctx, doc_id="d1", formula_id_or_name="bad"))
        assert result["isError"] is True


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


class TestListCategories:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"items": [{"name": "Project Management"}, {"name": "Education"}]}
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_categories(ctx))
        assert result["total_count"] == 2

    async def test_empty(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_categories(ctx))
        assert result["total_count"] == 0

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(500, "ISE", "fail"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_categories(ctx))
        assert result["isError"] is True


class TestPublishDoc:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={"browserLink": "https://coda.io/@user/my-doc"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_publish_doc(ctx, doc_id="d1"))
        assert "browserLink" in result

    async def test_with_slug_and_categories(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={})
        ctx = _make_ctx(client)
        await coda_publish_doc(ctx, doc_id="d1", slug="my-doc", category_names=["cat1", "cat2"])
        body = client.put.call_args[1]["json_data"]
        assert body["slug"] == "my-doc"
        assert body["categoryNames"] == ["cat1", "cat2"]

    async def test_with_mode(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(return_value={})
        ctx = _make_ctx(client)
        await coda_publish_doc(ctx, doc_id="d1", mode="view")
        body = client.put.call_args[1]["json_data"]
        assert body["mode"] == "view"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.put = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_publish_doc(ctx, doc_id="bad"))
        assert result["isError"] is True

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_publish_doc(ctx, doc_id="d1"))
        assert result["isError"] is True


class TestUnpublishDoc:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = json.loads(await coda_unpublish_doc(ctx, doc_id="d1"))
        assert result["status"] == "unpublished"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_unpublish_doc(ctx, doc_id="d1"))
        assert result["isError"] is True
