"""CO-R01: every interpolated path segment is percent-encoded.

Before the fix, IDs and names were interpolated into the path raw. A `#` or `?`
ended the path (so a DELETE landed on a parent resource), and `/` or `%`
corrupted it. These go through the real CodaClient so the assertion is the exact
URL httpx puts on the wire.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
import respx

from mcp_coda.client import CodaClient
from mcp_coda.config import CodaConfig
from mcp_coda.servers import docs, pages, rows, tables
from mcp_coda.servers._helpers import _p
from tests.conftest import TEST_BASE_URL, TEST_TOKEN


def _fn(tool: object) -> object:
    """Unwrap a FunctionTool to its raw function (handles plain functions too)."""
    return getattr(tool, "fn", tool)


coda_get_doc = _fn(docs.coda_get_doc)
coda_delete_page = _fn(pages.coda_delete_page)
coda_delete_page_content = _fn(pages.coda_delete_page_content)
coda_delete_row = _fn(rows.coda_delete_row)
coda_list_rows = _fn(rows.coda_list_rows)
coda_get_table = _fn(tables.coda_get_table)


def _ctx(client: CodaClient) -> MagicMock:
    ctx = MagicMock()
    ctx.lifespan_context = {
        "config": CodaConfig(token=TEST_TOKEN),
        "client": client,
    }
    return ctx


class TestPathBuilder:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("#42", "%2342"),
            ("FAQ?", "FAQ%3F"),
            ("a/b", "a%2Fb"),
            ("50%", "50%25"),
            ("Q3/Q4 plan", "Q3%2FQ4%20plan"),
        ],
    )
    def test_segment_is_encoded(self, name: str, expected: str) -> None:
        assert _p("docs", name) == f"/docs/{expected}"

    @pytest.mark.parametrize("bad", [".", ".."])
    def test_dot_segments_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError, match="Unsafe path segment"):
            _p("docs", bad)

    def test_ordinary_ids_unchanged(self) -> None:
        assert _p("docs", "dAbc123", "pages", "canvas-1") == "/docs/dAbc123/pages/canvas-1"


async def _capture(method: str, call) -> httpx.Request:
    async with respx.mock(base_url=TEST_BASE_URL) as router:
        route = router.route(method=method).mock(
            return_value=httpx.Response(200, json={"id": "ok"})
        )
        client = CodaClient(CodaConfig(token=TEST_TOKEN, base_url=TEST_BASE_URL))
        try:
            await call(client)
        finally:
            await client.close()
        return route.calls.last.request


def _path(req: httpx.Request) -> str:
    """Encoded path only (raw_path carries the query string for GETs)."""
    return req.url.raw_path.decode().split("?", 1)[0]


class TestToolsEncodeSegments:
    """Hostile IDs/names must reach the encoded resource, not a parent one."""

    async def test_delete_page_content_hash_doc_id(self) -> None:
        # Repro from the review: dAbc# used to send DELETE /docs/dAbc (doc delete).
        req = await _capture(
            "DELETE",
            lambda c: coda_delete_page_content(_ctx(c), doc_id="dAbc#", page_id_or_name="canvas-1"),
        )
        assert _path(req) == "/apis/v1/docs/dAbc%23/pages/canvas-1/content"

    async def test_delete_row_question_mark_name(self) -> None:
        req = await _capture(
            "DELETE",
            lambda c: coda_delete_row(
                _ctx(c), doc_id="d1", table_id_or_name="Tasks", row_id_or_name="Fix login?"
            ),
        )
        assert _path(req) == ("/apis/v1/docs/d1/tables/Tasks/rows/Fix%20login%3F")

    async def test_delete_page_slash_in_name(self) -> None:
        req = await _capture(
            "DELETE",
            lambda c: coda_delete_page(_ctx(c), doc_id="d1", page_id_or_name="Q3/Q4 plan"),
        )
        assert _path(req) == "/apis/v1/docs/d1/pages/Q3%2FQ4%20plan"

    async def test_list_rows_question_mark_table(self) -> None:
        req = await _capture(
            "GET",
            lambda c: coda_list_rows(_ctx(c), doc_id="d1", table_id_or_name="Tasks?x=1"),
        )
        assert _path(req) == "/apis/v1/docs/d1/tables/Tasks%3Fx%3D1/rows"

    async def test_get_table_percent_in_name(self) -> None:
        req = await _capture(
            "GET",
            lambda c: coda_get_table(_ctx(c), doc_id="d1", table_id_or_name="100% done"),
        )
        assert _path(req) == "/apis/v1/docs/d1/tables/100%25%20done"

    async def test_get_doc_hash(self) -> None:
        req = await _capture(
            "GET",
            lambda c: coda_get_doc(_ctx(c), doc_id="d#1"),
        )
        assert _path(req) == "/apis/v1/docs/d%231"
