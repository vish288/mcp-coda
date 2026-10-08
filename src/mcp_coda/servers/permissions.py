"""Permission tools — sharing metadata, ACL, principals."""

from typing import Annotated, Any, Literal

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import Cursor, _get_client, _ok, _p, _page, tool_result


@mcp.tool(
    tags={"coda", "permissions", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_get_sharing_metadata(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to get sharing metadata for"),
    ],
) -> str:
    """Get sharing metadata for a Coda doc.

    Returns whether the doc can be shared, copied, or has sharing restrictions.
    This is metadata about the doc's sharing configuration, not the list of
    who has access — use coda_list_permissions for that.
    """
    return _ok(await _get_client(ctx).get(_p("docs", doc_id, "acl", "metadata")))


@mcp.tool(
    tags={"coda", "permissions", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_list_permissions(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to list permissions for"),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of permissions to return (1-200)", ge=1, le=200),
    ] = 50,
    cursor: Cursor = None,
) -> str:
    """List all permission entries (ACL) for a Coda doc.

    Returns who has access to the doc and their access level (read, write, etc.).
    Each entry includes the principal (user or group) and their permission type.
    Use coda_add_permission to grant access or coda_delete_permission to revoke.
    """
    params = {"limit": limit, "pageToken": cursor}
    return _page(
        await _get_client(ctx).get(_p("docs", doc_id, "acl", "permissions"), params=params)
    )


@mcp.tool(
    tags={"coda", "permissions", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_add_permission(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to add permission to"),
    ],
    access: Annotated[
        Literal["readonly", "write", "comment", "none"],
        Field(description="Access level to grant"),
    ],
    principal_email: Annotated[
        str | None,
        Field(description="Email address of the user to grant access to"),
    ] = None,
    principal_domain: Annotated[
        str | None,
        Field(description="Domain to grant access to (e.g. 'example.com')"),
    ] = None,
    suppress_notification: Annotated[
        bool,
        Field(description="If True, don't send an email notification"),
    ] = False,
) -> str:
    """Add a permission entry to a Coda doc.

    Grants access to a user by email or to an entire domain. Specify either
    principal_email or principal_domain (not both). The access level controls
    what the principal can do: readonly, write, comment, or none (removes
    implicit access). Returns the created permission entry.
    """
    if principal_email is None and principal_domain is None:
        msg = "principal_email or principal_domain required"
        raise ValueError(msg)
    body: dict[str, Any] = {"access": access}
    principal: dict[str, str] = {}
    if principal_email is not None:
        principal["type"] = "email"
        principal["email"] = principal_email
    elif principal_domain is not None:
        principal["type"] = "domain"
        principal["domain"] = principal_domain
    body["principal"] = principal
    if suppress_notification:
        body["suppressEmail"] = True
    return _ok(
        await _get_client(ctx).post(_p("docs", doc_id, "acl", "permissions"), json_data=body)
    )


@mcp.tool(
    tags={"coda", "permissions", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
@tool_result(write=True)
async def coda_delete_permission(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to remove permission from"),
    ],
    permission_id: Annotated[
        str,
        Field(description="The permission ID to delete (from coda_list_permissions)"),
    ],
) -> str:
    """Remove a permission entry from a Coda doc.

    Revokes the specified permission. The principal will lose access to the doc
    unless they have access through another permission (e.g. domain-level).
    Get the permission_id from coda_list_permissions first.
    """
    await _get_client(ctx).delete(_p("docs", doc_id, "acl", "permissions", permission_id))
    return _ok({"status": "deleted", "doc_id": doc_id, "permission_id": permission_id})


@mcp.tool(
    tags={"coda", "permissions", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_search_principals(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to search principals in"),
    ],
    query: Annotated[
        str,
        Field(description="Search query (name or email prefix)"),
    ],
) -> str:
    """Search for users and groups that can be added to a doc's permissions.

    Returns matching principals (users and groups) based on the query string.
    Use this to look up a user's email or find groups before calling
    coda_add_permission. Results include the principal's type, email, and name.
    """
    return _ok(
        await _get_client(ctx).get(
            _p("docs", doc_id, "acl", "principals", "search"),
            params={"query": query},
        )
    )


@mcp.tool(
    tags={"coda", "permissions", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
@tool_result
async def coda_get_acl_settings(
    ctx: Context,
    doc_id: Annotated[
        str,
        Field(description="The doc ID to get ACL settings for"),
    ],
) -> str:
    """Get the ACL settings for a Coda doc.

    Returns doc-level access control settings such as whether the doc allows
    copying, whether editors can change permissions, and the default access
    mode. These are administrative settings, not individual permission entries.
    """
    return _ok(await _get_client(ctx).get(_p("docs", doc_id, "acl", "settings")))
