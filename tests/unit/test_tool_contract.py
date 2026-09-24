"""Wire contract for every tool, through the real server.

The `.fn` tests in test_tools_*.py mock the client, so they pin the kwargs a
tool hands to `CodaClient`, not what leaves the process. This table pins the
request as respx sees it: method, path, query string, JSON body. One row per
`@mcp.tool` in src/. Derived from each tool body, not guessed.

Row: (tool_name, call_args, method, path, expected_query, expected_json_body).
`method=None` marks a tool with no HTTP call; only its response shape is checked.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
import respx
from fastmcp import Client
from httpx import Response

from mcp_coda.servers import mcp

ROWS: list[tuple[str, dict[str, Any], str | None, str, dict[str, str], Any]] = [
    # account
    ("coda_whoami", {}, "GET", "/whoami", {}, None),
    (
        "coda_resolve_browser_link",
        {"url": "https://coda.io/d/Doc_dabc"},
        "GET",
        "/resolveBrowserLink",
        {"url": "https://coda.io/d/Doc_dabc"},
        None,
    ),
    ("coda_get_mutation_status", {"request_id": "req1"}, "GET", "/mutationStatus/req1", {}, None),
    ("coda_rate_limit_budget", {}, None, "", {}, None),
    # analytics
    (
        "coda_list_doc_analytics",
        {
            "doc_ids": ["d1", "d2"],
            "is_published": True,
            "since_date": "2024-01-01",
            "until_date": "2024-02-01",
            "limit": 10,
            "cursor": "c1",
        },
        "GET",
        "/analytics/docs",
        {
            "limit": "10",
            "docIds": "d1,d2",
            "isPublished": "true",
            "sinceDate": "2024-01-01",
            "untilDate": "2024-02-01",
            "pageToken": "c1",
        },
        None,
    ),
    (
        "coda_get_doc_analytics_summary",
        {"is_published": False, "since_date": "2024-01-01"},
        "GET",
        "/analytics/docs/summary",
        {"isPublished": "false", "sinceDate": "2024-01-01"},
        None,
    ),
    (
        "coda_list_page_analytics",
        {"doc_id": "d1", "since_date": "2024-01-01", "limit": 5, "cursor": "c1"},
        "GET",
        "/analytics/docs/d1/pages",
        {"limit": "5", "sinceDate": "2024-01-01", "pageToken": "c1"},
        None,
    ),
    (
        "coda_list_pack_analytics",
        {"pack_ids": [1, 2], "is_published": True, "limit": 5},
        "GET",
        "/analytics/packs",
        {"limit": "5", "packIds": "1,2", "isPublished": "true"},
        None,
    ),
    (
        "coda_get_pack_analytics_summary",
        {"pack_ids": [7], "until_date": "2024-02-01"},
        "GET",
        "/analytics/packs/summary",
        {"packIds": "7", "untilDate": "2024-02-01"},
        None,
    ),
    (
        "coda_list_pack_formula_analytics",
        {"pack_id": 7, "until_date": "2024-02-01", "limit": 5, "cursor": "c1"},
        "GET",
        "/analytics/packs/7/formulas",
        {"limit": "5", "untilDate": "2024-02-01", "pageToken": "c1"},
        None,
    ),
    ("coda_get_analytics_updated", {}, "GET", "/analytics/updated", {}, None),
    # automations
    (
        "coda_trigger_automation",
        {"doc_id": "d1", "rule_id": "r1", "payload": {"k": "v"}},
        "POST",
        "/docs/d1/hooks/automation/r1",
        {},
        {"k": "v"},
    ),
    # controls
    (
        "coda_list_controls",
        {"doc_id": "d1", "limit": 5, "cursor": "c1"},
        "GET",
        "/docs/d1/controls",
        {"limit": "5", "pageToken": "c1"},
        None,
    ),
    (
        "coda_get_control",
        {"doc_id": "d1", "control_id_or_name": "ctrl-1"},
        "GET",
        "/docs/d1/controls/ctrl-1",
        {},
        None,
    ),
    # docs
    (
        "coda_list_docs",
        {"query": "q", "is_owner": True, "folder_id": "f1", "limit": 5, "cursor": "c1"},
        "GET",
        "/docs",
        {"limit": "5", "query": "q", "isOwner": "true", "folderId": "f1", "pageToken": "c1"},
        None,
    ),
    ("coda_get_doc", {"doc_id": "d1"}, "GET", "/docs/d1", {}, None),
    (
        "coda_create_doc",
        {"title": "T", "folder_id": "f1", "source_doc": "d0"},
        "POST",
        "/docs",
        {},
        {"title": "T", "folderId": "f1", "sourceDoc": "d0"},
    ),
    (
        "coda_update_doc",
        {"doc_id": "d1", "title": "T", "icon_name": "rocket"},
        "PATCH",
        "/docs/d1",
        {},
        {"title": "T", "iconName": "rocket"},
    ),
    ("coda_delete_doc", {"doc_id": "d1"}, "DELETE", "/docs/d1", {}, None),
    # folders
    ("coda_list_folders", {}, "GET", "/folders", {}, None),
    ("coda_get_folder", {"folder_id": "f1"}, "GET", "/folders/f1", {}, None),
    (
        "coda_create_folder",
        {"name": "N", "workspace_id": "ws1", "description": "D"},
        "POST",
        "/folders",
        {},
        {"name": "N", "workspaceId": "ws1", "description": "D"},
    ),
    (
        "coda_update_folder",
        {"folder_id": "f1", "name": "N"},
        "PATCH",
        "/folders/f1",
        {},
        {"name": "N"},
    ),
    ("coda_delete_folder", {"folder_id": "f1"}, "DELETE", "/folders/f1", {}, None),
    # formulas
    (
        "coda_list_formulas",
        {"doc_id": "d1", "limit": 5, "cursor": "c1"},
        "GET",
        "/docs/d1/formulas",
        {"limit": "5", "pageToken": "c1"},
        None,
    ),
    (
        "coda_get_formula",
        {"doc_id": "d1", "formula_id_or_name": "f-1"},
        "GET",
        "/docs/d1/formulas/f-1",
        {},
        None,
    ),
    # pages
    (
        "coda_list_pages",
        {"doc_id": "d1", "limit": 5, "cursor": "c1"},
        "GET",
        "/docs/d1/pages",
        {"limit": "5", "pageToken": "c1"},
        None,
    ),
    (
        "coda_get_page",
        {"doc_id": "d1", "page_id_or_name": "p1"},
        "GET",
        "/docs/d1/pages/p1",
        {},
        None,
    ),
    (
        "coda_create_page",
        {
            "doc_id": "d1",
            "name": "P",
            "parent_page_id": "p0",
            "subtitle": "S",
            "content": "# hi",
            "content_format": "markdown",
        },
        "POST",
        "/docs/d1/pages",
        {},
        {
            "name": "P",
            "parentPageId": "p0",
            "subtitle": "S",
            "pageContent": {
                "type": "canvas",
                "canvasContent": {"format": "markdown", "content": "# hi"},
            },
        },
    ),
    (
        "coda_update_page",
        {
            "doc_id": "d1",
            "page_id_or_name": "p1",
            "name": "P",
            "subtitle": "S",
            "content": "<p>x</p>",
            "content_format": "html",
            "insert_mode": "append",
        },
        "PUT",
        "/docs/d1/pages/p1",
        {},
        {
            "name": "P",
            "subtitle": "S",
            "contentUpdate": {
                "insertionMode": "append",
                "canvasContent": {"format": "html", "content": "<p>x</p>"},
            },
        },
    ),
    (
        "coda_delete_page",
        {"doc_id": "d1", "page_id_or_name": "p1"},
        "DELETE",
        "/docs/d1/pages/p1",
        {},
        None,
    ),
    (
        "coda_get_page_content",
        {"doc_id": "d1", "page_id_or_name": "p1", "output_format": "html"},
        "GET",
        "/docs/d1/pages/p1/content",
        {"outputFormat": "html"},
        None,
    ),
    (
        "coda_delete_page_content",
        {"doc_id": "d1", "page_id_or_name": "p1"},
        "DELETE",
        "/docs/d1/pages/p1/content",
        {},
        None,
    ),
    (
        "coda_export_page",
        {"doc_id": "d1", "page_id_or_name": "p1", "output_format": "html"},
        "POST",
        "/docs/d1/pages/p1/export",
        {},
        {"outputFormat": "html"},
    ),
    # permissions
    ("coda_get_sharing_metadata", {"doc_id": "d1"}, "GET", "/docs/d1/acl/metadata", {}, None),
    (
        "coda_list_permissions",
        {"doc_id": "d1", "limit": 5, "cursor": "c1"},
        "GET",
        "/docs/d1/acl/permissions",
        {"limit": "5", "pageToken": "c1"},
        None,
    ),
    (
        "coda_add_permission",
        {
            "doc_id": "d1",
            "access": "write",
            "principal_email": "a@b.c",
            "suppress_notification": True,
        },
        "POST",
        "/docs/d1/acl/permissions",
        {},
        {
            "access": "write",
            "principal": {"type": "email", "email": "a@b.c"},
            "suppressEmail": True,
        },
    ),
    (
        "coda_delete_permission",
        {"doc_id": "d1", "permission_id": "perm1"},
        "DELETE",
        "/docs/d1/acl/permissions/perm1",
        {},
        None,
    ),
    (
        "coda_search_principals",
        {"doc_id": "d1", "query": "al"},
        "GET",
        "/docs/d1/acl/principals/search",
        {"query": "al"},
        None,
    ),
    ("coda_get_acl_settings", {"doc_id": "d1"}, "GET", "/docs/d1/acl/settings", {}, None),
    # publishing
    ("coda_list_categories", {}, "GET", "/categories", {}, None),
    (
        "coda_publish_doc",
        {
            "doc_id": "d1",
            "slug": "my-doc",
            "category_names": ["Ops"],
            "discoverable": False,
            "mode": "view",
        },
        "PUT",
        "/docs/d1/publish",
        {},
        {"discoverable": False, "slug": "my-doc", "categoryNames": ["Ops"], "mode": "view"},
    ),
    ("coda_unpublish_doc", {"doc_id": "d1"}, "DELETE", "/docs/d1/publish", {}, None),
    # rows
    (
        "coda_list_rows",
        {
            "doc_id": "d1",
            "table_id_or_name": "t1",
            "query": 'Status:"Active"',
            "sort_by": "-Created",
            "use_column_names": False,
            "limit": 5,
            "cursor": "c1",
        },
        "GET",
        "/docs/d1/tables/t1/rows",
        {
            "limit": "5",
            "useColumnNames": "false",
            "query": 'Status:"Active"',
            "sortBy": "-Created",
            "pageToken": "c1",
        },
        None,
    ),
    (
        "coda_get_row",
        {"doc_id": "d1", "table_id_or_name": "t1", "row_id_or_name": "r1"},
        "GET",
        "/docs/d1/tables/t1/rows/r1",
        {"useColumnNames": "true"},
        None,
    ),
    (
        "coda_insert_rows",
        {
            "doc_id": "d1",
            "table_id_or_name": "t1",
            "rows": [{"cells": [{"column": "Name", "value": "A"}]}],
            "key_columns": ["Name"],
        },
        "POST",
        "/docs/d1/tables/t1/rows",
        {},
        {"rows": [{"cells": [{"column": "Name", "value": "A"}]}], "keyColumns": ["Name"]},
    ),
    (
        "coda_update_row",
        {
            "doc_id": "d1",
            "table_id_or_name": "t1",
            "row_id_or_name": "r1",
            "cells": [{"column": "Status", "value": "Done"}],
        },
        "PUT",
        "/docs/d1/tables/t1/rows/r1",
        {},
        {"row": {"cells": [{"column": "Status", "value": "Done"}]}},
    ),
    (
        "coda_delete_row",
        {"doc_id": "d1", "table_id_or_name": "t1", "row_id_or_name": "r1"},
        "DELETE",
        "/docs/d1/tables/t1/rows/r1",
        {},
        None,
    ),
    (
        "coda_delete_rows",
        {"doc_id": "d1", "table_id_or_name": "t1", "row_ids": ["r1", "r2"]},
        "DELETE",
        "/docs/d1/tables/t1/rows",
        {},
        {"rowIds": ["r1", "r2"]},
    ),
    (
        "coda_push_button",
        {
            "doc_id": "d1",
            "table_id_or_name": "t1",
            "row_id_or_name": "r1",
            "column_id_or_name": "Go",
        },
        "POST",
        "/docs/d1/tables/t1/rows/r1/buttons/Go",
        {},
        None,
    ),
    # tables
    (
        "coda_list_tables",
        {"doc_id": "d1", "table_types": "view", "limit": 5, "cursor": "c1"},
        "GET",
        "/docs/d1/tables",
        {"limit": "5", "tableTypes": "view", "pageToken": "c1"},
        None,
    ),
    (
        "coda_get_table",
        {"doc_id": "d1", "table_id_or_name": "t1"},
        "GET",
        "/docs/d1/tables/t1",
        {},
        None,
    ),
    (
        "coda_list_columns",
        {"doc_id": "d1", "table_id_or_name": "t1", "limit": 5, "cursor": "c1"},
        "GET",
        "/docs/d1/tables/t1/columns",
        {"limit": "5", "pageToken": "c1"},
        None,
    ),
    (
        "coda_get_column",
        {"doc_id": "d1", "table_id_or_name": "t1", "column_id_or_name": "c-1"},
        "GET",
        "/docs/d1/tables/t1/columns/c-1",
        {},
        None,
    ),
]

HTTP_ROWS = [r for r in ROWS if r[2] is not None]
WRITE_TOOLS = {t.name for t in asyncio.run(mcp.list_tools()) if "write" in t.tags}
_IDS = [r[0] for r in ROWS]


def test_table_covers_every_registered_tool() -> None:
    registered = {t.name for t in asyncio.run(mcp.list_tools())}
    assert set(_IDS) == registered
    assert len(_IDS) == len(registered), "duplicate rows"


async def _call(client: Client, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    result = await client.call_tool(tool, args)
    return json.loads(result.content[0].text)


@pytest.mark.parametrize("row", ROWS, ids=_IDS)
async def test_request_shape(
    tool_client: tuple[Client, respx.MockRouter], row: tuple[Any, ...]
) -> None:
    tool, args, method, path, query, body = row
    client, router = tool_client
    if method is None:
        assert "isError" not in await _call(client, tool, args)
        assert not router.calls
        return
    route = router.request(method, path).mock(return_value=Response(200, json={"items": []}))
    out = await _call(client, tool, args)
    assert "isError" not in out, out
    req = route.calls.last.request
    assert req.method == method
    assert req.url.path == f"/apis/v1{path}"
    assert dict(req.url.params) == query
    assert (json.loads(req.content) if req.content else None) == body


@pytest.mark.parametrize("row", HTTP_ROWS, ids=[r[0] for r in HTTP_ROWS])
async def test_forced_failure(
    tool_client: tuple[Client, respx.MockRouter], row: tuple[Any, ...]
) -> None:
    tool, args, method, path, _, _ = row
    client, router = tool_client
    status = 401 if tool == "coda_whoami" else 404
    router.request(method, path).mock(return_value=Response(status, text="nope"))
    out = await _call(client, tool, args)
    assert set(out) == {"isError", "error", "status_code", "body"}
    assert out["isError"] is True
    assert out["status_code"] == status
    assert out["body"] == "nope"


@pytest.mark.parametrize(
    "row", [r for r in HTTP_ROWS if r[0] in WRITE_TOOLS], ids=sorted(WRITE_TOOLS)
)
async def test_read_only_blocks_write(
    readonly_client: tuple[Client, respx.MockRouter], row: tuple[Any, ...]
) -> None:
    tool, args, *_ = row
    client, router = readonly_client
    out = await _call(client, tool, args)
    assert out["isError"] is True
    assert "CODA_READ_ONLY" in out["error"]
    assert not router.calls
