"""Account tools — whoami, resolve browser link, mutation status."""

from __future__ import annotations

from typing import Annotated

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import _err, _get_client, _ok


@mcp.tool(
    tags={"coda", "account", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_whoami(ctx: Context) -> str:
    """Get information about the current API token owner.

    Returns the user's name, email, and token scopes. Use this to verify
    that the API token is valid and has the expected permissions. If this
    returns an error, the token is invalid or expired.
    """
    try:
        data = await _get_client(ctx).get("/whoami")
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "account", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_resolve_browser_link(
    ctx: Context,
    url: Annotated[
        str,
        Field(description="A Coda browser URL to resolve (e.g. https://coda.io/d/...)"),
    ],
) -> str:
    """Resolve a Coda browser URL to API resource IDs.

    Converts a browser URL (e.g. from the address bar or a shared link) into
    API-compatible IDs for the doc, page, table, row, or column it points to.
    Use this as the first step when a user provides a Coda URL instead of IDs.
    Returns a type field indicating the resource kind and corresponding IDs.
    """
    try:
        data = await _get_client(ctx).get(
            "/resolveBrowserLink",
            params={"url": url},
        )
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "account", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_mutation_status(
    ctx: Context,
    request_id: Annotated[
        str,
        Field(description="The requestId returned by a write operation (202 response)"),
    ],
) -> str:
    """Check the status of an asynchronous mutation (write operation).

    Coda write operations return 202 with a requestId. Use this tool to poll
    whether the mutation has completed, is still processing, or failed. Returns
    a completed boolean and any error details. Poll every 2 seconds, up to 30
    seconds maximum.
    """
    try:
        data = await _get_client(ctx).get(f"/mutationStatus/{request_id}")
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "account", "read"},
    annotations={
        "openWorldHint": True,
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)
async def coda_rate_limit_budget(ctx: Context) -> str:
    """Check the current rate limit budget for reads and writes.

    Returns how many read and write API calls remain in the current sliding
    window (6 seconds). Coda allows 100 reads/6s and 10 writes/6s. Use this
    before batch operations to avoid hitting 429 errors. The budget is tracked
    locally — it resets if the server restarts.
    """
    try:
        budget = _get_client(ctx).budget.remaining()
        return _ok(budget)
    except Exception as e:
        return _err(e)
