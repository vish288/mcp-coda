"""Shared helper functions for tool modules."""

from __future__ import annotations

import functools
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import Field

from ..client import CodaClient
from ..config import CodaConfig
from ..exceptions import CodaApiError, CodaError, CodaRateLimitError, CodaWriteDisabledError

# Shared parameter type aliases
DocId = Annotated[str, Field(description="The doc ID containing the table")]
Cursor = Annotated[str | None, Field(description="Pagination cursor from a previous response")]
Limit = Annotated[int, Field(description="Maximum number of results (1-200)", ge=1, le=200)]

_log = logging.getLogger(__name__)

# Maximum response size in characters. Responses exceeding this are truncated
# to prevent context window blowout in LLM consumers.
CHARACTER_LIMIT = 25000

# Matches: https://coda.io/d/<Slug>_d<DocId>  (browser URL format)
_CODA_DOC_URL_RE = re.compile(r"https?://[^/]+/d/[^/]+_d([a-zA-Z0-9_-]+)")

_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


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


def _p(*segments: str) -> str:
    """Build an API path from segments, percent-encoding each one.

    Doc/page/table/row IDs and names reach us from a model and are untrusted.
    Interpolated raw, a `#` or `?` in a segment ends the path (so a DELETE lands
    on a parent resource), and `/` or `%` corrupt it. Every segment is encoded
    with `safe=""` so each one is exactly one path component — a row named
    "a/b" or "Fix?" reaches the right resource instead of retargeting the call.

    Dot segments are rejected outright: `quote` leaves `.`/`..` unchanged, and
    those are the segments httpx resolves away to a different endpoint.
    """
    parts: list[str] = []
    for segment in segments:
        text = str(segment)
        if text in (".", ".."):
            msg = f"Unsafe path segment {text!r}"
            raise ValueError(msg)
        parts.append(quote(text, safe=""))
    return "/" + "/".join(parts)


def _get_client(ctx: Context) -> CodaClient:
    """Retrieve the CodaClient from lifespan context."""
    return ctx.lifespan_context["client"]


def _get_config(ctx: Context) -> CodaConfig:
    """Retrieve the CodaConfig from lifespan context."""
    return ctx.lifespan_context["config"]


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


def _dumps(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _ok(data: Any) -> str:
    """Serialize a successful response to JSON, shrinking it to fit if needed.

    Oversized payloads drop whole items until the serialized form fits, rather
    than slicing the JSON string. Slicing produced output that was neither valid
    JSON nor a usable partial -- `json.loads` failed, so the caller lost every
    item instead of just the overflow -- and because the pagination envelope is
    serialized after `items`, `next_cursor` was the first thing cut, removing
    the means of fetching the rest.
    """
    result = _dumps(data)
    if len(result) <= CHARACTER_LIMIT:
        return result

    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        # Not a list envelope (e.g. a single large doc): fall back to slicing.
        return _truncate(result)

    kept = list(items)
    shrunk = {**data, "items": kept}

    def _with_notice() -> dict[str, Any]:
        # The notice is part of what has to fit. Measuring without it and
        # appending afterwards pushed the payload back over the limit in the
        # boundary case, which fell through to slicing -- reintroducing exactly
        # the unparseable output this function exists to prevent.
        dropped = len(items) - len(kept)
        shrunk["truncated"] = {
            "returned": len(kept),
            "dropped": dropped,
            "reason": f"response exceeded {CHARACTER_LIMIT} characters",
            "hint": (
                "re-call the same request with a smaller limit "
                f"(e.g. limit={len(kept)}) or add filters; do NOT follow "
                "next_cursor, it resumes past the dropped items"
            ),
        }
        # The API's next_cursor resumes *after* this page, so emitting it here
        # would skip the items just dropped (rows 41-99 in the review's repro
        # became unreachable). Clear it and keep has_more so the caller retries
        # this page at a smaller size. total_count must count what we return.
        if "next_cursor" in shrunk:
            shrunk["next_cursor"] = None
            shrunk["has_more"] = True
        if "total_count" in shrunk:
            shrunk["total_count"] = len(kept)
        return shrunk

    # Drop ~10% at a time so a 5,000-item response costs a handful of dumps
    # rather than 5,000 of them.
    while kept and len(_dumps(_with_notice())) > CHARACTER_LIMIT:
        del kept[-max(1, len(kept) // 10) :]

    # Even zero items can overflow if the rest of the envelope is huge. Return a
    # valid, empty envelope rather than a sliced string: a caller that can parse
    # the response can still read next_cursor and retry with a narrower query.
    return _dumps(_with_notice())


def _page(data: dict[str, Any]) -> str:
    """Serialize a Coda list response as the standard pagination envelope."""
    items = data.get("items", [])
    next_cursor = data.get("nextPageToken")
    return _ok(
        {
            "items": items,
            "has_more": next_cursor is not None,
            "next_cursor": next_cursor,
            "total_count": len(items),
        }
    )


def _list_footer(
    total_count: int, has_more: bool, next_cursor: str | None, *, noun: str = "items"
) -> str:
    """The trailing `N items returned (more available, cursor: …)` line."""
    footer = f"\n\n{total_count} {noun} returned"
    if has_more:
        footer += f" (more available, cursor: `{next_cursor}`)"
    return footer


def _format_list_as_markdown(
    items: list[dict[str, Any]],
    *,
    has_more: bool = False,
    next_cursor: str | None = None,
    total_count: int = 0,
) -> str:
    """Format a list response as human-readable markdown."""
    lines: list[str] = []
    for item in items:
        name = item.get("name", "Untitled")
        item_id = item.get("id", "")
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
    return "\n".join(lines) + _list_footer(total_count, has_more, next_cursor)


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


def tool_result(fn: Callable[..., Any] | None = None, *, write: bool = False) -> Any:
    """Apply under @mcp.tool. Expected failures become JSON; bugs become tool errors.

    A CodaError (HTTP 401/403/404/429, other API statuses, read-only mode) is
    what the caller can act on, so it comes back as the structured `_err`
    payload. Anything else is a defect: it is logged with its traceback and
    re-raised as ToolError so the MCP result carries isError=True instead of
    a success envelope that merely mentions an error.

    functools.wraps keeps the wrapped signature visible, so FastMCP still
    injects Context and generates the same schema.
    """

    def wrap(f: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(f)
        async def inner(ctx: Context, *args: Any, **kwargs: Any) -> str:
            try:
                if write:
                    _check_write(ctx)
                return await f(ctx, *args, **kwargs)
            except CodaError as e:
                return _err(e)
            except Exception as e:
                _log.exception("%s failed", f.__name__)
                msg = f"{type(e).__name__}: {e}"
                raise ToolError(msg) from e

        return inner

    return wrap(fn) if fn is not None else wrap
