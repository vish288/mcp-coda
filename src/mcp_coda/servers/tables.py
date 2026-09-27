"""Table and column tools — list/get tables and columns."""

from typing import Annotated, Literal

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import Cursor, DocId, _get_client, _ok, _page, tool_result


@mcp.tool(
    tags={"coda", "tables", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
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
    cursor: Cursor = None,
) -> str:
    """List all tables and views in a Coda doc.

    Returns table metadata including name, ID, type (table or view), row count,
    and parent page. Does NOT return row data — use coda_list_rows for that.
    Use coda_list_columns to get the column schema of a specific table.
    """
    params = {"limit": limit, "tableTypes": table_types, "pageToken": cursor}
    return _page(await _get_client(ctx).get(f"/docs/{doc_id}/tables", params=params))


@mcp.tool(
    tags={"coda", "tables", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_get_table(
    ctx: Context,
    doc_id: DocId,
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
    return _ok(await _get_client(ctx).get(f"/docs/{doc_id}/tables/{table_id_or_name}"))


@mcp.tool(
    tags={"coda", "tables", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_list_columns(
    ctx: Context,
    doc_id: DocId,
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name to list columns from"),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of columns to return (1-200)", ge=1, le=200),
    ] = 100,
    cursor: Cursor = None,
) -> str:
    """List all columns in a Coda table.

    Returns column metadata including name, ID, type (text, number, date, etc.),
    and configuration. Column IDs are internal identifiers — use column names
    when working with row data. This is the table schema — call this before
    inserting or updating rows to know the available columns and their types.
    """
    params = {"limit": limit, "pageToken": cursor}
    return _page(
        await _get_client(ctx).get(
            f"/docs/{doc_id}/tables/{table_id_or_name}/columns",
            params=params,
        )
    )


@mcp.tool(
    tags={"coda", "tables", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_get_column(
    ctx: Context,
    doc_id: DocId,
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
    return _ok(
        await _get_client(ctx).get(
            f"/docs/{doc_id}/tables/{table_id_or_name}/columns/{column_id_or_name}"
        )
    )
