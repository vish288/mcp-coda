"""Control tools — list and get control values."""


from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import _err, _get_client, _ok


@mcp.tool(
    tags={"coda", "controls", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_controls(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to list controls from"),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of controls to return (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Annotated[
        str | None,
        Field(description="Pagination cursor from a previous response"),
    ] = None,
) -> str:
    """List all controls (sliders, select lists, date pickers, etc.) in a Coda doc.

    Returns control metadata including name, ID, type, and current value.
    Controls are interactive UI elements on pages. Use coda_get_control to
    read a specific control's current value.
    """
    try:
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["pageToken"] = cursor
        data = await _get_client(ctx).get(f"/docs/{doc_id}/controls", params=params)
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
    tags={"coda", "controls", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_get_control(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the control"),
    ],
    control_id_or_name: Annotated[
        str,
        Field(description="Control ID or name"),
    ],
) -> str:
    """Get the current value of a control in a Coda doc.

    Returns the control's name, ID, type, and current value. Controls include
    sliders, select lists, date pickers, text inputs, and buttons. The value
    reflects the current user-facing state. Use coda_list_controls to discover
    available controls.
    """
    try:
        data = await _get_client(ctx).get(f"/docs/{doc_id}/controls/{control_id_or_name}")
        return _ok(data)
    except Exception as e:
        return _err(e)
