"""Tests for CodaConfig."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from mcp_coda.config import CodaConfig


class TestCodaConfig:
    @pytest.fixture(autouse=True)
    def _no_ambient_read_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Strip both read-only env vars so a ``MCP_READ_ONLY=true`` gate run (the
        suite is required green with it exported) does not lock the config under tests
        that set only ``CODA_READ_ONLY`` or none."""
        monkeypatch.delenv("MCP_READ_ONLY", raising=False)
        monkeypatch.delenv("CODA_READ_ONLY", raising=False)

    def test_defaults(self) -> None:
        config = CodaConfig()
        assert config.token == ""
        assert config.base_url == "https://coda.io/apis/v1"
        assert config.read_only is False
        assert config.timeout == 30

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

    def test_from_env_timeout(self) -> None:
        env = {"CODA_API_TOKEN": "tok", "CODA_TIMEOUT": "60"}
        with patch.dict(os.environ, env, clear=False):
            config = CodaConfig.from_env()
        assert config.timeout == 60

    def test_from_env_timeout_invalid(self) -> None:
        """A non-integer CODA_TIMEOUT fails with a message naming the variable."""
        env = {"CODA_API_TOKEN": "tok", "CODA_TIMEOUT": "abc"}
        with (
            patch.dict(os.environ, env, clear=False),
            pytest.raises(ValueError, match="CODA_TIMEOUT"),
        ):
            CodaConfig.from_env()

    def test_from_env_timeout_non_positive(self) -> None:
        """A zero or negative CODA_TIMEOUT is rejected as not positive."""
        env = {"CODA_API_TOKEN": "tok", "CODA_TIMEOUT": "0"}
        with (
            patch.dict(os.environ, env, clear=False),
            pytest.raises(ValueError, match="positive"),
        ):
            CodaConfig.from_env()

    def test_from_env_with_coda_token(self) -> None:
        env = {"CODA_TOKEN": "tok-alias"}
        with patch.dict(os.environ, env, clear=False):
            config = CodaConfig.from_env()
        assert config.token == "tok-alias"

    def test_from_env_with_coda_pat(self) -> None:
        env = {"CODA_PAT": "tok-pat"}
        with patch.dict(os.environ, env, clear=False):
            config = CodaConfig.from_env()
        assert config.token == "tok-pat"

    def test_token_priority(self) -> None:
        """CODA_API_TOKEN takes precedence over aliases."""
        env = {
            "CODA_API_TOKEN": "winner",
            "CODA_TOKEN": "loser1",
            "CODA_PAT": "loser2",
        }
        with patch.dict(os.environ, env, clear=False):
            config = CodaConfig.from_env()
        assert config.token == "winner"

    def test_validate_success(self) -> None:
        CodaConfig(token="abc").validate()  # should not raise

    def test_validate_missing_token(self) -> None:
        with pytest.raises(ValueError, match="CODA_API_TOKEN"):
            CodaConfig().validate()

    def test_validate_non_ascii_token(self) -> None:
        with pytest.raises(ValueError, match="non-ASCII"):
            CodaConfig(token="tok\ufffd").validate()

    def test_non_ascii_message_does_not_blame_a_specific_env_var(self) -> None:
        """The token may have come from CODA_TOKEN or CODA_PAT \u2014 naming one misleads."""
        with pytest.raises(ValueError) as excinfo:
            CodaConfig(token="tok\ufffd").validate()
        assert "CODA_API_TOKEN" not in str(excinfo.value)

    def test_validate_ascii_token_ok(self) -> None:
        CodaConfig(token="abc-123-def").validate()  # should not raise
