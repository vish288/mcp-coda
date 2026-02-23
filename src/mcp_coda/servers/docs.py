"""Doc tools — list, get, create, update, delete docs."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import (
    _check_write,
    _err,
    _format_list_as_markdown,
    _get_client,
    _ok,
    _ok_markdown,
)


@mcp.tool(
    tags={"coda", "docs", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_docs(
    ctx: Context,
    query: Annotated[
        str | None,
        Field(description="Search query to filter docs by name"),
    ] = None,
    is_owner: Annotated[
        bool | None,
        Field(description="Filter to docs owned by the API token owner"),
    ] = None,
    folder_id: Annotated[
        str | None,
        Field(description="Filter to docs in a specific folder"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of docs to return (1-200)", ge=1, le=200),
    ] = 25,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
    response_format: Annotated[
        Literal["json", "markdown"],
        Field(description="'json' for structured data, 'markdown' for readable text"),
    ] = "json",
) -> str:
    """List Coda docs accessible to the current API token.

    Returns doc metadata including name, owner, folder, and timestamps. Does NOT
    return page content or table data — use coda_list_pages or coda_list_tables
    for those. Rate-limited to 4 calls per 6 seconds. Use the query parameter to
    search by doc name. Pass cursor to paginate through results.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if query is not None:
            params["query"] = query
        if is_owner is not None:
            params["isOwner"] = is_owner
        if folder_id is not None:
            params["folderId"] = folder_id
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get("/docs", params=params)
        items = data.get("items", [])
        next_cursor = data.get("nextPageToken")
        has_more = next_cursor is not None
        total_count = len(items)
        if response_format == "markdown":
            return _ok_markdown(
                _format_list_as_markdown(
                    items,
                    has_more=has_more,
                    next_cursor=next_cursor,
                    total_count=total_count,
                )
            )
        return _ok(
            {
                "items": items,
                "has_more": has_more,
                "next_cursor": next_cursor,
                "total_count": total_count,
            }
        )
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "docs", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_doc(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The ID of the doc (from coda_list_docs or coda_resolve_browser_link)"),
    ],
) -> str:
    """Get metadata for a single Coda doc by ID.

    Returns name, owner email, folder, created/updated timestamps, and doc size.
    Does NOT return page content or table data — use coda_list_pages or
    coda_list_tables for those. The doc_id can be obtained from coda_list_docs
    or coda_resolve_browser_link.
    """
    try:
        data = await _get_client(ctx).get(f"/docs/{doc_id}")
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "docs", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
async def coda_create_doc(
    ctx: Context,
    title: Annotated[
        str,
        Field(description="Title for the new doc"),
    ],
    folder_id: Annotated[
        str | None,
        Field(description="Folder ID to create the doc in (omit for root)"),
    ] = None,
    source_doc: Annotated[
        str | None,
        Field(description="Doc ID to copy as a starting point"),
    ] = None,
) -> str:
    """Create a new Coda doc.

    Creates a blank doc or a copy of an existing doc. Returns the new doc's ID,
    name, and browser URL. The doc is created in the specified folder, or the
    user's root if no folder is given. Use source_doc to clone an existing doc
    as a template.
    """
    try:
        _check_write(ctx)
        body: dict[str, Any] = {"title": title}
        if folder_id is not None:
            body["folderId"] = folder_id
        if source_doc is not None:
            body["sourceDoc"] = source_doc
        data = await _get_client(ctx).post("/docs", json_data=body)
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "docs", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False, "idempotentHint": True},
)
async def coda_update_doc(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The ID of the doc to update"),
    ],
    title: Annotated[
        str | None,
        Field(description="New title for the doc"),
    ] = None,
    icon_name: Annotated[
        str | None,
        Field(description="New icon name (e.g. 'rocket', 'star')"),
    ] = None,
) -> str:
    """Update metadata for an existing Coda doc.

    Updates the doc's title and/or icon. Does NOT update page content — use
    coda_update_page for that. Returns the updated doc metadata. This is an
    idempotent operation — calling with the same values produces the same result.
    """
    try:
        _check_write(ctx)
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if icon_name is not None:
            body["icon"] = {"name": icon_name, "type": "name"}
        data = await _get_client(ctx).patch(f"/docs/{doc_id}", json_data=body)
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "docs", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
async def coda_delete_doc(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The ID of the doc to delete"),
    ],
) -> str:
    """Permanently delete a Coda doc.

    This is irreversible — the doc and all its pages, tables, and data will be
    permanently removed. Verify the doc name with coda_get_doc before calling
    this. Returns a confirmation status.
    """
    try:
        _check_write(ctx)
        await _get_client(ctx).delete(f"/docs/{doc_id}")
        return _ok({"status": "deleted", "doc_id": doc_id})
    except Exception as e:
        return _err(e)
