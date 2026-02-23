"""Shared test fixtures."""

from __future__ import annotations

import pytest
import respx

from mcp_coda.client import CodaClient
from mcp_coda.config import CodaConfig

TEST_BASE_URL = "https://coda.io/apis/v1"
TEST_TOKEN = "test-coda-token"


@pytest.fixture
def config() -> CodaConfig:
    return CodaConfig(token=TEST_TOKEN, base_url=TEST_BASE_URL)


@pytest.fixture
def read_only_config() -> CodaConfig:
    return CodaConfig(token=TEST_TOKEN, base_url=TEST_BASE_URL, read_only=True)


@pytest.fixture
def client(config: CodaConfig) -> CodaClient:
    return CodaClient(config)


@pytest.fixture
def mock_api() -> respx.MockRouter:
    with respx.mock(base_url=TEST_BASE_URL) as router:
        yield router
