"""Coda API client using httpx."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from .config import CodaConfig
from .exceptions import (
    CodaApiError,
    CodaAuthError,
    CodaNotFoundError,
    CodaRateLimitError,
)

# Coda rate limit buckets (requests per window)
RATE_LIMITS = {
    "read": {"limit": 100, "window": 6},
    "write": {"limit": 10, "window": 6},
}

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class RateLimitBudget:
    """Tracks rate limit budget usage with sliding window counters."""

    def __init__(self) -> None:
        self._read_calls: list[float] = []
        self._write_calls: list[float] = []

    def record(self, method: str) -> None:
        """Record a request."""
        now = time.monotonic()
        if method.upper() in WRITE_METHODS:
            self._write_calls.append(now)
        else:
            self._read_calls.append(now)

    def _prune(self, calls: list[float], window: int) -> list[float]:
        cutoff = time.monotonic() - window
        return [t for t in calls if t > cutoff]

    def remaining(self) -> dict[str, dict[str, int]]:
        """Return remaining budget for each bucket."""
        self._read_calls = self._prune(self._read_calls, RATE_LIMITS["read"]["window"])
        self._write_calls = self._prune(self._write_calls, RATE_LIMITS["write"]["window"])
        return {
            "read": {
                "remaining": max(0, RATE_LIMITS["read"]["limit"] - len(self._read_calls)),
                "limit": RATE_LIMITS["read"]["limit"],
                "window_seconds": RATE_LIMITS["read"]["window"],
                "used": len(self._read_calls),
            },
            "write": {
                "remaining": max(0, RATE_LIMITS["write"]["limit"] - len(self._write_calls)),
                "limit": RATE_LIMITS["write"]["limit"],
                "window_seconds": RATE_LIMITS["write"]["window"],
                "used": len(self._write_calls),
            },
        }


class CodaClient:
    """Async HTTP client for the Coda v1 API."""

    def __init__(self, config: CodaConfig | None = None) -> None:
        self.config = config or CodaConfig.from_env()
        self.config.validate()
        self.budget = RateLimitBudget()
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={
                "Authorization": f"Bearer {self.config.token}",
                "Content-Type": "application/json",
            },
            timeout=self.config.timeout,
            verify=self.config.ssl_verify,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an HTTP request against the Coda API.

        Returns parsed JSON response or None for 204/empty responses.
        Raises typed exceptions for error status codes.
        """
        kwargs: dict[str, Any] = {}
        if params is not None:
            # Filter out None values from params
            kwargs["params"] = {k: v for k, v in params.items() if v is not None}
        if json_data is not None:
            kwargs["json"] = json_data

        resp = await self._client.request(method, path, **kwargs)
        self.budget.record(method)

        # Rate limit
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            raise CodaRateLimitError(retry_after=retry_after, body=resp.text)

        # Auth errors
        if resp.status_code in (401, 403):
            raise CodaAuthError(resp.status_code, resp.text)

        # Not found
        if resp.status_code == 404:
            raise CodaNotFoundError(resp.text)

        # Other errors
        if not resp.is_success:
            raise CodaApiError(resp.status_code, resp.reason_phrase or "", resp.text)

        # Empty response (204 or no content)
        if resp.status_code == 204 or not resp.content:
            return None

        # Accepted (async mutation) — return full response including requestId
        if resp.status_code == 202:
            return resp.json()

        # HTML guard
        content_type = resp.headers.get("content-type", "")
        if "text/html" in content_type:
            msg = "Unexpected HTML response — check URL and authentication"
            raise CodaApiError(resp.status_code, msg, resp.text[:500])

        try:
            return resp.json()
        except json.JSONDecodeError as e:
            raise CodaApiError(resp.status_code, f"JSON parse error: {e}", resp.text[:500]) from e

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """HTTP GET request."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json_data: Any = None, **kwargs: Any) -> Any:
        """HTTP POST request."""
        return await self._request("POST", path, json_data=json_data, **kwargs)

    async def put(self, path: str, json_data: Any = None, **kwargs: Any) -> Any:
        """HTTP PUT request."""
        return await self._request("PUT", path, json_data=json_data, **kwargs)

    async def patch(self, path: str, json_data: Any = None, **kwargs: Any) -> Any:
        """HTTP PATCH request."""
        return await self._request("PATCH", path, json_data=json_data, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Any:
        """HTTP DELETE request."""
        return await self._request("DELETE", path, **kwargs)
