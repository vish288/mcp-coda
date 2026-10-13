"""Behaviour tests for the misc tools (automations/formulas/controls/publishing)
the wire contract does not pin.

Happy-path passthrough, `test_error`, `test_read_only_blocked` and simple
param-echo tests duplicated `test_tool_contract.py` and were removed. What
remains asserts behaviour the contract table does not cover: the empty-payload
default for `coda_trigger_automation`, the empty-list envelope for
`coda_list_categories`, and the publish defaults / enum rejection (CO-R23).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import respx
from fastmcp import Client

from mcp_coda.servers.misc import (
    coda_list_categories as _coda_list_categories,
)
from mcp_coda.servers.misc import (
    coda_publish_doc as _coda_publish_doc,
)
from mcp_coda.servers.misc import (
    coda_trigger_automation as _coda_trigger_automation,
)
from tests.conftest import _body, _make_ctx

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_trigger_automation = getattr(_coda_trigger_automation, "fn", _coda_trigger_automation)
coda_list_categories = getattr(_coda_list_categories, "fn", _coda_list_categories)
coda_publish_doc = getattr(_coda_publish_doc, "fn", _coda_publish_doc)


class TestTriggerAutomation:
    async def test_without_payload(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"requestId": "req1"})
        ctx = _make_ctx(client)
        await coda_trigger_automation(ctx, doc_id="d1", rule_id="r1")
        body = client.post.call_args[1]["json_data"]
        assert body == {}


class TestListCategories:
    async def test_empty(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        result = _body(await coda_list_categories(ctx))
        assert result["total_count"] == 0


class TestPublishDoc:
    async def test_default_is_unlisted(self) -> None:
        """CO-R23: publishing alone no longer lists the doc in the public gallery."""
        client = AsyncMock()
        client.put = AsyncMock(return_value={})
        ctx = _make_ctx(client)
        await coda_publish_doc(ctx, doc_id="d1")
        body = client.put.call_args[1]["json_data"]
        assert body["discoverable"] is False

    async def test_mode_rejects_unknown(self, tool_client: tuple[Client, respx.MockRouter]) -> None:
        """CO-R23: mode is the view/play/edit enum. The .fn path bypasses pydantic,
        so this goes through the real server where validation runs."""
        client, router = tool_client
        result = await client.call_tool(
            "coda_publish_doc", {"doc_id": "d1", "mode": "banana"}, raise_on_error=False
        )
        assert result.is_error is True
        # A pydantic Literal rejection names the allowed values; a bare-str default
        # would have let "banana" through to an (unmocked) HTTP call instead.
        assert "view" in result.content[0].text
        assert not router.calls
