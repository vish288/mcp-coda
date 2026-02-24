"""Tests for permission tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import CodaApiError
from mcp_coda.servers.permissions import (
    coda_add_permission as _coda_add_permission,
)
from mcp_coda.servers.permissions import (
    coda_delete_permission as _coda_delete_permission,
)
from mcp_coda.servers.permissions import (
    coda_get_acl_settings as _coda_get_acl_settings,
)
from mcp_coda.servers.permissions import (
    coda_get_sharing_metadata as _coda_get_sharing_metadata,
)
from mcp_coda.servers.permissions import (
    coda_list_permissions as _coda_list_permissions,
)
from mcp_coda.servers.permissions import (
    coda_search_principals as _coda_search_principals,
)

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_add_permission = getattr(_coda_add_permission, "fn", _coda_add_permission)
coda_delete_permission = getattr(_coda_delete_permission, "fn", _coda_delete_permission)
coda_get_acl_settings = getattr(_coda_get_acl_settings, "fn", _coda_get_acl_settings)
coda_get_sharing_metadata = getattr(_coda_get_sharing_metadata, "fn", _coda_get_sharing_metadata)
coda_list_permissions = getattr(_coda_list_permissions, "fn", _coda_list_permissions)
coda_search_principals = getattr(_coda_search_principals, "fn", _coda_search_principals)


def _make_ctx(client_mock: AsyncMock, read_only: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok", read_only=read_only),
        "client": client_mock,
    }
    return ctx


class TestGetSharingMetadata:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"canShare": True, "canShareWithOrg": False})
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_sharing_metadata(ctx, doc_id="d1"))
        assert result["canShare"] is True

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_sharing_metadata(ctx, doc_id="bad"))
        assert result["isError"] is True


class TestListPermissions:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"id": "p1", "access": "write"}],
                "nextPageToken": "cur2",
            }
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_permissions(ctx, doc_id="d1"))
        assert result["total_count"] == 1
        assert result["has_more"] is True

    async def test_no_more_pages(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_permissions(ctx, doc_id="d1"))
        assert result["has_more"] is False

    async def test_with_cursor(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(return_value={"items": []})
        ctx = _make_ctx(client)
        await coda_list_permissions(ctx, doc_id="d1", cursor="abc")
        params = client.get.call_args[1]["params"]
        assert params["pageToken"] == "abc"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_list_permissions(ctx, doc_id="bad"))
        assert result["isError"] is True


class TestAddPermission:
    async def test_success_with_email(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p2", "access": "write"})
        ctx = _make_ctx(client)
        result = json.loads(
            await coda_add_permission(
                ctx, doc_id="d1", access="write", principal_email="user@example.com"
            )
        )
        assert result["access"] == "write"
        body = client.post.call_args[1]["json_data"]
        assert body["principal"]["email"] == "user@example.com"
        assert body["principal"]["type"] == "email"

    async def test_success_with_domain(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p3"})
        ctx = _make_ctx(client)
        await coda_add_permission(
            ctx, doc_id="d1", access="readonly", principal_domain="example.com"
        )
        body = client.post.call_args[1]["json_data"]
        assert body["principal"]["domain"] == "example.com"
        assert body["principal"]["type"] == "domain"

    async def test_suppress_notification(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p4"})
        ctx = _make_ctx(client)
        await coda_add_permission(
            ctx,
            doc_id="d1",
            access="write",
            principal_email="user@example.com",
            suppress_notification=True,
        )
        body = client.post.call_args[1]["json_data"]
        assert body["suppressNotification"] is True

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_add_permission(ctx, doc_id="d1", access="write"))
        assert result["isError"] is True
        assert "CODA_READ_ONLY" in result["error"]


class TestDeletePermission:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.delete = AsyncMock(return_value=None)
        ctx = _make_ctx(client)
        result = json.loads(await coda_delete_permission(ctx, doc_id="d1", permission_id="p1"))
        assert result["status"] == "deleted"
        assert result["permission_id"] == "p1"

    async def test_read_only_blocked(self) -> None:
        client = AsyncMock()
        ctx = _make_ctx(client, read_only=True)
        result = json.loads(await coda_delete_permission(ctx, doc_id="d1", permission_id="p1"))
        assert result["isError"] is True


class TestSearchPrincipals:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"items": [{"type": "email", "email": "user@example.com"}]}
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_search_principals(ctx, doc_id="d1", query="user"))
        assert result["items"][0]["email"] == "user@example.com"

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_search_principals(ctx, doc_id="bad", query="x"))
        assert result["isError"] is True


class TestGetAclSettings:
    async def test_success(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(
            return_value={"allowEditorsToChangePermissions": True, "allowCopying": False}
        )
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_acl_settings(ctx, doc_id="d1"))
        assert result["allowEditorsToChangePermissions"] is True

    async def test_error(self) -> None:
        client = AsyncMock()
        client.get = AsyncMock(side_effect=CodaApiError(404, "Not Found", "no doc"))
        ctx = _make_ctx(client)
        result = json.loads(await coda_get_acl_settings(ctx, doc_id="bad"))
        assert result["isError"] is True
