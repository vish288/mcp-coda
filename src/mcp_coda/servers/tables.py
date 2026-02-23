"""Table and column tools — list/get tables and columns."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import _err, _get_client, _ok


@mcp.tool(
    tags={"coda", "tables", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_tables(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to list tables from"),
    ],
    table_types: Annotated[
        Literal["table", "view"] | None,
        Field(description="Filter by type: 'table' for base tables, 'view' for views"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of tables to return (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
) -> str:
    """List all tables and views in a Coda doc.

    Returns table metadata including name, ID, type (table or view), row count,
    and parent page. Does NOT return row data — use coda_list_rows for that.
    Use coda_list_columns to get the column schema of a specific table.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if table_types is not None:
            params["tableTypes"] = table_types
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get(f"/docs/{doc_id}/tables", params=params)
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
    tags={"coda", "tables", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_table(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the table"),
    ],
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name"),
    ],
) -> str:
    """Get metadata for a single table or view in a Coda doc.

    Returns the table's name, ID, type, row count, parent page, and sort/filter
    info. Does NOT return row data or column definitions — use coda_list_rows
    and coda_list_columns for those.
    """
    try:
        data = await _get_client(ctx).get(f"/docs/{doc_id}/tables/{table_id_or_name}")
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "tables", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_columns(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the table"),
    ],
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name to list columns from"),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of columns to return (1-200)", ge=1, le=200),
    ] = 100,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
) -> str:
    """List all columns in a Coda table.

    Returns column metadata including name, ID, type (text, number, date, etc.),
    and configuration. Column IDs are internal identifiers — use column names
    when working with row data. This is the table schema — call this before
    inserting or updating rows to know the available columns and their types.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get(
            f"/docs/{doc_id}/tables/{table_id_or_name}/columns",
            params=params,
        )
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
    tags={"coda", "tables", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_column(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the table"),
    ],
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name"),
    ],
    column_id_or_name: Annotated[
        str,
        Field(description="Column ID or name"),
    ],
) -> str:
    """Get metadata for a single column in a Coda table.

    Returns the column's name, ID, type, format, and configuration details.
    Use this to check a specific column's type before writing data to it.
    For the full column schema, use coda_list_columns instead.
    """
    try:
        data = await _get_client(ctx).get(
            f"/docs/{doc_id}/tables/{table_id_or_name}/columns/{column_id_or_name}"
        )
        return _ok(data)
    except Exception as e:
        return _err(e)
