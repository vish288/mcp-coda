"""Tests for server helper functions."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import (
    CodaApiError,
    CodaRateLimitError,
    CodaWriteDisabledError,
)
from mcp_coda.servers._helpers import (
    CHARACTER_LIMIT,
    _check_write,
    _err,
    _ok,
    _ok_markdown,
    _truncate,
)


def _make_ctx(read_only: bool = False) -> MagicMock:
    """Create a mock Context with lifespan_context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "config": CodaConfig(token="tok", read_only=read_only),
        "client": MagicMock(),
    }
    return ctx


class TestOk:
    def test_serializes_dict(self) -> None:
        result = _ok({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_serializes_list(self) -> None:
        result = _ok([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_handles_unicode(self) -> None:
        result = _ok({"name": "café"})
        assert "café" in result

    def test_indented(self) -> None:
        result = _ok({"a": 1})
        assert "\n" in result

    def test_truncates_large_response(self) -> None:
        large_data = {"items": ["x" * 100 for _ in range(500)]}
        result = _ok(large_data)
        assert len(result) <= CHARACTER_LIMIT + 200  # truncation notice overhead
        assert "truncated" in result


class TestOkMarkdown:
    def test_returns_text(self) -> None:
        result = _ok_markdown("# Hello\n\nSome content")
        assert result == "# Hello\n\nSome content"

    def test_truncates_large_markdown(self) -> None:
        large_text = "x" * (CHARACTER_LIMIT + 1000)
        result = _ok_markdown(large_text)
        assert len(result) <= CHARACTER_LIMIT + 200
        assert "truncated" in result


class TestTruncate:
    def test_short_text_unchanged(self) -> None:
        assert _truncate("hello") == "hello"

    def test_exact_limit_unchanged(self) -> None:
        text = "a" * CHARACTER_LIMIT
        assert _truncate(text) == text

    def test_over_limit_truncated(self) -> None:
        text = "a" * (CHARACTER_LIMIT + 100)
        result = _truncate(text)
        assert result.startswith("a" * CHARACTER_LIMIT)
        assert "truncated" in result
        assert str(CHARACTER_LIMIT) in result


class TestErr:
    def test_generic_exception(self) -> None:
        result = json.loads(_err(ValueError("bad input")))
        assert result["error"] == "bad input"
        assert result["isError"] is True
        assert "status_code" not in result

    def test_api_error(self) -> None:
        result = json.loads(_err(CodaApiError(500, "ISE", "details")))
        assert result["status_code"] == 500
        assert result["body"] == "details"
        assert result["isError"] is True

    def test_rate_limit_error(self) -> None:
        result = json.loads(_err(CodaRateLimitError(retry_after=3)))
        assert result["status_code"] == 429
        assert result["retry_after"] == 3
        assert result["isError"] is True

    def test_write_disabled_error(self) -> None:
        result = json.loads(_err(CodaWriteDisabledError()))
        assert "CODA_READ_ONLY" in result["error"]
        assert result["isError"] is True
        assert "status_code" not in result


class TestCheckWrite:
    def test_allows_when_not_read_only(self) -> None:
        ctx = _make_ctx(read_only=False)
        _check_write(ctx)  # should not raise

    def test_raises_when_read_only(self) -> None:
        ctx = _make_ctx(read_only=True)
        with pytest.raises(CodaWriteDisabledError):
            _check_write(ctx)
