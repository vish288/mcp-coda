"""Coda API exceptions."""

from __future__ import annotations


class CodaError(Exception):
    """Base exception for Coda operations."""


class CodaApiError(CodaError):
    """HTTP error from the Coda API."""

    def __init__(self, status_code: int, status_text: str, body: str = "") -> None:
        self.status_code = status_code
        self.status_text = status_text
        self.body = body
        super().__init__(f"Coda API Error {status_code} {status_text}: {body}")


class CodaAuthError(CodaApiError):
    """Authentication or authorization failure (401/403)."""

    def __init__(self, status_code: int, body: str = "") -> None:
        status_text = "Unauthorized" if status_code == 401 else "Forbidden"
        super().__init__(status_code, status_text, body)


class CodaNotFoundError(CodaApiError):
    """Resource not found (404)."""

    def __init__(self, body: str = "") -> None:
        super().__init__(404, "Not Found", body)


class CodaRateLimitError(CodaApiError):
    """Rate limit exceeded (429)."""

    def __init__(self, retry_after: int = 1, body: str = "") -> None:
        self.retry_after = retry_after
        super().__init__(429, "Too Many Requests", body)


class CodaConnectionError(CodaError):
    """The Coda API could not be reached (network/transport failure).

    Raised when httpx cannot complete the request at all (DNS, connect,
    read/write timeout, …). It is an expected, actionable failure — the caller
    can retry or fix connectivity — not a bug in the tool, so it carries no
    traceback.
    """

    def __init__(self, url: str, detail: str = "") -> None:
        self.url = url
        self.detail = detail
        msg = f"Cannot reach {url}"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)


class CodaWriteDisabledError(CodaError):
    """Write operations are disabled via MCP_READ_ONLY or CODA_READ_ONLY."""

    def __init__(self) -> None:
        super().__init__(
            "Write operations are disabled (read-only: MCP_READ_ONLY or CODA_READ_ONLY)"
        )
