"""Miscellaneous tools — automations, formulas, controls, and publishing.

These four small tool groups share no state and were one tool (automations),
two (formulas), two (controls) and three (publishing) modules; folded into one
file so the tools no longer need a dozen modules.
"""

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import Cursor, _get_client, _ok, _p, _page, tool_result

# --- Automations ---


@mcp.tool(
    tags={"coda", "automations", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_trigger_automation(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID containing the automation"),
    ],
    rule_id: Annotated[
        str,
        Field(description="The automation rule ID to trigger"),
    ],
    payload: Annotated[
        dict[str, Any] | None,
        Field(description="Optional JSON payload to pass to the automation"),
    ] = None,
) -> str:
    """Trigger a Coda automation rule.

    Fires the specified automation rule, optionally passing a JSON payload.
    The automation must have an API-triggerable event type. The payload schema
    depends on the automation's configuration. Returns a requestId for tracking.
    The rule_id can be found in the automation's settings in the Coda UI.
    """
    body: dict[str, Any] = payload if payload is not None else {}
    return _ok(
        await _get_client(ctx).post(
            _p("docs", doc_id, "hooks", "automation", rule_id),
            json_data=body,
        )
    )


# --- Formulas ---


@mcp.tool(
    tags={"coda", "formulas", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
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
    cursor: Cursor = None,
) -> str:
    """List all named formulas in a Coda doc.

    Returns formula metadata including name, ID, and value. Named formulas are
    doc-level computed values (not column formulas). Use coda_get_formula to
    get a specific formula's current value.
    """
    params = {"limit": limit, "pageToken": cursor}
    return _page(await _get_client(ctx).get(_p("docs", doc_id, "formulas"), params=params))


@mcp.tool(
    tags={"coda", "formulas", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
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
    return _ok(await _get_client(ctx).get(_p("docs", doc_id, "formulas", formula_id_or_name)))


# --- Controls ---


@mcp.tool(
    tags={"coda", "controls", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
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
    cursor: Cursor = None,
) -> str:
    """List all controls (sliders, select lists, date pickers, etc.) in a Coda doc.

    Returns control metadata including name, ID, type, and current value.
    Controls are interactive UI elements on pages. Use coda_get_control to
    read a specific control's current value.
    """
    params = {"limit": limit, "pageToken": cursor}
    return _page(await _get_client(ctx).get(_p("docs", doc_id, "controls"), params=params))


@mcp.tool(
    tags={"coda", "controls", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
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
    return _ok(await _get_client(ctx).get(_p("docs", doc_id, "controls", control_id_or_name)))


# --- Publishing ---


@mcp.tool(
    tags={"coda", "publishing", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_list_categories(ctx: Context) -> str:
    """List all available publishing categories in Coda.

    Returns the categories that can be used when publishing a doc to the Coda
    gallery. Each category has a name and ID. Use these category IDs with
    coda_publish_doc.
    """
    data = await _get_client(ctx).get("/categories")
    items = data.get("items", [])
    return _ok({"items": items, "total_count": len(items)})


@mcp.tool(
    tags={"coda", "publishing", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_publish_doc(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to publish"),
    ],
    slug: Annotated[
        str | None,
        Field(description="URL slug for the published doc"),
    ] = None,
    category_names: Annotated[
        list[str] | None,
        Field(description="Category names for the published doc (from coda_list_categories)"),
    ] = None,
    discoverable: Annotated[
        bool,
        Field(description="Whether the doc is discoverable in the Coda gallery"),
    ] = True,
    mode: Annotated[
        str | None,
        Field(description="Publishing mode (e.g. 'view', 'play', 'edit')"),
    ] = None,
) -> str:
    """Publish a Coda doc to make it publicly accessible.

    Publishes the doc with optional gallery listing and URL slug. The doc
    becomes accessible via a public URL. Use coda_unpublish_doc to revert.
    Returns the published doc's URL and settings.
    """
    body: dict[str, Any] = {"discoverable": discoverable}
    if slug is not None:
        body["slug"] = slug
    if category_names is not None:
        body["categoryNames"] = category_names
    if mode is not None:
        body["mode"] = mode
    return _ok(await _get_client(ctx).put(_p("docs", doc_id, "publish"), json_data=body))


@mcp.tool(
    tags={"coda", "publishing", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_unpublish_doc(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to unpublish"),
    ],
) -> str:
    """Unpublish a Coda doc, removing public access. Returns confirmation with doc_id.

    Reverts a previously published doc to private. The public URL will stop
    working. This is reversible — you can publish again with coda_publish_doc.
    """
    await _get_client(ctx).delete(_p("docs", doc_id, "publish"))
    return _ok({"status": "unpublished", "doc_id": doc_id})
