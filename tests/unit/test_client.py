"""Tests for CodaClient."""

from __future__ import annotations

import httpx
import pytest
import respx

from mcp_coda.client import CodaClient
from mcp_coda.config import CodaConfig
from mcp_coda.exceptions import (
    CodaApiError,
    CodaAuthError,
    CodaConnectionError,
    CodaNotFoundError,
    CodaRateLimitError,
    CodaTimeoutError,
)
from tests.conftest import TEST_BASE_URL, TEST_TOKEN


class TestCodaClientInit:
    def test_creates_with_config(self, config: CodaConfig) -> None:
        client = CodaClient(config)
        assert client.config is config

    def test_validates_on_init(self) -> None:
        with pytest.raises(ValueError, match="CODA_API_TOKEN"):
            CodaClient(CodaConfig())

    def test_sets_auth_header(self, config: CodaConfig) -> None:
        client = CodaClient(config)
        assert client._client.headers["authorization"] == f"Bearer {TEST_TOKEN}"

    def test_passes_timeout_to_httpx(self) -> None:
        """config.timeout reaches httpx; without it a hung API would hang forever."""
        client = CodaClient(CodaConfig(token="tok", timeout=7))
        assert client._client.timeout.read == 7.0


class TestCodaClientRequest:
    """Tests using respx to mock httpx transport.

    Each test creates a fresh CodaClient with respx mocking the transport.
    We use the full URL since respx intercepts at the transport level.
    """

    async def test_get_success(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/whoami").mock(
                return_value=httpx.Response(200, json={"name": "Test User"})
            )
            client = CodaClient(config)
            data = await client.get("/whoami")
            assert data == {"name": "Test User"}

    async def test_post_with_json(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.post(f"{TEST_BASE_URL}/docs").mock(
                return_value=httpx.Response(201, json={"id": "doc-1"})
            )
            client = CodaClient(config)
            data = await client.post("/docs", json_data={"title": "New Doc"})
            assert data == {"id": "doc-1"}

    async def test_put_request(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.put(f"{TEST_BASE_URL}/docs/d1/pages/p1").mock(
                return_value=httpx.Response(200, json={"id": "p1"})
            )
            client = CodaClient(config)
            data = await client.put("/docs/d1/pages/p1", json_data={"name": "Updated"})
            assert data == {"id": "p1"}

    async def test_patch_request(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.patch(f"{TEST_BASE_URL}/docs/d1").mock(
                return_value=httpx.Response(200, json={"id": "d1"})
            )
            client = CodaClient(config)
            data = await client.patch("/docs/d1", json_data={"title": "Renamed"})
            assert data == {"id": "d1"}

    async def test_delete_request(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.delete(f"{TEST_BASE_URL}/docs/d1").mock(return_value=httpx.Response(204))
            client = CodaClient(config)
            data = await client.delete("/docs/d1")
            assert data is None

    async def test_202_accepted(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.post(f"{TEST_BASE_URL}/docs/d1/tables/t1/rows").mock(
                return_value=httpx.Response(202, json={"requestId": "req-123"})
            )
            client = CodaClient(config)
            data = await client.post("/docs/d1/tables/t1/rows", json_data={"rows": []})
            assert data == {"requestId": "req-123"}

    async def test_empty_200_body_is_none(self, config: CodaConfig) -> None:
        """A 200 with no body returns None, not a JSON parse error.

        Some Coda writes answer 200 with an empty body; parsing that as JSON
        would raise CodaApiError instead of a clean success.
        """
        async with respx.mock:
            respx.delete(f"{TEST_BASE_URL}/docs/d1").mock(return_value=httpx.Response(200))
            client = CodaClient(config)
            assert await client.delete("/docs/d1") is None

    async def test_params_filter_none(self, config: CodaConfig) -> None:
        async with respx.mock:
            route = respx.get(f"{TEST_BASE_URL}/docs").mock(
                return_value=httpx.Response(200, json={"items": []})
            )
            client = CodaClient(config)
            await client.get("/docs", params={"query": "test", "folderId": None})
            assert "folderId" not in str(route.calls[0].request.url)

    async def test_rate_limit_429(self, config: CodaConfig) -> None:
        # A long Retry-After (> 5s) is not auto-retried: the 429 surfaces its
        # retry_after for the caller to wait on.
        async with respx.mock:
            route = respx.get(f"{TEST_BASE_URL}/docs").mock(
                return_value=httpx.Response(429, headers={"Retry-After": "30"}, text="slow down")
            )
            client = CodaClient(config)
            with pytest.raises(CodaRateLimitError) as exc_info:
                await client.get("/docs")
            assert exc_info.value.retry_after == 30
            assert route.call_count == 1

    async def test_rate_limit_default_retry(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/docs").mock(
                return_value=httpx.Response(429, text="slow down")
            )
            client = CodaClient(config)
            with pytest.raises(CodaRateLimitError) as exc_info:
                await client.get("/docs")
            assert exc_info.value.retry_after == 1

    async def test_rate_limit_http_date_retry_after(self, config: CodaConfig) -> None:
        # Retry-After may be an HTTP-date instead of delta-seconds; we can't act
        # on that, so fall back to 1 rather than blowing up on int().
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/docs").mock(
                return_value=httpx.Response(
                    429,
                    headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"},
                    text="slow down",
                )
            )
            client = CodaClient(config)
            with pytest.raises(CodaRateLimitError) as exc_info:
                await client.get("/docs")
            assert exc_info.value.retry_after == 1

    async def test_auth_error_401(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/whoami").mock(
                return_value=httpx.Response(401, text="invalid token")
            )
            client = CodaClient(config)
            with pytest.raises(CodaAuthError) as exc_info:
                await client.get("/whoami")
            assert exc_info.value.status_code == 401

    async def test_auth_error_403(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/docs/d1").mock(
                return_value=httpx.Response(403, text="no access")
            )
            client = CodaClient(config)
            with pytest.raises(CodaAuthError) as exc_info:
                await client.get("/docs/d1")
            assert exc_info.value.status_code == 403

    async def test_not_found_404(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/docs/nope").mock(
                return_value=httpx.Response(404, text="not found")
            )
            client = CodaClient(config)
            with pytest.raises(CodaNotFoundError):
                await client.get("/docs/nope")

    async def test_server_error_500(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/whoami").mock(
                return_value=httpx.Response(500, text="internal error")
            )
            client = CodaClient(config)
            with pytest.raises(CodaApiError) as exc_info:
                await client.get("/whoami")
            assert exc_info.value.status_code == 500

    async def test_html_response_guard(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/whoami").mock(
                return_value=httpx.Response(
                    200,
                    text="<html>Login</html>",
                    headers={"content-type": "text/html"},
                )
            )
            client = CodaClient(config)
            with pytest.raises(CodaApiError, match="HTML"):
                await client.get("/whoami")

    async def test_json_parse_error(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/whoami").mock(
                return_value=httpx.Response(
                    200,
                    text="not json at all",
                    headers={"content-type": "application/json"},
                )
            )
            client = CodaClient(config)
            with pytest.raises(CodaApiError, match="JSON parse error"):
                await client.get("/whoami")


class TestPathTraversal:
    """IDs come from a model, and httpx resolves dot segments on join.

    Before the guard, "/docs/../../whoami" silently became /apis/whoami --
    a different endpoint returning plausible data for the wrong resource.
    """

    @pytest.mark.parametrize(
        "path",
        [
            "/docs/../../whoami",
            "/docs/../whoami",
            "/docs/abc/tables/../../../whoami",
            "/docs/./abc",
        ],
    )
    async def test_dot_segments_rejected(self, config: CodaConfig, path: str) -> None:
        client = CodaClient(config)
        try:
            with pytest.raises(ValueError, match="Unsafe path segment"):
                await client.get(path)
        finally:
            await client.close()

    async def test_escapes_api_root_without_guard(self, config: CodaConfig) -> None:
        """Pin the underlying httpx behaviour the guard exists to stop."""
        raw = httpx.AsyncClient(base_url=TEST_BASE_URL)
        assert str(raw.build_request("GET", "/docs/../../whoami").url) == (
            "https://coda.io/apis/whoami"
        )
        await raw.aclose()

    async def test_names_with_spaces_still_allowed(self, config: CodaConfig) -> None:
        """Table/column/row segments accept a *name*; the guard must not block it."""
        async with respx.mock:
            respx.get(url__regex=r".*/tables/.*").mock(
                return_value=httpx.Response(200, json={"id": "grid-1"})
            )
            client = CodaClient(config)
            assert await client.get("/docs/abc/tables/My Table") == {"id": "grid-1"}
            await client.close()


class TestCodaClientClose:
    async def test_close(self, config: CodaConfig) -> None:
        client = CodaClient(config)
        await client.close()
        assert client._client.is_closed


class TestCodaClientTransport:
    """R2: GET-only retries, Retry-After, and the timeout-vs-unreachable split."""

    @pytest.fixture
    def _no_jitter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import mcp_coda.client as client_mod

        monkeypatch.setattr(client_mod._jitter, "uniform", lambda _a, _b: 0.0)

    async def test_get_retries_on_503_then_succeeds(
        self, config: CodaConfig, _no_jitter: None
    ) -> None:
        async with respx.mock:
            route = respx.get(f"{TEST_BASE_URL}/docs").mock(
                side_effect=[
                    httpx.Response(503, headers={"Retry-After": "1"}, text="unavailable"),
                    httpx.Response(200, json={"items": []}),
                ]
            )
            client = CodaClient(config)
            result = await client.get("/docs")
            assert result == {"items": []}
            assert route.call_count == 2

    async def test_get_retries_on_429_with_short_retry_after(self, config: CodaConfig) -> None:
        async with respx.mock:
            route = respx.get(f"{TEST_BASE_URL}/docs").mock(
                side_effect=[
                    httpx.Response(429, headers={"Retry-After": "0"}, text="slow down"),
                    httpx.Response(200, json={"items": []}),
                ]
            )
            client = CodaClient(config)
            result = await client.get("/docs")
            assert result == {"items": []}
            assert route.call_count == 2

    async def test_post_is_never_retried(self, config: CodaConfig) -> None:
        async with respx.mock:
            route = respx.post(f"{TEST_BASE_URL}/docs").mock(
                side_effect=[
                    httpx.Response(503, text="unavailable"),
                    httpx.Response(200, json={}),
                ]
            )
            client = CodaClient(config)
            with pytest.raises(CodaApiError) as exc_info:
                await client.post("/docs", json_data={})
            assert exc_info.value.status_code == 503
            assert route.call_count == 1

    async def test_timeout_is_distinct_from_unreachable(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/docs").mock(side_effect=httpx.ReadTimeout("slow"))
            client = CodaClient(config)
            with pytest.raises(CodaTimeoutError):
                await client.get("/docs")

    async def test_connect_error_is_unreachable(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/docs").mock(side_effect=httpx.ConnectError("refused"))
            client = CodaClient(config)
            with pytest.raises(CodaConnectionError):
                await client.get("/docs")

    def test_connect_timeout_capped(self) -> None:
        client = CodaClient(CodaConfig(token="tok", timeout=50))
        assert client._client.timeout.connect == 10  # min(10, 50)
        assert client._client.timeout.read == 50

    async def test_connect_timeout_is_unreachable(self, config: CodaConfig) -> None:
        # ConnectTimeout is a TimeoutException subclass but means the host was
        # never reached, so it maps to the connection (unreachable) error.
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/docs").mock(side_effect=httpx.ConnectTimeout("no route"))
            client = CodaClient(config)
            with pytest.raises(CodaConnectionError):
                await client.get("/docs")

    async def test_get_gives_up_after_two_attempts(
        self, config: CodaConfig, _no_jitter: None
    ) -> None:
        async with respx.mock:
            route = respx.get(f"{TEST_BASE_URL}/docs").mock(
                return_value=httpx.Response(503, text="unavailable")
            )
            client = CodaClient(config)
            with pytest.raises(CodaApiError) as exc_info:
                await client.get("/docs")
            assert exc_info.value.status_code == 503
            assert route.call_count == 2

    async def test_cancellation_propagates_without_retry(
        self, config: CodaConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The retry loop must not swallow cancellation; it propagates on the
        # first attempt. (respx cannot carry a BaseException side_effect.)
        import asyncio

        client = CodaClient(config)
        calls = 0

        async def _boom(*_a, **_k):
            nonlocal calls
            calls += 1
            raise asyncio.CancelledError

        monkeypatch.setattr(client._client, "request", _boom)
        with pytest.raises(asyncio.CancelledError):
            await client.get("/docs")
        assert calls == 1

    def test_url_userinfo_stripped_from_error(self) -> None:
        # A credential embedded in the base URL must not leak into error text.
        import asyncio

        cfg = CodaConfig(token="tok", base_url="https://user:secret@coda.example.com/apis/v1")

        async def _run() -> None:
            async with respx.mock(assert_all_called=False) as router:
                router.get(url__regex=r".*/docs").mock(side_effect=httpx.ConnectError("refused"))
                client = CodaClient(cfg)
                with pytest.raises(CodaConnectionError) as exc_info:
                    await client.get("/docs")
                assert "secret" not in str(exc_info.value)

        asyncio.run(_run())


class TestRetryAfterParsing:
    """_retry_after_seconds handles both forms, clamps, and rejects non-finite."""

    @staticmethod
    def _resp(retry_after: str | None) -> httpx.Response:
        headers = {"Retry-After": retry_after} if retry_after is not None else {}
        return httpx.Response(429, headers=headers)

    def test_delta_seconds(self) -> None:
        import mcp_coda.client as client_mod

        assert client_mod._retry_after_seconds(self._resp("5")) == 5.0

    def test_http_date(self) -> None:
        from datetime import datetime, timedelta, timezone
        from email.utils import format_datetime

        import mcp_coda.client as client_mod

        when = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=100))
        secs = client_mod._retry_after_seconds(self._resp(when))
        assert secs is not None
        assert 80 <= secs <= 100

    def test_past_date_and_negative_clamped(self) -> None:
        import mcp_coda.client as client_mod

        assert client_mod._retry_after_seconds(self._resp("Wed, 21 Oct 2015 07:28:00 GMT")) == 0.0
        assert client_mod._retry_after_seconds(self._resp("-5")) == 0.0

    def test_non_finite_rejected(self) -> None:
        import mcp_coda.client as client_mod

        assert client_mod._retry_after_seconds(self._resp("nan")) is None
        assert client_mod._retry_after_seconds(self._resp("inf")) is None

    def test_absent(self) -> None:
        import mcp_coda.client as client_mod

        assert client_mod._retry_after_seconds(self._resp(None)) is None
