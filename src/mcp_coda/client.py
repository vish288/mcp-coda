"""Coda API client using httpx."""

from __future__ import annotations

import asyncio
import json
import math
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .config import CodaConfig
from .exceptions import (
    CodaApiError,
    CodaAuthError,
    CodaConnectionError,
    CodaNotFoundError,
    CodaRateLimitError,
    CodaTimeoutError,
)

# Transport retry policy (R2). Idempotent GETs are retried on a transient
# upstream status; writes are never retried. httpx's AsyncHTTPTransport(retries=)
# already covers connection-level failures, so this layer only adds status
# retries. "Max 2 attempts" = the initial request plus at most one retry.
_RETRY_STATUSES = frozenset({502, 503, 504})
_MAX_ATTEMPTS = 2
_MAX_RETRY_AFTER = 5.0  # only honour a 429 Retry-After at most this long (seconds)
_jitter = random.SystemRandom()  # jitter source; SystemRandom sidesteps the S311 lint


def _retry_after_seconds(resp: httpx.Response) -> float | None:
    """Parse a ``Retry-After`` header to seconds-from-now, or None when absent.

    Both forms are handled: delta-seconds, and an HTTP-date (RFC 7231), which is
    converted to the delay from now. The result is clamped to >= 0 (a past date
    means "retry now") and non-finite values are rejected."""
    raw = resp.headers.get("Retry-After")
    if raw is None:
        return None
    raw = raw.strip()
    try:
        seconds = float(raw)
    except ValueError:
        try:
            when = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
        if when is None:
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        seconds = (when - datetime.now(timezone.utc)).total_seconds()
    if not math.isfinite(seconds):
        return None
    return max(0.0, seconds)


def _retry_delay(resp: httpx.Response) -> float | None:
    """Seconds to wait before retrying this response, or None to not retry.

    502/503/504 get a jittered backoff; a 429 is retried only when it names a
    ``Retry-After`` of at most ``_MAX_RETRY_AFTER`` seconds."""
    if resp.status_code in _RETRY_STATUSES:
        return _jitter.uniform(0.5, 1.5)
    if resp.status_code == 429:
        after = _retry_after_seconds(resp)
        if after is not None and after <= _MAX_RETRY_AFTER:
            return after
    return None


# Segments httpx resolves away when joining onto base_url. An id containing one
# silently retargets the request at a *different* endpoint: "/docs/../../whoami"
# leaves /apis/v1 altogether and answers as /apis/whoami, returning plausible
# data for the wrong resource. IDs reach us from a model, so they are untrusted.
#
# Note the narrow rule. Several segments are `*_id_or_name`, and a Coda object
# name may legitimately contain spaces and punctuation, so validating every
# segment against an identifier pattern would break lookup by name. Only the dot
# segments -- the ones that actually change which endpoint is hit -- are rejected.
_UNSAFE_SEGMENTS = {".", ".."}


def _check_path(path: str) -> None:
    """Reject paths that would resolve outside the configured API root."""
    for segment in path.split("/"):
        if segment in _UNSAFE_SEGMENTS:
            msg = f"Unsafe path segment {segment!r} in {path!r}"
            raise ValueError(msg)


class CodaClient:
    """Async HTTP client for the Coda v1 API."""

    def __init__(self, config: CodaConfig | None = None) -> None:
        self.config = config or CodaConfig.from_env()
        self.config.validate()
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={
                "Authorization": f"Bearer {self.config.token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self.config.timeout, connect=min(10, self.config.timeout)),
            transport=httpx.AsyncHTTPTransport(retries=2),
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """One send path with the R2 retry policy. Idempotent GETs are retried on
        a transient upstream status (502/503/504, or a 429 naming a short
        ``Retry-After``) with jitter; writes are never retried. Connection-level
        failures are retried beneath this by ``AsyncHTTPTransport(retries=2)``.

        A timeout and an unreachable host become distinct expected errors (the
        split is ported from mcp-argocd) rather than a single "cannot reach"."""
        # Strip any userinfo so a credential embedded in the URL never lands in
        # an error (as mcp-argocd/mcp-gitlab do).
        safe = httpx.URL(f"{self.config.base_url}{path}").copy_with(username=None, password=None)
        url = str(safe)
        resp: httpx.Response
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                resp = await self._client.request(method, path, **kwargs)
            except httpx.ConnectTimeout as e:
                # A connect timeout means the host was never reached — treat it as
                # unreachable, not slow (it is a TimeoutException subclass, so it
                # must be caught before the timeout branch).
                raise CodaConnectionError(url, str(e)) from e
            except httpx.TimeoutException as e:
                raise CodaTimeoutError(url, str(e)) from e
            except httpx.TransportError as e:
                raise CodaConnectionError(url, str(e)) from e
            except httpx.RequestError as e:
                # Any other request-level failure (e.g. DecodingError,
                # TooManyRedirects): still "could not complete the request".
                raise CodaConnectionError(url, str(e)) from e
            if method == "GET" and attempt < _MAX_ATTEMPTS:
                delay = _retry_delay(resp)
                if delay is not None:
                    await asyncio.sleep(delay)
                    continue
            return resp
        return resp  # pragma: no cover — the loop always returns

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
        _check_path(path)

        kwargs: dict[str, Any] = {}
        if params is not None:
            # Filter out None values from params
            kwargs["params"] = {k: v for k, v in params.items() if v is not None}
        if json_data is not None:
            kwargs["json"] = json_data

        resp = await self._send(method, path, **kwargs)

        # Rate limit. A short Retry-After (<= 5s) was already retried once in
        # _send; whatever reaches here is surfaced with its Retry-After (both the
        # delta-seconds and HTTP-date forms are parsed), falling back to 1s.
        if resp.status_code == 429:
            retry_after = _retry_after_seconds(resp) or 1
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

        # HTML guard (202 async-mutation bodies fall through to the JSON parse
        # below, which returns the full response including requestId)
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
