"""Shared helper functions for tool modules."""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Any

from fastmcp import Context

from ..client import CodaClient
from ..config import CodaConfig
from ..exceptions import CodaApiError, CodaRateLimitError, CodaWriteDisabledError

# Maximum response size in characters. Responses exceeding this are truncated
# to prevent context window blowout in LLM consumers.
CHARACTER_LIMIT = 25000

# Matches: https://coda.io/d/<Slug>_d<DocId>  (browser URL format)
_CODA_DOC_URL_RE = re.compile(r"https?://[^/]+/d/[^/]+_d([a-zA-Z0-9_-]+)")

_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_id(value: str, name: str) -> None:
    """Validate that *value* looks like a safe Coda object identifier."""
    if not value or not _ID_RE.match(value):
        msg = f"Invalid {name}: {value!r}"
        raise ValueError(msg)


def _parse_coda_doc_url(value: str) -> str:
    """Extract doc_id from a Coda browser URL.

    If *value* is not a URL, returns it unchanged (assumes it's already a doc ID).
    Handles: https://coda.io/d/DocTitle_dABCdef123
    """
    if not value.startswith(("http://", "https://")):
        return value
    m = _CODA_DOC_URL_RE.match(value)
    if m:
        return m.group(1)
    return value


@functools.cache
def _load_file(base_dir: str, filename: str) -> str:
    """Load a file from the given directory with path traversal protection.

    Results are cached — static files do not change at runtime.
    """
    if "/" in filename or "\\" in filename or ".." in filename:
        msg = f"Invalid filename: {filename}"
        raise ValueError(msg)
    base = Path(base_dir)
    path = base / filename
    if not path.resolve().is_relative_to(base.resolve()):
        msg = f"Invalid filename: {filename}"
        raise ValueError(msg)
    return path.read_text(encoding="utf-8")


def _get_client(ctx: Context) -> CodaClient:
    """Retrieve the CodaClient from lifespan context."""
    return ctx.request_context.lifespan_context["client"]


def _get_config(ctx: Context) -> CodaConfig:
    """Retrieve the CodaConfig from lifespan context."""
    return ctx.request_context.lifespan_context["config"]


def _check_write(ctx: Context) -> None:
    """Raise if write operations are disabled."""
    if _get_config(ctx).read_only:
        raise CodaWriteDisabledError


def _truncate(text: str) -> str:
    """Truncate text exceeding CHARACTER_LIMIT with a notice."""
    if len(text) <= CHARACTER_LIMIT:
        return text
    return text[:CHARACTER_LIMIT] + (
        "\n\n... [truncated — response exceeded "
        f"{CHARACTER_LIMIT} characters. Use pagination or filters to narrow results.]"
    )


def _ok(data: Any) -> str:
    """Serialize a successful response to JSON string, with truncation guard."""
    result = json.dumps(data, indent=2, ensure_ascii=False)
    return _truncate(result)


def _ok_markdown(text: str) -> str:
    """Return a markdown-formatted response, with truncation guard."""
    return _truncate(text)


def _format_list_as_markdown(
    items: list[dict[str, Any]],
    *,
    has_more: bool = False,
    next_cursor: str | None = None,
    total_count: int = 0,
    name_key: str = "name",
    id_key: str = "id",
) -> str:
    """Format a list response as human-readable markdown."""
    lines: list[str] = []
    for item in items:
        name = item.get(name_key, "Untitled")
        item_id = item.get(id_key, "")
        line = f"- **{name}** (`{item_id}`)"
        # Add any extra useful fields
        if "type" in item:
            line += f" — {item['type']}"
        if "owner" in item:
            line += f" — owner: {item['owner']}"
        if "browserLink" in item:
            line += f"\n  {item['browserLink']}"
        lines.append(line)
    if not lines:
        lines.append("*No results found.*")
    footer = f"\n\n{total_count} items returned"
    if has_more:
        footer += f" (more available, cursor: `{next_cursor}`)"
    return "\n".join(lines) + footer


def _err(error: Exception) -> str:
    """Serialize an error response to JSON string with recovery hints."""
    detail: dict[str, Any] = {"isError": True, "error": str(error)}
    if isinstance(error, CodaRateLimitError):
        detail["status_code"] = 429
        detail["retry_after"] = error.retry_after
    elif isinstance(error, CodaApiError):
        detail["status_code"] = error.status_code
        detail["body"] = error.body
    return json.dumps(detail, indent=2, ensure_ascii=False)
