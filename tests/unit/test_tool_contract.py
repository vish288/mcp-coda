"""Wire contract for every tool, through the real server.

The `.fn` tests in test_tools_*.py mock the client, so they pin the kwargs a
tool hands to `CodaClient`, not what leaves the process. This table pins the
request as respx sees it: method, path, query string, JSON body. One row per
`@mcp.tool` in src/. Derived from each tool body, not guessed.

Row: (tool_name, call_args, method, path, expected_query, expected_json_body).
Every tool in src/ issues one HTTP call, so every row names a method.
"""

from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import respx
from fastmcp import Client
from httpx import Response

import mcp_coda.servers as servers_pkg
from mcp_coda.client import CodaClient
from mcp_coda.servers import mcp

_SERVERS_DIR = Path(servers_pkg.__file__).parent

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
    ("coda_list_folders", {}, "GET", "/folders", {"limit": "50"}, None),
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
    (
        "coda_get_export_status",
        {"doc_id": "d1", "page_id_or_name": "p1", "request_id": "req-1"},
        "GET",
        "/docs/d1/pages/p1/export/req-1",
        {},
        None,
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
            "sort_by": "createdAt",
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
            "sortBy": "createdAt",
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
WRITE_ROWS = [r for r in HTTP_ROWS if r[0] in WRITE_TOOLS]
_IDS = [r[0] for r in ROWS]


def test_table_covers_every_registered_tool() -> None:
    registered = {t.name for t in asyncio.run(mcp.list_tools())}
    assert set(_IDS) == registered
    assert len(_IDS) == len(registered), "duplicate rows"


async def _call(client: Client, tool: str, args: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Call a tool without raising on error; return (is_error, JSON body)."""
    result = await client.call_tool(tool, args, raise_on_error=False)
    return result.is_error, json.loads(result.content[0].text)


@pytest.mark.parametrize("row", ROWS, ids=_IDS)
async def test_request_shape(
    tool_client: tuple[Client, respx.MockRouter], row: tuple[Any, ...]
) -> None:
    tool, args, method, path, query, body = row
    client, router = tool_client
    route = router.request(method, path).mock(return_value=Response(200, json={"items": []}))
    result = await client.call_tool(tool, args, raise_on_error=False)
    assert result.is_error is False
    out = json.loads(result.content[0].text)
    # Shape C: structuredContent is the JSON object itself, not {"result": "<json>"}.
    # The equality alone proves the wrapper is gone (it would have been {"result": text}).
    assert result.structured_content == out
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
    is_error, out = await _call(client, tool, args)
    assert is_error is True
    assert set(out) == {"error", "status_code", "body", "hint"}
    assert out["status_code"] == status
    assert out["body"] == "nope"


@pytest.mark.parametrize("row", WRITE_ROWS, ids=[r[0] for r in WRITE_ROWS])
async def test_read_only_blocks_write(
    readonly_client: tuple[Client, respx.MockRouter], row: tuple[Any, ...]
) -> None:
    tool, args, *_ = row
    client, router = readonly_client
    is_error, out = await _call(client, tool, args)
    assert is_error is True
    assert "CODA_READ_ONLY" in out["error"]
    assert not router.calls


async def test_api_error_is_an_error_result_with_hint(
    tool_client: tuple[Client, respx.MockRouter],
) -> None:
    """A 404 is an isError result with an actionable hint; its body is text only."""
    client, router = tool_client
    router.get("/docs/d1").mock(return_value=Response(404, text="gone"))
    result = await client.call_tool("coda_get_doc", {"doc_id": "d1"}, raise_on_error=False)
    assert result.is_error is True
    out = json.loads(result.content[0].text)
    assert "isError" not in out  # D-X1D3: the flag lives on the result, not the body
    assert out["status_code"] == 404
    assert out["hint"]
    assert result.structured_content is None


async def _assert_error_result(client: Client, tool: str, args: dict[str, Any]) -> None:
    """Call fails as an isError result whose body is the text content, no structuredContent."""
    result = await client.call_tool(tool, args, raise_on_error=False)
    assert result.is_error is True
    body = json.loads(result.content[0].text)
    assert "isError" not in body
    assert body["error"]
    assert result.structured_content is None


async def test_every_expected_failure_is_an_error_result(
    tool_client: tuple[Client, respx.MockRouter],
) -> None:
    """API-origin failure types land as isError results carrying the error body as text."""
    client, router = tool_client
    router.get("/docs/d1").mock(return_value=Response(404, text="gone"))  # CodaApiError
    await _assert_error_result(client, "coda_get_doc", {"doc_id": "d1"})
    router.get("/whoami").mock(return_value=Response(401, text="bad token"))  # CodaAuthError
    await _assert_error_result(client, "coda_whoami", {})
    router.get("/docs/d2").mock(return_value=Response(429, text="slow down"))  # CodaRateLimitError
    await _assert_error_result(client, "coda_get_doc", {"doc_id": "d2"})


async def test_read_only_failure_is_an_error_result(
    readonly_client: tuple[Client, respx.MockRouter],
) -> None:
    """CodaWriteDisabledError (read-only) is an isError result carrying the error body as text."""
    client, _ = readonly_client
    await _assert_error_result(client, "coda_create_doc", {"title": "x"})


async def test_unexpected_failure_is_a_tool_error(
    tool_client: tuple[Client, respx.MockRouter],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A bug in a tool body surfaces as isError=True with the exception named, and is logged."""

    async def boom(self: CodaClient, path: str, params: Any = None) -> Any:
        msg = "schema changed"
        raise RuntimeError(msg)

    monkeypatch.setattr(CodaClient, "get", boom)
    client, _ = tool_client
    with caplog.at_level("ERROR", logger="mcp_coda.servers._helpers"):
        result = await client.call_tool("coda_get_doc", {"doc_id": "d1"}, raise_on_error=False)
    assert result.is_error is True
    assert result.structured_content is None
    assert "RuntimeError: schema changed" in result.content[0].text
    assert "coda_get_doc failed" in caplog.text
    assert "Traceback" in caplog.text


_OUTPUT_SCHEMAS = {t.name: t.output_schema for t in asyncio.run(mcp.list_tools())}


@pytest.mark.parametrize("row", HTTP_ROWS, ids=[r[0] for r in HTTP_ROWS])
async def test_error_result_passes_strict_output_schema(
    tool_client: tuple[Client, respx.MockRouter], row: tuple[Any, ...]
) -> None:
    """Guard: the TS MCP SDK validates structuredContent even when isError is true.

    An error result must therefore carry no structuredContent, or one that matches
    the tool's outputSchema; otherwise callTool throws McpError and the error text
    and hint are lost in Claude Code / Cursor / VS Code.
    """
    tool, args, method, path, _, _ = row
    client, router = tool_client
    status = 401 if tool == "coda_whoami" else 404
    router.request(method, path).mock(return_value=Response(status, text="nope"))
    result = await client.call_tool(tool, args, raise_on_error=False)
    assert result.is_error is True
    if result.structured_content is not None:
        jsonschema.validate(result.structured_content, _OUTPUT_SCHEMAS[tool])


def test_no_tool_advertises_a_wrapped_schema() -> None:
    """Shape C: no tool carries fastmcp's `{"result": …}` wrapper schema.

    Every tool's `output_schema` is None (a typed schema is opt-in per tool
    later via `@mcp.tool(output_schema=…)`); when one is present it must be an
    object schema without `x-fastmcp-wrap-result`. Fails on pre-X2 code, where
    every `-> str` tool advertised `{..., "x-fastmcp-wrap-result": true}`.
    """
    for t in asyncio.run(mcp.list_tools()):
        schema = t.output_schema
        assert schema is None or (
            schema.get("type") == "object" and "x-fastmcp-wrap-result" not in schema
        ), (t.name, schema)


async def test_success_text_is_pinned_pretty_json(
    tool_client: tuple[Client, respx.MockRouter],
) -> None:
    """Golden pin: success text is byte-identical pretty JSON and structuredContent
    is the same object (no `{"result": "<json>"}` wrapper)."""
    client, router = tool_client
    expected = {"id": "d1", "name": "My Doc"}
    router.get("/docs/d1").mock(return_value=Response(200, json=expected))
    result = await client.call_tool("coda_get_doc", {"doc_id": "d1"}, raise_on_error=False)
    assert result.is_error is False
    assert result.content[0].text == json.dumps(expected, indent=2, ensure_ascii=False)
    assert result.structured_content == expected


async def test_markdown_result_is_text_only(
    tool_client: tuple[Client, respx.MockRouter],
) -> None:
    """The two markdown tools return text only — no structuredContent (not JSON)."""
    client, router = tool_client
    router.get("/docs").mock(
        return_value=Response(200, json={"items": [{"id": "d1", "name": "Doc"}]})
    )
    result = await client.call_tool(
        "coda_list_docs", {"response_format": "markdown"}, raise_on_error=False
    )
    assert result.is_error is False
    assert result.structured_content is None
    assert "**Doc**" in result.content[0].text


async def test_oversized_single_payload_is_text_only(
    tool_client: tuple[Client, respx.MockRouter],
) -> None:
    """A single non-list payload too large to fit is sliced to text, so it carries
    no structuredContent (the sliced string is not valid JSON)."""
    client, router = tool_client
    router.get("/docs/d1").mock(return_value=Response(200, json={"id": "d1", "blob": "x" * 30000}))
    result = await client.call_tool("coda_get_doc", {"doc_id": "d1"}, raise_on_error=False)
    assert result.is_error is False
    assert result.structured_content is None
    assert "truncated" in result.content[0].text


def _tools_decorated_write() -> set[str]:
    """Scan servers/*.py for async tools carrying `@tool_result(write=True)`.

    Read from source (AST), independent of the registered tags, so this and
    WRITE_TOOLS (derived from `tags`) can only agree if the decorator and the
    "write" tag are declared together on every write tool.
    """
    names: set[str] = set()
    for path in _SERVERS_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            for dec in node.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == "tool_result"
                    and any(
                        kw.arg == "write"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                        for kw in dec.keywords
                    )
                ):
                    names.add(node.name)
    return names


def test_write_decorator_matches_write_tag() -> None:
    """Every `@tool_result(write=True)` tool is tagged "write", and vice versa.

    A write tool missing `write=True` would skip `_check_write`, running in
    read-only mode; one missing the tag would not be blocked by CODA_READ_ONLY.
    """
    assert _tools_decorated_write() == WRITE_TOOLS


async def test_list_rows_sort_by_is_enum(
    tool_client: tuple[Client, respx.MockRouter],
) -> None:
    """CO-R04: sort_by is the API's sortBy enum, not a free-form column string.

    On origin/main sort_by was a bare `str` (its description told the model to
    pass '-Created'), so the schema carried no enum and the upstream API 400'd.
    """
    client, _ = tool_client
    tools = {t.name: t for t in await client.list_tools()}
    sort_by = tools["coda_list_rows"].input_schema["properties"]["sort_by"]
    flat = json.dumps(sort_by)
    assert "createdAt" in flat
    assert "natural" in flat
    assert "updatedAt" in flat
