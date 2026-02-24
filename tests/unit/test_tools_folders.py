"""Tests for folder tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.servers.folders import (
    coda_create_folder as _coda_create_folder,
    coda_delete_folder as _coda_delete_folder,
    coda_get_folder as _coda_get_folder,
    coda_list_folders as _coda_list_folders,
    coda_update_folder as _coda_update_folder,
)

# Unwrap FunctionTool objects to get the raw async functions
coda_create_folder = _coda_create_folder.fn
coda_delete_folder = _coda_delete_folder.fn
coda_get_folder = _coda_get_folder.fn
coda_list_folders = _coda_list_folders.fn
coda_update_folder = _coda_update_folder.fn


def _make_ctx(client_mock: AsyncMock, read_only: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok", read_only=read_only),
        "client": client_mock,
    }
    return ctx


class TestListFolders:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": [{"id": "fl1", "name": "Projects"}]})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_folders(ctx))
        assert result["total_count"] == 1
        assert result["items"][0]["name"] == "Projects"


class TestGetFolder:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"id": "fl1", "name": "Projects"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_folder(ctx, folder_id="fl1"))
        assert result["name"] == "Projects"


class TestCreateFolder:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "fl2", "name": "New Folder"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_create_folder(ctx, name="New Folder"))
        assert result["id"] == "fl2"

    async def test_with_parent(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "fl3"})
        ctx = _make_ctx(client)
        await coda_create_folder(ctx, name="Sub", parent_folder_id="fl1")
        body = client.post.call_args[1]["json_data"]
        assert body["parentFolderId"] == "fl1"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_create_folder(ctx, name="Blocked"))
        assert result["isError"] is True


class TestUpdateFolder:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.patch = AsyncMock(return_value={"id": "fl1", "name": "Renamed"})
        ctx = _make_ctx(client)
        result = json.loads(await coda_update_folder(ctx, folder_id="fl1", name="Renamed"))
        assert result["name"] == "Renamed"


class TestDeleteFolder:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = json.loads(await coda_delete_folder(ctx, folder_id="fl1"))
        assert result["status"] == "deleted"
        assert result["folder_id"] == "fl1"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_delete_folder(ctx, folder_id="fl1"))
        assert result["isError"] is True
