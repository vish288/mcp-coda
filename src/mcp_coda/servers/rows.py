"""Row tools — list, get, insert, update, delete rows, push button."""

from typing import Annotated, Any, Literal

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import (
    Cursor,
    DocId,
    _get_client,
    _list_footer,
    _ok,
    _p,
    _page,
    _truncate,
    tool_result,
)


@mcp.tool(
    tags={"coda", "rows", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_list_rows(
    ctx: Context,
    doc_id: DocId,
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name to list rows from"),
    ],
    query: Annotated[
        str | None,
        Field(description="Filter formula (e.g. 'Status:\"Active\"' or 'c-abc123:\"value\"')"),
    ] = None,
    sort_by: Annotated[
        Literal["createdAt", "natural", "updatedAt"] | None,
        Field(
            description=(
                "Row sort order. One of 'createdAt', 'natural' (the table's own "
                "order), or 'updatedAt'. The API does not sort by an arbitrary column."
            )
        ),
    ] = None,
    use_column_names: Annotated[
        bool,
        Field(description="Use column names (True) or IDs (False) in row values"),
    ] = True,
    limit: Annotated[
        int,
        Field(description="Maximum number of rows to return (1-500)", ge=1, le=500),
    ] = 50,
    cursor: Cursor = None,
    response_format: Annotated[
        Literal["json", "markdown"],
        Field(description="'json' for structured data, 'markdown' for readable text"),
    ] = "json",
) -> str:
    """List rows in a Coda table with optional filtering and sorting.

    Returns row data with column values. By default uses column names (not IDs)
    for readability. Use the query parameter to filter rows by column values.
    For a specific row by ID, use coda_get_row instead. Results are paginated —
    pass cursor to get the next page.
    """
    params = {
        "limit": limit,
        "useColumnNames": use_column_names,
        "query": query,
        "sortBy": sort_by,
        "pageToken": cursor,
    }
    data = await _get_client(ctx).get(
        _p("docs", doc_id, "tables", table_id_or_name, "rows"),
        params=params,
    )
    items = data.get("items", [])
    next_cursor = data.get("nextPageToken")
    has_more = next_cursor is not None
    total_count = len(items)
    if response_format == "markdown":
        lines: list[str] = []
        for row in items:
            values = row.get("values", {})
            row_name = row.get("name", row.get("id", ""))
            cells = " | ".join(f"**{k}**: {v}" for k, v in values.items())
            lines.append(f"- {row_name}: {cells}")
        if not lines:
            lines.append("*No rows found.*")
        footer = _list_footer(total_count, has_more, next_cursor, noun="rows")
        return _truncate("\n".join(lines) + footer)
    return _page(data)


@mcp.tool(
    tags={"coda", "rows", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_get_row(
    ctx: Context,
    doc_id: DocId,
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name"),
    ],
    row_id_or_name: Annotated[
        str,
        Field(description="Row ID or name (display column value)"),
    ],
    use_column_names: Annotated[
        bool,
        Field(description="Use column names (True) or IDs (False) in row values"),
    ] = True,
) -> str:
    """Get a single row from a Coda table by ID or display column value.

    Returns all column values for the specified row. Use this when you have a
    specific row ID or know the display column value. For querying multiple
    rows with filters, use coda_list_rows instead.
    """
    params: dict[str, Any] = {"useColumnNames": use_column_names}
    return _ok(
        await _get_client(ctx).get(
            _p("docs", doc_id, "tables", table_id_or_name, "rows", row_id_or_name),
            params=params,
        )
    )


@mcp.tool(
    tags={"coda", "rows", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_insert_rows(
    ctx: Context,
    doc_id: DocId,
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name to insert rows into"),
    ],
    rows: Annotated[
        list[dict[str, Any]],
        Field(
            description=(
                "List of rows to insert. Each row is a dict with 'cells' key "
                "containing a list of {column: name, value: val} objects. "
                "Example: [{'cells': [{'column': 'Name', 'value': 'Alice'}]}]"
            )
        ),
    ],
    key_columns: Annotated[
        list[str] | None,
        Field(
            description=(
                "Column names to use as upsert keys. If a row matches on these "
                "columns, it is updated instead of inserted. Omit for pure insert."
            )
        ),
    ] = None,
) -> str:
    """Insert one or more rows into a Coda table, with optional upsert.

    Inserts up to 500 rows per call. Use column names (not IDs) in the cells.
    With key_columns, matching rows are updated (upsert) instead of inserted —
    this is the only way to bulk-update rows. Returns a requestId for async
    mutation tracking via coda_get_mutation_status. The operation is async (202).
    """
    body: dict[str, Any] = {"rows": rows}
    if key_columns is not None:
        body["keyColumns"] = key_columns
    return _ok(
        await _get_client(ctx).post(
            _p("docs", doc_id, "tables", table_id_or_name, "rows"),
            json_data=body,
        )
    )


@mcp.tool(
    tags={"coda", "rows", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False, "idempotentHint": True},
)
@tool_result(write=True)
async def coda_update_row(
    ctx: Context,
    doc_id: DocId,
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name"),
    ],
    row_id_or_name: Annotated[
        str,
        Field(description="Row ID or name to update"),
    ],
    cells: Annotated[
        list[dict[str, Any]],
        Field(
            description=(
                "Column values to update. List of {column: name, value: val} objects. "
                "Example: [{'column': 'Status', 'value': 'Done'}]"
            )
        ),
    ],
) -> str:
    """Update a single row in a Coda table.

    Updates specific column values for one row. Only the specified columns are
    changed — other columns are left unchanged. Use column names (not IDs).
    For bulk updates, use coda_insert_rows with key_columns (upsert) instead.
    Returns a requestId for async mutation tracking.
    """
    body: dict[str, Any] = {"row": {"cells": cells}}
    return _ok(
        await _get_client(ctx).put(
            _p("docs", doc_id, "tables", table_id_or_name, "rows", row_id_or_name),
            json_data=body,
        )
    )


@mcp.tool(
    tags={"coda", "rows", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_delete_row(
    ctx: Context,
    doc_id: DocId,
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name"),
    ],
    row_id_or_name: Annotated[
        str,
        Field(description="Row ID or name to delete"),
    ],
) -> str:
    """Delete a single row from a Coda table.

    Permanently removes the row. This is irreversible. Verify the row with
    coda_get_row before deleting. For bulk deletion, use coda_delete_rows
    with a list of row IDs instead.
    """
    await _get_client(ctx).delete(
        _p("docs", doc_id, "tables", table_id_or_name, "rows", row_id_or_name)
    )
    return _ok(
        {
            "status": "deleted",
            "doc_id": doc_id,
            "table_id": table_id_or_name,
            "row_id": row_id_or_name,
        }
    )


@mcp.tool(
    tags={"coda", "rows", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_delete_rows(
    ctx: Context,
    doc_id: DocId,
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name"),
    ],
    row_ids: Annotated[
        list[str],
        Field(description="List of row IDs to delete"),
    ],
) -> str:
    """Delete multiple rows from a Coda table in a single call.

    Permanently removes all specified rows. This is irreversible. List the rows
    first with coda_list_rows to get their IDs. Returns a requestId for async
    mutation tracking. Prefer this over calling coda_delete_row in a loop for
    better performance and rate limit efficiency.
    """
    body: dict[str, Any] = {"rowIds": row_ids}
    data = await _get_client(ctx).delete(
        _p("docs", doc_id, "tables", table_id_or_name, "rows"),
        json_data=body,
    )
    return _ok(data or {"status": "deleted", "row_count": len(row_ids)})


@mcp.tool(
    tags={"coda", "rows", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_push_button(
    ctx: Context,
    doc_id: DocId,
    table_id_or_name: Annotated[
        str,
        Field(description="Table ID or name"),
    ],
    row_id_or_name: Annotated[
        str,
        Field(description="Row ID or name containing the button"),
    ],
    column_id_or_name: Annotated[
        str,
        Field(description="Column ID or name of the button column"),
    ],
) -> str:
    """Push a button in a Coda table row.

    Triggers the button's configured action (e.g. run automation, modify row).
    The button must be in a Button-type column. The effect depends on the
    button's configuration in the Coda doc. Returns a requestId for async
    mutation tracking.
    """
    return _ok(
        await _get_client(ctx).post(
            _p(
                "docs",
                doc_id,
                "tables",
                table_id_or_name,
                "rows",
                row_id_or_name,
                "buttons",
                column_id_or_name,
            ),
        )
    )
