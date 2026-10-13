"""Behaviour tests for doc tools the wire contract does not pin.

Happy-path passthrough, `test_error` and `test_read_only_blocked` here only
re-exercised `test_tool_contract.py`'s per-tool rows (request shape,
`test_forced_failure`, `test_read_only_blocks_write`), so they were removed.
What remains asserts response shaping the contract table does not: the markdown
branch and the no-op short-circuit.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from mcp_coda.servers.docs import (
    coda_list_docs as _coda_list_docs,
)
from mcp_coda.servers.docs import (
    coda_update_doc as _coda_update_doc,
)
from tests.conftest import _body, _make_ctx, _md

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_list_docs = getattr(_coda_list_docs, "fn", _coda_list_docs)
coda_update_doc = getattr(_coda_update_doc, "fn", _coda_update_doc)


class TestListDocs:
    async def test_markdown_format(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "d1", "name": "My Doc"}],
                "nextPageToken": None,
            }
        )
        ctx = _make_ctx(client)
        result = _md(await coda_list_docs(ctx, response_format="markdown"))
        assert "**My Doc**" in result
        assert "1 items returned" in result


class TestUpdateDoc:
    async def test_no_op_when_nothing_to_update(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client)
        result = _body(await coda_update_doc(ctx, doc_id="d1"))
        assert result == {"unchanged": True, "doc_id": "d1"}
        client.patch.assert_not_called()
