"""Coda MCP server configuration."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

# Read-only resolves across sources that fail CLOSED: a value is stripped and
# lower-cased; anything in _FALSEY is "off", everything else non-empty is "on".
# An unrecognised value therefore locks the server (and warns), never unlocks it.
_FALSEY = frozenset({"", "0", "false", "no", "off"})
_TRUTHY = frozenset({"1", "true", "yes", "on"})

# Shared across the mcp-* servers so one deployer-set env var locks any of them
# read-only. The per-server alias (CODA_READ_ONLY) stays; either being on wins.
_SHARED_READ_ONLY = "MCP_READ_ONLY"

_log = logging.getLogger(__name__)


def _classify(name: str) -> tuple[str, str | None]:
    """Classify one env source as unset / falsey / truthy / other, with its raw value."""
    raw = os.getenv(name)
    if raw is None:
        return "unset", None
    value = raw.strip().lower()
    if value in _FALSEY:
        return "falsey", raw
    if value in _TRUTHY:
        return "truthy", raw
    return "other", raw


def read_only_sources(alias: str) -> list[str]:
    """Env var names (shared first, then the alias) whose value locks read-only."""
    return [
        name for name in (_SHARED_READ_ONLY, alias) if _classify(name)[0] in ("truthy", "other")
    ]


def _read_only(alias: str) -> bool:
    """Resolve read-only as ``on(MCP_READ_ONLY) or on(<alias>)`` — any source wins.

    Fails closed: an unrecognised value locks the server and logs a WARNING naming the
    source and value. A falsy value is never an override — it is the default; when
    another source has locked, one WARNING per ignored falsy source records that it
    had no effect.
    """
    classes = {name: _classify(name) for name in (_SHARED_READ_ONLY, alias)}
    locked = any(kind in ("truthy", "other") for kind, _ in classes.values())
    if locked:
        for name, (kind, raw) in classes.items():
            if kind == "other":
                _log.warning(
                    "read-only: locking on unrecognised %s=%s (anything but a falsy value locks)",
                    name,
                    raw,
                )
            elif kind == "falsey":
                _log.warning(
                    "read-only is locked on; ignoring %s=%s (a falsy value cannot unlock it)",
                    name,
                    raw,
                )
    return locked


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
        read_only = _read_only("CODA_READ_ONLY")
        raw_timeout = os.getenv("CODA_TIMEOUT", "30")
        try:
            timeout = int(raw_timeout)
        except ValueError:
            msg = f"CODA_TIMEOUT must be an integer number of seconds, got {raw_timeout!r}"
            raise ValueError(msg) from None
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
