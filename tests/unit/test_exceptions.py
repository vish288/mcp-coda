"""Tests for exception hierarchy."""

from __future__ import annotations

from mcp_coda.exceptions import (
    CodaApiError,
    CodaAuthError,
    CodaError,
    CodaNotFoundError,
    CodaRateLimitError,
    CodaWriteDisabledError,
)


class TestExceptions:
    def test_base_error(self) -> None:
        err = CodaError("something broke")
        assert str(err) == "something broke"
        assert isinstance(err, Exception)

    def test_api_error(self) -> None:
        err = CodaApiError(500, "Internal Server Error", "oops")
        assert err.status_code == 500
        assert err.status_text == "Internal Server Error"
        assert err.body == "oops"
        assert "500" in str(err)
        assert isinstance(err, CodaError)

    def test_auth_error_401(self) -> None:
        err = CodaAuthError(401, "bad token")
        assert err.status_code == 401
        assert err.status_text == "Unauthorized"
        assert isinstance(err, CodaApiError)

    def test_auth_error_403(self) -> None:
        err = CodaAuthError(403, "no access")
        assert err.status_code == 403
        assert err.status_text == "Forbidden"

    def test_not_found_error(self) -> None:
        err = CodaNotFoundError("doc xyz not found")
        assert err.status_code == 404
        assert err.status_text == "Not Found"
        assert isinstance(err, CodaApiError)

    def test_rate_limit_error(self) -> None:
        err = CodaRateLimitError(retry_after=5, body="too fast")
        assert err.status_code == 429
        assert err.retry_after == 5
        assert isinstance(err, CodaApiError)

    def test_rate_limit_error_defaults(self) -> None:
        err = CodaRateLimitError()
        assert err.retry_after == 1
        assert err.body == ""

    def test_write_disabled_error(self) -> None:
        err = CodaWriteDisabledError()
        assert "CODA_READ_ONLY" in str(err)
        assert isinstance(err, CodaError)
        assert not isinstance(err, CodaApiError)
