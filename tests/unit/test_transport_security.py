"""CO-R02: streamable-http validates Host/Origin (DNS-rebinding protection).

Before the fix the CLI ran the HTTP transports with no Host/Origin guard, so a
rebinding page could POST to the loopback server and drive tools with the user's
token. The CLI now passes host_origin_protection="auto", which rejects foreign
Host (421) and cross-site Origin (403) while allowing localhost/127.0.0.1.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner

from mcp_coda import main
from mcp_coda.servers import mcp

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2026-07-28",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_streamable_http_enables_host_origin_protection(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODA_API_TOKEN", "tok")
    with (
        patch("mcp_coda.asyncio.run") as mock_run,
        patch("mcp_coda.servers.mcp.run_async", new_callable=MagicMock) as mock_run_async,
    ):
        result = runner.invoke(main, ["--transport", "streamable-http", "--port", "18770"])
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        assert mock_run_async.call_args.kwargs["host_origin_protection"] == "auto"


def test_stdio_has_no_host_origin_protection(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODA_API_TOKEN", "tok")
    with (
        patch("mcp_coda.asyncio.run"),
        patch("mcp_coda.servers.mcp.run_async", new_callable=MagicMock) as mock_run_async,
    ):
        runner.invoke(main, [])
        assert "host_origin_protection" not in mock_run_async.call_args.kwargs


async def _post(headers: dict[str, str]) -> httpx.Response:
    app = mcp.http_app(transport="streamable-http", host_origin_protection="auto")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:18770") as client:
        return await client.post("/mcp", json=_INIT, headers=headers)


async def test_foreign_origin_rejected() -> None:
    resp = await _post(
        {
            "Host": "127.0.0.1:18770",
            "Origin": "http://evil.example",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
    )
    assert resp.status_code == 403


async def test_foreign_host_rejected() -> None:
    resp = await _post(
        {
            "Host": "evil.example",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
    )
    assert resp.status_code == 421
