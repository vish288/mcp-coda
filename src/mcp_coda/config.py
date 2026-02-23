"""Coda MCP server configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CodaConfig:
    """Configuration for the Coda MCP server."""

    token: str = ""
    base_url: str = "https://coda.io/apis/v1"
    read_only: bool = False
    timeout: int = 30
    ssl_verify: bool = True

    @classmethod
    def from_env(cls) -> CodaConfig:
        """Create configuration from environment variables."""
        token = os.getenv("CODA_API_TOKEN", "")
        base_url = os.getenv("CODA_BASE_URL", "https://coda.io/apis/v1").rstrip("/")
        read_only = os.getenv("CODA_READ_ONLY", "false").lower() in ("true", "1", "yes")
        timeout = int(os.getenv("CODA_TIMEOUT", "30"))
        ssl_verify = os.getenv("CODA_SSL_VERIFY", "true").lower() not in ("false", "0", "no")
        return cls(
            token=token,
            base_url=base_url,
            read_only=read_only,
            timeout=timeout,
            ssl_verify=ssl_verify,
        )

    @property
    def is_configured(self) -> bool:
        """Check if the minimum required configuration is present."""
        return bool(self.token)

    def validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.token:
            msg = "CODA_API_TOKEN environment variable is required"
            raise ValueError(msg)
