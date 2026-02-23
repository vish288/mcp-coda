"""Automation tools — trigger automations."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import _check_write, _err, _get_client, _ok


@mcp.tool(
    tags={"coda", "automations", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
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
    try:
        _check_write(ctx)
        body: dict[str, Any] = {}
        if payload is not None:
            body["message"] = payload
        data = await _get_client(ctx).post(
            f"/docs/{doc_id}/hooks/automation/{rule_id}",
            json_data=body,
        )
        return _ok(data)
    except Exception as e:
        return _err(e)
