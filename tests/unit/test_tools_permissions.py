"""Behaviour tests for permission tools the wire contract does not pin.

Happy-path passthrough, `test_error`, `test_read_only_blocked` and the
email-principal shape duplicated `test_tool_contract.py` and were removed. What
remains asserts behaviour the contract table does not cover: the domain
principal shape, the absent-by-default `suppressEmail`, the email-over-domain
precedence, and the no-principal rejection (D3: now an expected error, not a
ToolError bug).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from mcp_coda.servers.permissions import (
    coda_add_permission as _coda_add_permission,
)
from tests.conftest import _err_body, _make_ctx

# Unwrap FunctionTool → raw function (getattr handles plain functions too)
coda_add_permission = getattr(_coda_add_permission, "fn", _coda_add_permission)


class TestAddPermission:
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

    async def test_suppress_email_absent_by_default(self) -> None:
        """suppress_notification defaults False → no suppressEmail key on the wire.

        Sending suppressEmail unconditionally would silence the invite email for
        every grant, not just when the caller asked.
        """
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p5"})
        ctx = _make_ctx(client)
        await coda_add_permission(
            ctx, doc_id="d1", access="write", principal_email="user@example.com"
        )
        body = client.post.call_args[1]["json_data"]
        assert "suppressEmail" not in body

    async def test_email_wins_over_domain(self) -> None:
        """Both given → principal is the email (the if/elif precedence)."""
        client = AsyncMock()
        client.post = AsyncMock(return_value={"id": "p6"})
        ctx = _make_ctx(client)
        await coda_add_permission(
            ctx,
            doc_id="d1",
            access="write",
            principal_email="user@example.com",
            principal_domain="example.com",
        )
        body = client.post.call_args[1]["json_data"]
        assert body["principal"] == {"type": "email", "email": "user@example.com"}

    async def test_requires_a_principal(self) -> None:
        """D3: a missing principal is bad input, so it comes back as an expected
        isError result (ValueError is in the expected set) rather than a ToolError
        bug logged with a traceback. The upstream call is never made."""
        client = AsyncMock()
        ctx = _make_ctx(client)
        result = _err_body(await coda_add_permission(ctx, doc_id="d1", access="write"))
        assert "principal_email or principal_domain required" in result["error"]
        client.post.assert_not_called()
