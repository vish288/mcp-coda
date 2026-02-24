"""MCP Resources — static knowledge resources and live data resources."""

import json
from pathlib import Path
from typing import Any

from fastmcp import Context

from . import mcp
from ._helpers import _get_client, _load_file

# ════════════════════════════════════════════════════════════════════
# Static resource loader
# ════════════════════════════════════════════════════════════════════

_RESOURCES_DIR = str(Path(__file__).resolve().parent.parent / "resources")


def _load(filename: str) -> str:
    """Load a resource markdown file from the resources directory."""
    return _load_file(_RESOURCES_DIR, filename)


# ════════════════════════════════════════════════════════════════════
# Rules
# ════════════════════════════════════════════════════════════════════


@mcp.resource(
    "resource://rules/coda-doc-structure",
    name="Coda Doc Structure",
    description=(
        "Doc → Pages → Subpages hierarchy, page types, naming, "
        "organization, when to split docs vs folders"
    ),
    mime_type="text/markdown",
    tags={"rule", "coda", "docs"},
)
def coda_doc_structure_rules() -> str:
    """Doc hierarchy, page types, and organization patterns."""
    return _load("coda-doc-structure.md")


@mcp.resource(
    "resource://rules/coda-table-design",
    name="Coda Table Design",
    description=(
        "Column types, lookup/relation patterns, display columns, "
        "calculated columns, row limits, table vs view, schema naming"
    ),
    mime_type="text/markdown",
    tags={"rule", "coda", "tables"},
)
def coda_table_design_rules() -> str:
    """Table schema design patterns and column type reference."""
    return _load("coda-table-design.md")


@mcp.resource(
    "resource://rules/coda-permissions",
    name="Coda Permission Model",
    description=(
        "Doc-level vs page-level locking, sharing hierarchy, "
        "ACL settings, domain sharing, principal types"
    ),
    mime_type="text/markdown",
    tags={"rule", "coda", "permissions"},
)
def coda_permissions_rules() -> str:
    """Permission model, sharing hierarchy, and ACL patterns."""
    return _load("coda-permissions.md")


@mcp.resource(
    "resource://rules/coda-automations",
    name="Coda Automation Patterns",
    description=(
        "Rule types, webhook triggers, button triggers, rate limits, payload design, idempotency"
    ),
    mime_type="text/markdown",
    tags={"rule", "coda", "automations"},
)
def coda_automations_rules() -> str:
    """Automation patterns for webhooks, buttons, and scheduled rules."""
    return _load("coda-automations.md")


@mcp.resource(
    "resource://rules/coda-api-patterns",
    name="Coda API Best Practices",
    description=(
        "Rate limits (100 read/6s, 10 write/6s), pagination, "
        "async mutations, error handling, retry strategy"
    ),
    mime_type="text/markdown",
    tags={"rule", "coda", "api"},
)
def coda_api_patterns_rules() -> str:
    """API rate limits, pagination, async mutations, and retry patterns."""
    return _load("coda-api-patterns.md")


# ════════════════════════════════════════════════════════════════════
# Guides
# ════════════════════════════════════════════════════════════════════


@mcp.resource(
    "resource://guides/row-operations",
    name="Row Operations Guide",
    description=(
        "Insert vs upsert, bulk ops (500 limit), key columns, "
        "cell value formats, button pushing, delete strategies"
    ),
    mime_type="text/markdown",
    tags={"guide", "coda", "rows"},
)
def row_operations_guide() -> str:
    """Row insert, upsert, update, delete, and bulk operation patterns."""
    return _load("row-operations.md")


@mcp.resource(
    "resource://guides/page-content",
    name="Page Content Guide",
    description=(
        "HTML vs markdown, content format selection, "
        "insert modes (replace/append), export workflows"
    ),
    mime_type="text/markdown",
    tags={"guide", "coda", "pages"},
)
def page_content_guide() -> str:
    """Page content reading, writing, formats, and export workflows."""
    return _load("page-content.md")


@mcp.resource(
    "resource://guides/formula-controls",
    name="Formulas & Controls Guide",
    description=("Named formulas, formula evaluation, control types, reading control values"),
    mime_type="text/markdown",
    tags={"guide", "coda", "formulas"},
)
def formula_controls_guide() -> str:
    """Named formula and control reading patterns."""
    return _load("formula-controls.md")


@mcp.resource(
    "resource://guides/publishing-analytics",
    name="Publishing & Analytics Guide",
    description=(
        "Publishing categories, gallery settings, doc/page/pack analytics, date filtering"
    ),
    mime_type="text/markdown",
    tags={"guide", "coda", "analytics"},
)
def publishing_analytics_guide() -> str:
    """Doc publishing and analytics query patterns."""
    return _load("publishing-analytics.md")


@mcp.resource(
    "resource://guides/folder-organization",
    name="Folder Organization Guide",
    description=("Folder CRUD, doc-folder relationships, folder hierarchy, bulk organization"),
    mime_type="text/markdown",
    tags={"guide", "coda", "folders"},
)
def folder_organization_guide() -> str:
    """Folder structure, doc organization, and bulk move patterns."""
    return _load("folder-organization.md")


# ════════════════════════════════════════════════════════════════════
# Data resources (live API)
# ════════════════════════════════════════════════════════════════════


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
