"""Tests for CodaConfig."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from mcp_coda.config import CodaConfig


class TestCodaConfig:
    def test_defaults(self) -> None:
        config = CodaConfig()
        assert config.token == ""
        assert config.base_url == "https://coda.io/apis/v1"
        assert config.read_only is False
        assert config.timeout == 30
        assert config.ssl_verify is True

    def test_from_env_with_token(self) -> None:
        env = {"CODA_API_TOKEN": "my-token"}
        with patch.dict(os.environ, env, clear=False):
            config = CodaConfig.from_env()
        assert config.token == "my-token"
        assert config.base_url == "https://coda.io/apis/v1"

    def test_from_env_custom_base_url(self) -> None:
        env = {
            "CODA_API_TOKEN": "tok",
            "CODA_BASE_URL": "https://custom.coda.io/apis/v1/",
        }
        with patch.dict(os.environ, env, clear=False):
            config = CodaConfig.from_env()
        assert config.base_url == "https://custom.coda.io/apis/v1"  # trailing slash stripped

    def test_from_env_read_only(self) -> None:
        for truthy in ("true", "1", "yes", "True", "YES"):
            env = {"CODA_API_TOKEN": "tok", "CODA_READ_ONLY": truthy}
            with patch.dict(os.environ, env, clear=False):
                config = CodaConfig.from_env()
            assert config.read_only is True, f"Expected True for CODA_READ_ONLY={truthy}"

    def test_from_env_not_read_only(self) -> None:
        for falsy in ("false", "0", "no", ""):
            env = {"CODA_API_TOKEN": "tok", "CODA_READ_ONLY": falsy}
            with patch.dict(os.environ, env, clear=False):
                config = CodaConfig.from_env()
            assert config.read_only is False, f"Expected False for CODA_READ_ONLY={falsy}"

    def test_from_env_ssl_verify_disabled(self) -> None:
        env = {"CODA_API_TOKEN": "tok", "CODA_SSL_VERIFY": "false"}
        with patch.dict(os.environ, env, clear=False):
            config = CodaConfig.from_env()
        assert config.ssl_verify is False

    def test_from_env_timeout(self) -> None:
        env = {"CODA_API_TOKEN": "tok", "CODA_TIMEOUT": "60"}
        with patch.dict(os.environ, env, clear=False):
            config = CodaConfig.from_env()
        assert config.timeout == 60

    def test_is_configured_with_token(self) -> None:
        assert CodaConfig(token="abc").is_configured is True

    def test_is_configured_without_token(self) -> None:
        assert CodaConfig().is_configured is False

    def test_validate_success(self) -> None:
        CodaConfig(token="abc").validate()  # should not raise

    def test_validate_missing_token(self) -> None:
        with pytest.raises(ValueError, match="CODA_API_TOKEN"):
            CodaConfig().validate()

    def test_validate_non_ascii_token(self) -> None:
        with pytest.raises(ValueError, match="non-ASCII"):
            CodaConfig(token="tok\ufffd").validate()

    def test_validate_ascii_token_ok(self) -> None:
        CodaConfig(token="abc-123-def").validate()  # should not raise
