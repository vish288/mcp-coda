"""Page tools — list, get, create, update, delete, content, export pages."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import _check_write, _err, _get_client, _ok


@mcp.tool(
    tags={"coda", "pages", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_pages(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the pages"),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of pages to return (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
) -> str:
    """List all pages in a Coda doc.

    Returns page metadata including name, ID, parent page, and icon. Pages are
    returned in their tree order. Does NOT return page content — use
    coda_get_page_content for that. Use the returned page IDs (not names) for
    all subsequent page operations.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get(f"/docs/{doc_id}/pages", params=params)
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
    tags={"coda", "pages", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_page(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the page"),
    ],
    page_id_or_name: Annotated[
        str,
        Field(description="Page ID or name (prefer ID — names are unstable)"),
    ],
) -> str:
    """Get metadata for a single page in a Coda doc.

    Returns the page's name, ID, parent, subtitle, icon, and image. Does NOT
    return the page's text content — use coda_get_page_content for that. Page
    names can change; always use page IDs for reliable access.
    """
    try:
        data = await _get_client(ctx).get(f"/docs/{doc_id}/pages/{page_id_or_name}")
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "pages", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
async def coda_create_page(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to create the page in"),
    ],
    name: Annotated[
        str,
        Field(description="Name/title for the new page"),
    ],
    parent_page_id: Annotated[
        str | None,
        Field(description="Parent page ID to nest under (omit for top-level)"),
    ] = None,
    subtitle: Annotated[
        str | None,
        Field(description="Subtitle text for the page"),
    ] = None,
    content: Annotated[
        str | None,
        Field(description="Initial page content in HTML or markdown"),
    ] = None,
    content_format: Annotated[
        Literal["html", "markdown"] | None,
        Field(description="Format of the content parameter"),
    ] = None,
) -> str:
    """Create a new page in a Coda doc.

    Creates a page with optional initial content. Returns the new page's ID and
    metadata. The page is created at the top level unless parent_page_id is
    specified. Content can be HTML or markdown — specify the format via
    content_format. Pack formulas cannot be inserted via the API.
    """
    try:
        _check_write(ctx)
        body: dict[str, Any] = {"name": name}
        if parent_page_id is not None:
            body["parentPageId"] = parent_page_id
        if subtitle is not None:
            body["subtitle"] = subtitle
        if content is not None:
            body["pageContent"] = {
                "content": content,
                "contentFormat": content_format or "html",
            }
        data = await _get_client(ctx).post(f"/docs/{doc_id}/pages", json_data=body)
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "pages", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False, "idempotentHint": True},
)
async def coda_update_page(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the page"),
    ],
    page_id_or_name: Annotated[
        str,
        Field(description="Page ID or name to update"),
    ],
    name: Annotated[
        str | None,
        Field(description="New name for the page"),
    ] = None,
    subtitle: Annotated[
        str | None,
        Field(description="New subtitle for the page"),
    ] = None,
    content: Annotated[
        str | None,
        Field(description="New page content (replaces existing content)"),
    ] = None,
    content_format: Annotated[
        Literal["html", "markdown"] | None,
        Field(description="Format of the content parameter"),
    ] = None,
    insert_mode: Annotated[
        Literal["replace", "append"] | None,
        Field(description="How to insert content: 'replace' overwrites, 'append' adds to end"),
    ] = None,
) -> str:
    """Update a page's name, subtitle, or content in a Coda doc.

    Updates page metadata and/or content. When updating content, 'replace' mode
    overwrites the entire page while 'append' adds to the end. There is no
    partial inline edit — draft full content locally first. Content format must
    match what you send (HTML or markdown). Returns the updated page metadata.
    """
    try:
        _check_write(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if subtitle is not None:
            body["subtitle"] = subtitle
        if content is not None:
            page_content: dict[str, str] = {
                "content": content,
                "contentFormat": content_format or "html",
            }
            if insert_mode is not None:
                page_content["insertionMode"] = insert_mode
            body["contentUpdate"] = page_content
        data = await _get_client(ctx).put(f"/docs/{doc_id}/pages/{page_id_or_name}", json_data=body)
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "pages", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
async def coda_delete_page(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the page"),
    ],
    page_id_or_name: Annotated[
        str,
        Field(description="Page ID or name to delete"),
    ],
) -> str:
    """Permanently delete a page from a Coda doc.

    This is irreversible — the page and all its content will be removed. Child
    pages are reparented to the deleted page's parent. Verify the page name with
    coda_get_page before calling this.
    """
    try:
        _check_write(ctx)
        await _get_client(ctx).delete(f"/docs/{doc_id}/pages/{page_id_or_name}")
        return _ok({"status": "deleted", "doc_id": doc_id, "page_id": page_id_or_name})
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "pages", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_page_content(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the page"),
    ],
    page_id_or_name: Annotated[
        str,
        Field(description="Page ID or name to read content from"),
    ],
    output_format: Annotated[
        Literal["html", "markdown"],
        Field(description="Content output format"),
    ] = "markdown",
) -> str:
    """Get the text content of a page in a Coda doc.

    Returns the page's content in the specified format (HTML or markdown).
    Markdown output may be lossy for complex Coda content (embedded objects,
    pack formulas). Use this for reading page text — use coda_get_page for
    metadata only.
    """
    try:
        data = await _get_client(ctx).get(
            f"/docs/{doc_id}/pages/{page_id_or_name}/content",
            params={"outputFormat": output_format},
        )
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "pages", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
async def coda_delete_page_content(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the page"),
    ],
    page_id_or_name: Annotated[
        str,
        Field(description="Page ID or name to clear content from"),
    ],
) -> str:
    """Delete all content from a page, leaving it blank.

    Removes the page's text content but does NOT delete the page itself. The
    page remains in the doc with its name and metadata intact. This is
    irreversible. Use coda_delete_page to remove the page entirely.
    """
    try:
        _check_write(ctx)
        await _get_client(ctx).delete(f"/docs/{doc_id}/pages/{page_id_or_name}/content")
        return _ok({"status": "content_deleted", "doc_id": doc_id, "page_id": page_id_or_name})
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "pages", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True},
)
async def coda_export_page(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the page"),
    ],
    page_id_or_name: Annotated[
        str,
        Field(description="Page ID or name to export"),
    ],
    output_format: Annotated[
        Literal["html", "markdown"],
        Field(description="Export format"),
    ] = "markdown",
) -> str:
    """Export a page's content, initiating an async export if needed.

    Starts an export job and returns the export status. For small pages, the
    content may be returned immediately. For large pages, poll the returned
    export ID until complete. Prefer coda_get_page_content for quick reads —
    use this only when you need a full export with embedded images resolved.
    """
    try:
        data = await _get_client(ctx).post(
            f"/docs/{doc_id}/pages/{page_id_or_name}/export",
            json_data={"outputFormat": output_format},
        )
        return _ok(data)
    except Exception as e:
        return _err(e)
