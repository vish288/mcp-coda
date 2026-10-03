"""CLI entry point tests."""

from __future__ import annotations

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
