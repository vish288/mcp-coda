"""CLI entry point tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from click.testing import CliRunner

from mcp_coda import _BearerTokenVerifier, main
from mcp_coda.servers import mcp as server_mcp

_TOKEN32 = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _reset_auth() -> Iterator[None]:
    """main() mutates the module-level server's auth; keep tests isolated."""
    yield
    server_mcp.auth = None


def test_sse_deprecation_warning(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Warn when --transport sse is used."""
    monkeypatch.setenv("CODA_API_TOKEN", "tok")
    with patch.object(server_mcp, "run_async", new_callable=AsyncMock) as mock_run:
        result = runner.invoke(main, ["--transport", "sse"])
        assert result.exit_code == 0
        assert "Warning: --transport sse uses the HTTP+SSE transport" in result.stderr
        assert "deprecated in MCP 2026-07-28" in result.stderr
        assert "Use --transport streamable-http" in result.stderr
        mock_run.assert_called_once()


def test_coda_token_flag_hidden_from_help(runner: CliRunner) -> None:
    """--coda-token is deprecated and hidden from --help; --read-only stays visible."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--coda-token" not in result.output
    assert "--read-only" in result.output


def test_coda_token_flag_still_works_and_warns(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Passing --coda-token still configures the token but warns once on stderr."""
    # setenv first so monkeypatch records an undo entry; the CLI writes
    # CODA_API_TOKEN directly, and delenv alone on an absent var would not
    # register a restore, leaking the token into later tests.
    monkeypatch.setenv("CODA_API_TOKEN", "placeholder")
    monkeypatch.delenv("CODA_API_TOKEN")
    monkeypatch.delenv("CODA_TOKEN", raising=False)
    monkeypatch.delenv("CODA_PAT", raising=False)
    with patch.object(server_mcp, "run_async", new_callable=AsyncMock) as mock_run:
        result = runner.invoke(main, ["--coda-token", "argv-tok"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        assert os.environ["CODA_API_TOKEN"] == "argv-tok"
        assert "--coda-token is deprecated" in result.stderr
        assert "CODA_API_TOKEN" in result.stderr
        assert "deprecated" not in result.stdout


def test_env_coda_token_does_not_warn(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    """A token supplied via the env var does not emit the deprecation warning."""
    monkeypatch.setenv("CODA_API_TOKEN", "env-tok")
    with patch.object(server_mcp, "run_async", new_callable=AsyncMock) as mock_run:
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        assert "deprecated" not in result.stderr


class TestHttpBearerToken:
    """CO-R17: an HTTP transport on a non-loopback host needs a bearer token."""

    def test_non_loopback_without_token_exits(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CODA_API_TOKEN", "tok")
        monkeypatch.delenv("CODA_HTTP_BEARER_TOKEN", raising=False)
        with patch.object(server_mcp, "run_async", new_callable=AsyncMock) as mock_run:
            result = runner.invoke(main, ["--transport", "streamable-http", "--host", "0.0.0.0"])
        assert result.exit_code == 2
        assert "CODA_HTTP_BEARER_TOKEN" in result.output
        mock_run.assert_not_called()

    def test_token_sets_static_auth(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CODA_API_TOKEN", "tok")
        monkeypatch.setenv("CODA_HTTP_BEARER_TOKEN", _TOKEN32)
        with patch.object(server_mcp, "run_async", new_callable=AsyncMock) as mock_run:
            result = runner.invoke(main, ["--transport", "streamable-http", "--host", "0.0.0.0"])
        assert result.exit_code == 0
        assert isinstance(server_mcp.auth, _BearerTokenVerifier)
        mock_run.assert_called_once()

    def test_loopback_without_token_no_auth(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CODA_API_TOKEN", "tok")
        monkeypatch.delenv("CODA_HTTP_BEARER_TOKEN", raising=False)
        with patch.object(server_mcp, "run_async", new_callable=AsyncMock) as mock_run:
            result = runner.invoke(main, ["--transport", "streamable-http", "--host", "127.0.0.1"])
        assert result.exit_code == 0
        assert server_mcp.auth is None
        mock_run.assert_called_once()

    def test_short_token_exits(self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODA_API_TOKEN", "tok")
        monkeypatch.setenv("CODA_HTTP_BEARER_TOKEN", "deadbeef")  # 8 chars
        with patch.object(server_mcp, "run_async", new_callable=AsyncMock) as mock_run:
            result = runner.invoke(main, ["--transport", "streamable-http", "--host", "0.0.0.0"])
        assert result.exit_code == 2
        assert "at least 16" in result.output
        mock_run.assert_not_called()

    def test_stdio_ignores_token(self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODA_API_TOKEN", "tok")
        monkeypatch.setenv("CODA_HTTP_BEARER_TOKEN", _TOKEN32)
        with patch.object(server_mcp, "run_async", new_callable=AsyncMock) as mock_run:
            result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert server_mcp.auth is None
        mock_run.assert_called_once()


async def test_bearer_middleware_streamable_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wire check: with auth set, the streamable-http ASGI app enforces the token."""
    monkeypatch.setenv("CODA_API_TOKEN", "tok")
    # These two boot the real lifespan (app.router.lifespan_context), so strip the
    # read-only env vars: a MCP_READ_ONLY=true gate run would otherwise lock the shared
    # server mid-test and leak the hide into every later tool_client test.
    monkeypatch.delenv("MCP_READ_ONLY", raising=False)
    monkeypatch.delenv("CODA_READ_ONLY", raising=False)
    server_mcp.auth = _BearerTokenVerifier(_TOKEN32)
    try:
        app = server_mcp.http_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            async with app.router.lifespan_context(app):
                no_header = await client.post("/mcp", json={})
                wrong_token = await client.post(
                    "/mcp", json={}, headers={"Authorization": "Bearer wrong-token-value"}
                )
                # Non-ASCII must be rejected, not crash: compare_digest raises
                # TypeError on a non-ASCII str, which would 500 with a traceback.
                # HTTP headers are latin-1, so send raw bytes — httpx refuses to
                # ascii-encode a non-ASCII str value, but a real client can send
                # these bytes on the wire.
                non_ascii = await client.post(
                    "/mcp", json={}, headers={"Authorization": "Bearer café".encode("latin-1")}
                )
                with_header = await client.post(
                    "/mcp", json={}, headers={"Authorization": f"Bearer {_TOKEN32}"}
                )
        assert no_header.status_code == 401
        assert wrong_token.status_code == 401
        assert non_ascii.status_code == 401
        # The middleware ran and let the authenticated request through to the
        # endpoint; any non-401 status proves that.
        assert with_header.status_code != 401
    finally:
        server_mcp.auth = None


async def test_bearer_middleware_sse(monkeypatch: pytest.MonkeyPatch) -> None:
    """The bearer guard also covers the (deprecated) SSE transport endpoint."""
    monkeypatch.setenv("CODA_API_TOKEN", "tok")
    # These two boot the real lifespan (app.router.lifespan_context), so strip the
    # read-only env vars: a MCP_READ_ONLY=true gate run would otherwise lock the shared
    # server mid-test and leak the hide into every later tool_client test.
    monkeypatch.delenv("MCP_READ_ONLY", raising=False)
    monkeypatch.delenv("CODA_READ_ONLY", raising=False)
    server_mcp.auth = _BearerTokenVerifier(_TOKEN32)
    try:
        app = server_mcp.http_app(transport="sse")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            async with app.router.lifespan_context(app):
                no_header = await client.get("/sse")
        assert no_header.status_code == 401
    finally:
        server_mcp.auth = None


def test_missing_config_exits_2_with_one_line(runner: CliRunner) -> None:
    """D7: a missing token is one clear ``Error:`` line and exit 2, not a traceback."""
    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(main, [])
    assert result.exit_code == 2
    lines = [ln for ln in result.stderr.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert lines[0].startswith("Error:")
    assert "CODA_API_TOKEN" in lines[0]
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_invalid_timeout_exits_2(runner: CliRunner) -> None:
    """A bad CODA_TIMEOUT is surfaced as the same one-line exit-2 error."""
    with patch.dict(os.environ, {"CODA_API_TOKEN": "tok", "CODA_TIMEOUT": "abc"}, clear=True):
        result = runner.invoke(main, [])
    assert result.exit_code == 2
    assert "CODA_TIMEOUT" in result.stderr
