"""Publishing tools — publish, unpublish docs, list categories."""


from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from . import mcp
from ._helpers import _check_write, _err, _get_client, _ok


@mcp.tool(
    tags={"coda", "publishing", "read"},
    annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True},
)
async def coda_list_categories(ctx: Context) -> str:
    """List all available publishing categories in Coda.

    Returns the categories that can be used when publishing a doc to the Coda
    gallery. Each category has a name and ID. Use these category IDs with
    coda_publish_doc.
    """
    try:
        data = await _get_client(ctx).get("/categories")
        items = data.get("items", [])
        return _ok({"items": items, "total_count": len(items)})
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "publishing", "write"},
    annotations={"openWorldHint": True, "readOnlyHint": False},
)
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
    category_ids: Annotated[
        list[str] | None,
        Field(description="Category IDs for the published doc (from coda_list_categories)"),
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
    try:
        _check_write(ctx)
        body: dict[str, Any] = {"discoverable": discoverable}
        if slug is not None:
            body["slug"] = slug
        if category_ids is not None:
            body["categoryIds"] = category_ids
        if mode is not None:
            body["mode"] = mode
        data = await _get_client(ctx).put(f"/docs/{doc_id}/publish", json_data=body)
        return _ok(data)
    except Exception as e:
        return _err(e)


@mcp.tool(
    tags={"coda", "publishing", "write"},
    annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False},
)
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
    try:
        _check_write(ctx)
        await _get_client(ctx).delete(f"/docs/{doc_id}/publish")
        return _ok({"status": "unpublished", "doc_id": doc_id})
    except Exception as e:
        return _err(e)
