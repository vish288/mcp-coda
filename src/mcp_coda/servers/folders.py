"""Folder tools — list, get, create, update, delete folders."""

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import _check_write, _err, _get_client, _ok


@mcp.tool(
    tags={"coda", "folders", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_folders(ctx: Context) -> str:
    """List all folders accessible to the current API token.

    Returns folder metadata including name, ID, and parent folder. Folders
    organize docs in the Coda workspace. Use the returned folder IDs with
    coda_create_doc to place new docs in specific folders.
    """
    try:
        data = await _get_client(ctx).get("/folders")
        items = data.get("items", [])
        return _ok({"items": items, "total_count": len(items)})
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "folders", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
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
    try:
        data = await _get_client(ctx).get(f"/folders/{folder_id}")
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "folders", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
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
    try:
        _check_write(ctx)
        body: dict[str, Any] = {"name": name, "workspaceId": workspace_id}
        if description is not None:
            body["description"] = description
        data = await _get_client(ctx).post("/folders", json_data=body)
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "folders", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False, "idempotentHint": True},
)
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
    try:
        _check_write(ctx)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        data = await _get_client(ctx).patch(f"/folders/{folder_id}", json_data=body)
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "folders", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
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
    try:
        _check_write(ctx)
        await _get_client(ctx).delete(f"/folders/{folder_id}")
        return _ok({"status": "deleted", "folder_id": folder_id})
    except Exception as e:
        return _err(e)
