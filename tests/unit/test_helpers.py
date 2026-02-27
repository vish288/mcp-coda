"""Tests for server helper functions."""

from __future__ import annotations

import json
from pathlib import Path
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
    _format_list_as_markdown,
    _get_client,
    _get_config,
    _load_file,
    _ok,
    _ok_markdown,
    _parse_coda_doc_url,
    _truncate,
    _validate_id,
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
        result = _ok({"name": "caf\u00e9"})
        assert "caf\u00e9" in result

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


class TestGetClient:
    def test_returns_client_from_context(self) -> None:
        ctx = _make_ctx()
        client = _get_client(ctx)
        assert client is ctx.request_context.lifespan_context["client"]


class TestGetConfig:
    def test_returns_config_from_context(self) -> None:
        ctx = _make_ctx()
        config = _get_config(ctx)
        assert config is ctx.request_context.lifespan_context["config"]


class TestFormatListAsMarkdown:
    def test_basic_items(self) -> None:
        items = [
            {"id": "d1", "name": "Doc One"},
            {"id": "d2", "name": "Doc Two"},
        ]
        result = _format_list_as_markdown(items, total_count=2)
        assert "**Doc One** (`d1`)" in result
        assert "**Doc Two** (`d2`)" in result
        assert "2 items returned" in result

    def test_empty_list(self) -> None:
        result = _format_list_as_markdown([], total_count=0)
        assert "*No results found.*" in result
        assert "0 items returned" in result

    def test_has_more_with_cursor(self) -> None:
        items = [{"id": "d1", "name": "Doc"}]
        result = _format_list_as_markdown(items, has_more=True, next_cursor="abc", total_count=1)
        assert "more available" in result
        assert "abc" in result

    def test_item_with_type(self) -> None:
        items = [{"id": "d1", "name": "My Doc", "type": "doc"}]
        result = _format_list_as_markdown(items, total_count=1)
        assert "doc" in result

    def test_item_with_owner(self) -> None:
        items = [{"id": "d1", "name": "My Doc", "owner": "user@test.com"}]
        result = _format_list_as_markdown(items, total_count=1)
        assert "user@test.com" in result

    def test_item_with_browser_link(self) -> None:
        items = [{"id": "d1", "name": "My Doc", "browserLink": "https://coda.io/d/d1"}]
        result = _format_list_as_markdown(items, total_count=1)
        assert "https://coda.io/d/d1" in result

    def test_custom_keys(self) -> None:
        items = [{"docId": "d1", "title": "Doc Title"}]
        result = _format_list_as_markdown(items, total_count=1, name_key="title", id_key="docId")
        assert "**Doc Title** (`d1`)" in result

    def test_missing_keys_use_defaults(self) -> None:
        items = [{"other": "field"}]
        result = _format_list_as_markdown(items, total_count=1)
        assert "**Untitled**" in result


class TestLoadFile:
    """Tests for the shared _load_file helper."""

    def setup_method(self) -> None:
        # Clear cache between tests to avoid cross-test pollution
        _load_file.cache_clear()

    def test_loads_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "test.md").write_text("hello world", encoding="utf-8")
        result = _load_file(str(tmp_path), "test.md")
        assert result == "hello world"

    def test_caches_result(self, tmp_path: Path) -> None:
        (tmp_path / "cached.md").write_text("original", encoding="utf-8")
        result1 = _load_file(str(tmp_path), "cached.md")
        (tmp_path / "cached.md").write_text("modified", encoding="utf-8")
        result2 = _load_file(str(tmp_path), "cached.md")
        assert result1 == result2 == "original"

    def test_rejects_slash(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid filename"):
            _load_file(str(tmp_path), "../etc/passwd")

    def test_rejects_backslash(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid filename"):
            _load_file(str(tmp_path), "..\\etc\\passwd")

    def test_rejects_dotdot(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid filename"):
            _load_file(str(tmp_path), "..")

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _load_file(str(tmp_path), "nonexistent.md")


class TestValidateId:
    """Tests for the _validate_id helper."""

    def test_accepts_alphanumeric(self) -> None:
        _validate_id("abc123", "doc_id")  # should not raise

    def test_accepts_hyphens_underscores(self) -> None:
        _validate_id("my-doc_v2", "doc_id")  # should not raise

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="Invalid doc_id"):
            _validate_id("", "doc_id")

    def test_rejects_slash(self) -> None:
        with pytest.raises(ValueError, match="Invalid doc_id"):
            _validate_id("../etc/passwd", "doc_id")

    def test_rejects_spaces(self) -> None:
        with pytest.raises(ValueError, match="Invalid doc_id"):
            _validate_id("has space", "doc_id")

    def test_rejects_special_chars(self) -> None:
        with pytest.raises(ValueError, match="Invalid doc_id"):
            _validate_id("id;DROP TABLE", "doc_id")


class TestParseCodaDocUrl:
    """Tests for _parse_coda_doc_url."""

    def test_extracts_doc_id_from_url(self) -> None:
        url = "https://coda.io/d/My-Doc-Title_dABCdef123"
        assert _parse_coda_doc_url(url) == "ABCdef123"

    def test_plain_id_passthrough(self) -> None:
        assert _parse_coda_doc_url("ABCdef123") == "ABCdef123"

    def test_url_with_page_suffix(self) -> None:
        url = "https://coda.io/d/MyDoc_dABC123/PageName_sXYZ"
        assert _parse_coda_doc_url(url) == "ABC123"

    def test_non_coda_url_passthrough(self) -> None:
        url = "https://example.com/some/path"
        assert _parse_coda_doc_url(url) == url

    def test_empty_string_passthrough(self) -> None:
        assert _parse_coda_doc_url("") == ""
