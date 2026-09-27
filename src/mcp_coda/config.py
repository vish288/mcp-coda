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

    @classmethod
    def from_env(cls) -> CodaConfig:
        """Create configuration from environment variables."""
        token = os.getenv("CODA_API_TOKEN") or os.getenv("CODA_TOKEN") or os.getenv("CODA_PAT", "")
        base_url = os.getenv("CODA_BASE_URL", "https://coda.io/apis/v1").rstrip("/")
        read_only = os.getenv("CODA_READ_ONLY", "false").lower() in ("true", "1", "yes")
        timeout = int(os.getenv("CODA_TIMEOUT", "30"))
        return cls(
            token=token,
            base_url=base_url,
            read_only=read_only,
            timeout=timeout,
        )

    def validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.token:
            msg = "Coda token is required. Set one of: CODA_API_TOKEN, CODA_TOKEN, or CODA_PAT"
            raise ValueError(msg)
        try:
            self.token.encode("ascii")
        except UnicodeEncodeError:
            msg = (
                "The Coda token contains non-ASCII characters. "
                "The token may have been incorrectly decoded (e.g. base64). "
                "Coda API tokens are plain ASCII strings."
            )
            raise ValueError(msg) from None
