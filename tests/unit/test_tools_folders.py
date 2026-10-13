"""Behaviour tests for folder tools the wire contract does not pin.

Happy-path passthrough, `test_error` and `test_read_only_blocked` duplicated
`test_tool_contract.py` and were removed. What remains asserts the pagination
envelope (CO-R05) and the no-op short-circuit, neither of which the contract
table covers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from mcp_coda.servers.folders import (
    coda_list_folders as _coda_list_folders,
)
from mcp_coda.servers.folders import (
    coda_update_folder as _coda_update_folder,
)
from tests.conftest import _body, _make_ctx

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_list_folders = getattr(_coda_list_folders, "fn", _coda_list_folders)
coda_update_folder = getattr(_coda_update_folder, "fn", _coda_update_folder)


class TestListFolders:
    async def test_paginates(self) -> None:
        # CO-R05: /folders defaults to 25 per page with a nextPageToken. The
        # tool must surface the cursor instead of pretending the list is whole.
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [{"id": "fl1"}], "nextPageToken": "tok2"})
        ctx = _make_ctx(client)
        result = _body(await coda_list_folders(ctx, limit=25, cursor="tok1"))
        assert result["has_more"] is True
        assert result["next_cursor"] == "tok2"
        params = client.get.call_args[1]["params"]
        assert params["limit"] == 25
        assert params["pageToken"] == "tok1"


class TestUpdateFolder:
    async def test_no_op_when_nothing_to_update(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client)
        result = _body(await coda_update_folder(ctx, folder_id="fl1"))
        assert result == {"unchanged": True, "folder_id": "fl1"}
        client.patch.assert_not_called()
