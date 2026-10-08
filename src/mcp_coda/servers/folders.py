"""Folder tools — list, get, create, update, delete folders."""

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import Cursor, _get_client, _ok, _p, _page, tool_result


@mcp.tool(
    tags={"coda", "folders", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_list_folders(
    ctx: Context,
    workspace_id: Annotated[
        str | None,
        Field(description="Limit results to folders in this workspace (e.g. 'ws-AbCdEf')"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of folders to return (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Cursor = None,
) -> str:
    """List folders accessible to the current API token, one page at a time.

    Returns folder metadata (name, ID, parent folder) with pagination — the API
    defaults to 25 per page, so pass cursor to fetch the rest. Folders organize
    docs in the Coda workspace. Use the returned folder IDs with coda_create_doc
    to place new docs in specific folders.
    """
    params = {"limit": limit, "workspaceId": workspace_id, "pageToken": cursor}
    return _page(await _get_client(ctx).get("/folders", params=params))


@mcp.tool(
    tags={"coda", "folders", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_get_folder(
    ctx: Context,
    folder_id: Annotated[
        str,
        Field(description="The folder ID to get details for"),
    ],
) -> str:
    """Get metadata for a single folder.

    Returns the folder's name, ID, parent folder, and child items. Use
    coda_list_folders to discover available folders first.
    """
    return _ok(await _get_client(ctx).get(_p("folders", folder_id)))


@mcp.tool(
    tags={"coda", "folders", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_create_folder(
    ctx: Context,
    name: Annotated[
        str,
        Field(description="Name for the new folder"),
    ],
    workspace_id: Annotated[
        str,
        Field(description="Workspace ID where the folder will be created"),
    ],
    description: Annotated[
        str | None,
        Field(description="Description for the folder"),
    ] = None,
) -> str:
    """Create a new folder in a Coda workspace.

    Creates a folder in the specified workspace. Returns the new folder's ID and
    metadata. Use the folder ID when creating docs with coda_create_doc to
    organize them.
    """
    body: dict[str, Any] = {"name": name, "workspaceId": workspace_id}
    if description is not None:
        body["description"] = description
    return _ok(await _get_client(ctx).post("/folders", json_data=body))


@mcp.tool(
    tags={"coda", "folders", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False, "idempotentHint": True},
)
@tool_result(write=True)
async def coda_update_folder(
    ctx: Context,
    folder_id: Annotated[
        str,
        Field(description="The folder ID to update"),
    ],
    name: Annotated[
        str | None,
        Field(description="New name for the folder"),
    ] = None,
) -> str:
    """Update a folder's name.

    Renames the specified folder. Returns the updated folder metadata.
    This is an idempotent operation.
    """
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if not body:
        return _ok({"unchanged": True, "folder_id": folder_id})
    return _ok(await _get_client(ctx).patch(_p("folders", folder_id), json_data=body))


@mcp.tool(
    tags={"coda", "folders", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_delete_folder(
    ctx: Context,
    folder_id: Annotated[
        str,
        Field(description="The folder ID to delete"),
    ],
) -> str:
    """Delete a folder from the Coda workspace. Returns confirmation with folder_id.

    Permanently removes the folder. Docs inside the folder may be moved to
    the root level or deleted depending on Coda's behavior. Verify the folder
    with coda_get_folder before deleting.
    """
    await _get_client(ctx).delete(_p("folders", folder_id))
    return _ok({"status": "deleted", "folder_id": folder_id})
