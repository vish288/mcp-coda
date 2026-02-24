"""MCP Resources — expose doc list and table schemas as ambient context."""


import json
from typing import Any

from fastmcp import Context

from . import mcp
from ._helpers import _get_client


@mcp.resource(
    "coda://docs",
    name="Coda Docs",
    description="List of Coda docs accessible to the current API token",
    mime_type="application/json",
    tags={"coda", "docs"},
)
async def docs_resource(ctx: Context) -> str:
    """Return all accessible docs as JSON for ambient context."""
    try:
        data = await _get_client(ctx).get("/docs", params={"limit": 200})
        items = data.get("items", [])
        docs = [
            {
                "id": d.get("id"),
                "name": d.get("name"),
                "owner": d.get("owner"),
                "browserLink": d.get("browserLink"),
                "updatedAt": d.get("updatedAt"),
            }
            for d in items
        ]
        return json.dumps(docs, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource(
    "coda://docs/{doc_id}/schema",
    name="Coda Doc Schema",
    description=(
        "Table and column definitions for a Coda doc. "
        "Provides ambient schema context without consuming tool calls."
    ),
    mime_type="application/json",
    tags={"coda", "schema"},
)
async def doc_schema_resource(doc_id: str, ctx: Context) -> str:
    """Return table + column schema for a doc as JSON."""
    try:
        client = _get_client(ctx)
        tables_data = await client.get(f"/docs/{doc_id}/tables", params={"limit": 200})
        tables = tables_data.get("items", [])
        schema: list[dict[str, Any]] = []
        for table in tables:
            table_id = table.get("id", "")
            cols_data = await client.get(
                f"/docs/{doc_id}/tables/{table_id}/columns",
                params={"limit": 200},
            )
            columns = [
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "type": c.get("format", {}).get("type") if c.get("format") else None,
                    "calculated": c.get("calculated", False),
                    "display": c.get("display", False),
                }
                for c in cols_data.get("items", [])
            ]
            schema.append(
                {
                    "id": table_id,
                    "name": table.get("name"),
                    "type": table.get("tableType", "table"),
                    "rowCount": table.get("rowCount", 0),
                    "columns": columns,
                }
            )
        return json.dumps(schema, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
