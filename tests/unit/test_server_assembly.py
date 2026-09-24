"""Boot the real server (real lifespan, env-driven config) and count what it exposes.

The counts are re-derived by scanning src/ for decorators at test time, so a
module dropped from `_modules` or a decorator that silently fails to register
shows up as a mismatch rather than a smaller number nobody notices.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import respx
from fastmcp import Client
from httpx import Response

from mcp_coda.servers import mcp
from tests.conftest import TEST_BASE_URL

SERVERS = Path(__file__).resolve().parents[2] / "src" / "mcp_coda" / "servers"


def _decorators(kind: str) -> int:
    pattern = re.compile(rf"@mcp\.{kind}\(")
    return sum(len(pattern.findall(p.read_text(encoding="utf-8"))) for p in SERVERS.glob("*.py"))


@pytest.fixture
async def live_client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Client]:
    monkeypatch.setenv("CODA_API_TOKEN", "tok")
    monkeypatch.setenv("CODA_BASE_URL", TEST_BASE_URL)
    monkeypatch.delenv("CODA_READ_ONLY", raising=False)
    with respx.mock(base_url=TEST_BASE_URL, assert_all_called=False) as router:
        router.get("/docs").mock(return_value=Response(200, json={"items": [{"id": "d1"}]}))
        router.get("/docs/d1/tables").mock(return_value=Response(200, json={"items": []}))
        async with Client(mcp) as client:
            yield client


async def test_tool_count_matches_source(live_client: Client) -> None:
    expected = _decorators("tool")
    assert expected > 0
    tools = await live_client.list_tools()
    assert len(tools) == expected
    assert len({t.name for t in tools}) == expected


async def test_every_resource_reads(live_client: Client) -> None:
    resources = await live_client.list_resources()
    templates = await live_client.list_resource_templates()
    assert resources and templates
    assert len(resources) + len(templates) == _decorators("resource")
    uris = [str(r.uri) for r in resources] + ["coda://docs/d1/schema"]
    for uri in uris:
        text = (await live_client.read_resource(uri))[0].text
        assert text, uri
        if uri.startswith("coda://"):
            assert "isError" not in json.loads(text), uri


async def test_prompts_registered(live_client: Client) -> None:
    prompts = await live_client.list_prompts()
    assert prompts
    assert len(prompts) == _decorators("prompt")
