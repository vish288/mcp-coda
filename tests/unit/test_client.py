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
    CodaNotFoundError,
    CodaRateLimitError,
)

TEST_BASE_URL = "https://coda.io/apis/v1"
TEST_TOKEN = "test-token"


@pytest.fixture
def config() -> CodaConfig:
    return CodaConfig(token=TEST_TOKEN, base_url=TEST_BASE_URL)


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

    async def test_params_filter_none(self, config: CodaConfig) -> None:
        async with respx.mock:
            route = respx.get(f"{TEST_BASE_URL}/docs").mock(
                return_value=httpx.Response(200, json={"items": []})
            )
            client = CodaClient(config)
            await client.get("/docs", params={"query": "test", "folderId": None})
            assert "folderId" not in str(route.calls[0].request.url)

    async def test_rate_limit_429(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/docs").mock(
                return_value=httpx.Response(429, headers={"Retry-After": "5"}, text="slow down")
            )
            client = CodaClient(config)
            with pytest.raises(CodaRateLimitError) as exc_info:
                await client.get("/docs")
            assert exc_info.value.retry_after == 5

    async def test_rate_limit_default_retry(self, config: CodaConfig) -> None:
        async with respx.mock:
            respx.get(f"{TEST_BASE_URL}/docs").mock(
                return_value=httpx.Response(429, text="slow down")
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


class TestCodaClientClose:
    async def test_close(self, config: CodaConfig) -> None:
        client = CodaClient(config)
        await client.close()
        assert client._client.is_closed
