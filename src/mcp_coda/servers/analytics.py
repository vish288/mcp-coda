"""Analytics tools — doc, page, pack analytics and last-updated info."""

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import _err, _get_client, _ok


@mcp.tool(
    tags={"coda", "analytics", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_doc_analytics(
    ctx: Context,
    doc_ids: Annotated[
        list[str] | None,
        Field(description="Filter to specific doc IDs"),
    ] = None,
    is_published: Annotated[
        bool | None,
        Field(description="Filter to published (True) or unpublished (False) docs"),
    ] = None,
    since_date: Annotated[
        str | None,
        Field(description="Start date for analytics (ISO 8601, e.g. '2024-01-01')"),
    ] = None,
    until_date: Annotated[
        str | None,
        Field(description="End date for analytics (ISO 8601)"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of results (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
) -> str:
    """List analytics data for docs (views, copies, likes, sessions).

    Returns usage metrics for docs over the specified date range. Includes
    total views, unique views, copies, and other engagement metrics. Only
    available to doc owners. Use coda_get_doc_analytics_summary for aggregated
    totals instead of per-doc breakdown.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if doc_ids is not None:
            params["docIds"] = ",".join(doc_ids)
        if is_published is not None:
            params["isPublished"] = is_published
        if since_date is not None:
            params["sinceDate"] = since_date
        if until_date is not None:
            params["untilDate"] = until_date
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get("/analytics/docs", params=params)
        items = data.get("items", [])
        next_cursor = data.get("nextPageToken")
        return _ok(
            {
                "items": items,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "total_count": len(items),
            }
        )
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "analytics", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_doc_analytics_summary(
    ctx: Context,
    is_published: Annotated[
        bool | None,
        Field(description="Filter to published (True) or unpublished (False) docs"),
    ] = None,
    since_date: Annotated[
        str | None,
        Field(description="Start date for analytics (ISO 8601)"),
    ] = None,
    until_date: Annotated[
        str | None,
        Field(description="End date for analytics (ISO 8601)"),
    ] = None,
) -> str:
    """Get aggregated analytics summary across all docs.

    Returns total views, unique viewers, copies, and other metrics summed
    across all accessible docs. Use this for a high-level overview — use
    coda_list_doc_analytics for per-doc breakdown.
    """
    try:
        params: dict[str, Any] = {}
        if is_published is not None:
            params["isPublished"] = is_published
        if since_date is not None:
            params["sinceDate"] = since_date
        if until_date is not None:
            params["untilDate"] = until_date
        data = await _get_client(ctx).get("/analytics/docs/summary", params=params)
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "analytics", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_page_analytics(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to get page analytics for"),
    ],
    since_date: Annotated[
        str | None,
        Field(description="Start date for analytics (ISO 8601)"),
    ] = None,
    until_date: Annotated[
        str | None,
        Field(description="End date for analytics (ISO 8601)"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of results (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
) -> str:
    """List analytics data for pages within a doc.

    Returns per-page usage metrics (views, unique views) for the specified doc.
    Only available to doc owners. Useful for understanding which pages get the
    most traffic.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if since_date is not None:
            params["sinceDate"] = since_date
        if until_date is not None:
            params["untilDate"] = until_date
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get(f"/analytics/docs/{doc_id}/pages", params=params)
        items = data.get("items", [])
        next_cursor = data.get("nextPageToken")
        return _ok(
            {
                "items": items,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "total_count": len(items),
            }
        )
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "analytics", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_pack_analytics(
    ctx: Context,
    pack_ids: Annotated[
        list[int] | None,
        Field(description="Filter to specific pack IDs"),
    ] = None,
    is_published: Annotated[
        bool | None,
        Field(description="Filter to published (True) or unpublished (False) packs"),
    ] = None,
    since_date: Annotated[
        str | None,
        Field(description="Start date for analytics (ISO 8601)"),
    ] = None,
    until_date: Annotated[
        str | None,
        Field(description="End date for analytics (ISO 8601)"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of results (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
) -> str:
    """List analytics data for Coda packs.

    Returns usage metrics for packs including install counts, doc usage, and
    formula invocations. Only available to pack makers for their own packs.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if pack_ids is not None:
            params["packIds"] = ",".join(str(p) for p in pack_ids)
        if is_published is not None:
            params["isPublished"] = is_published
        if since_date is not None:
            params["sinceDate"] = since_date
        if until_date is not None:
            params["untilDate"] = until_date
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get("/analytics/packs", params=params)
        items = data.get("items", [])
        next_cursor = data.get("nextPageToken")
        return _ok(
            {
                "items": items,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "total_count": len(items),
            }
        )
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "analytics", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_pack_analytics_summary(
    ctx: Context,
    pack_ids: Annotated[
        list[int] | None,
        Field(description="Filter to specific pack IDs"),
    ] = None,
    is_published: Annotated[
        bool | None,
        Field(description="Filter to published (True) or unpublished (False) packs"),
    ] = None,
    since_date: Annotated[
        str | None,
        Field(description="Start date for analytics (ISO 8601)"),
    ] = None,
    until_date: Annotated[
        str | None,
        Field(description="End date for analytics (ISO 8601)"),
    ] = None,
) -> str:
    """Get aggregated analytics summary for packs.

    Returns total installs, doc usage, and formula invocations summed across
    packs. Only available to pack makers.
    """
    try:
        params: dict[str, Any] = {}
        if pack_ids is not None:
            params["packIds"] = ",".join(str(p) for p in pack_ids)
        if is_published is not None:
            params["isPublished"] = is_published
        if since_date is not None:
            params["sinceDate"] = since_date
        if until_date is not None:
            params["untilDate"] = until_date
        data = await _get_client(ctx).get("/analytics/packs/summary", params=params)
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "analytics", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_pack_formula_analytics(
    ctx: Context,
    pack_id: Annotated[
        int,
        Field(description="The pack ID to get formula analytics for"),
    ],
    since_date: Annotated[
        str | None,
        Field(description="Start date for analytics (ISO 8601)"),
    ] = None,
    until_date: Annotated[
        str | None,
        Field(description="End date for analytics (ISO 8601)"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of results (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
) -> str:
    """List analytics data for individual formulas within a pack.

    Returns per-formula invocation counts, error rates, and execution times.
    Only available to the pack maker.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if since_date is not None:
            params["sinceDate"] = since_date
        if until_date is not None:
            params["untilDate"] = until_date
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get(f"/analytics/packs/{pack_id}/formulas", params=params)
        items = data.get("items", [])
        next_cursor = data.get("nextPageToken")
        return _ok(
            {
                "items": items,
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "total_count": len(items),
            }
        )
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "analytics", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_analytics_updated(ctx: Context) -> str:
    """Get the timestamp of when analytics data was last updated.

    Returns a timestamp indicating the freshness of analytics data. Analytics
    are not real-time — they are typically updated every few hours. Check this
    before relying on analytics data for time-sensitive decisions.
    """
    try:
        data = await _get_client(ctx).get("/analytics/updated")
        return _ok(data)
    except Exception as e:
        return _err(e)
