"""CLI entry point tests."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mcp_coda import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_sse_deprecation_warning(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Warn when --transport sse is used."""
    monkeypatch.setenv("CODA_API_TOKEN", "tok")
    with patch("mcp_coda.asyncio.run") as mock_run:
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
    with patch("mcp_coda.asyncio.run") as mock_run:
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
    with patch("mcp_coda.asyncio.run") as mock_run:
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        assert "deprecated" not in result.stderr
