"""Formula tools — list and get formula values."""

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import _err, _get_client, _ok


@mcp.tool(
    tags={"coda", "formulas", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_formulas(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to list formulas from"),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of formulas to return (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
) -> str:
    """List all named formulas in a Coda doc.

    Returns formula metadata including name, ID, and value. Named formulas are
    doc-level computed values (not column formulas). Use coda_get_formula to
    get a specific formula's current value.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get(f"/docs/{doc_id}/formulas", params=params)
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
    tags={"coda", "formulas", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_formula(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the formula"),
    ],
    formula_id_or_name: Annotated[
        str,
        Field(description="Formula ID or name"),
    ],
) -> str:
    """Get the current value of a named formula in a Coda doc.

    Returns the formula's name, ID, type, current value, and whether it has
    an error. The value is computed by Coda and reflects the latest state.
    Use coda_list_formulas to discover available formulas in a doc.
    """
    try:
        data = await _get_client(ctx).get(f"/docs/{doc_id}/formulas/{formula_id_or_name}")
        return _ok(data)
    except Exception as e:
        return _err(e)
