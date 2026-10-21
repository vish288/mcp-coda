"""MCP server for Coda API."""

from __future__ import annotations

import asyncio
import hmac
import logging
import os
from typing import Any, Literal

import click
from dotenv import load_dotenv
from fastmcp.server.auth import TokenVerifier
from mcp.server.auth.provider import AccessToken

# Hosts for which an HTTP transport needs no bearer token: the loopback
# interface is only reachable from the same machine.
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class _BearerTokenVerifier(TokenVerifier):
    """Accept exactly one shared bearer token, compared in constant time.

    StaticTokenVerifier resolves tokens with a dict `.get`, which is not
    constant-time. For a single env-sourced secret, hmac.compare_digest avoids
    leaking how long a matching prefix the presented token has through response
    timing. Compare encoded bytes: compare_digest raises TypeError on a str
    containing non-ASCII, so a non-ASCII bearer would otherwise 500 instead of
    being rejected.
    """

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token.encode()

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(token.encode(), self._token):
            return AccessToken(token=token, client_id="mcp-coda", scopes=[])
        return None


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="MCP transport protocol. (sse is deprecated; use streamable-http)",
)
@click.option("--port", default=8000, help="Port for SSE/HTTP transport.")
@click.option("--host", default="127.0.0.1", help="Host for SSE/HTTP transport.")
@click.option("--coda-token", hidden=True, help="Deprecated: set CODA_API_TOKEN instead.")
@click.option("--read-only", is_flag=True, help="Disable all write operations.")
@click.pass_context
def main(
    ctx: click.Context,
    transport: Literal["stdio", "sse", "streamable-http"],
    port: int,
    host: str,
    coda_token: str | None,
    read_only: bool,
) -> None:
    """Run the Coda MCP server."""
    load_dotenv()

    if coda_token:
        click.echo(
            "Warning: --coda-token is deprecated. It puts the token in the process argument "
            "list, where `ps` and shell history can read it. Set CODA_API_TOKEN instead.",
            err=True,
        )
        os.environ["CODA_API_TOKEN"] = coda_token
    if read_only:
        os.environ["CODA_READ_ONLY"] = "true"

    # Validate configuration before the server starts its handshake (D7): a bad
    # config is one clear line and exit 2, not a traceback from inside the FastMCP
    # lifespan. The lifespan keeps its own validate() for the in-process test path.
    from .config import CodaConfig

    try:
        CodaConfig.from_env().validate()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(2)

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s | %(message)s",
    )

    from .servers import mcp

    bearer_token = os.getenv("CODA_HTTP_BEARER_TOKEN", "").strip()

    if transport == "sse":
        click.echo(
            "Warning: --transport sse uses the HTTP+SSE transport, deprecated in MCP 2026-07-28. "
            "Use --transport streamable-http.",
            err=True,
        )

    transport_kwargs: dict[str, Any] = {}
    if transport != "stdio":
        transport_kwargs["host"] = host
        transport_kwargs["port"] = port
        # DNS-rebinding protection: validate Host/Origin before a request reaches
        # the MCP endpoint. "auto" guards loopback-bound servers, allowing the
        # configured host plus localhost/127.0.0.1/[::1] and rejecting any other
        # Host (421) or cross-site Origin (403). Without this a rebinding page
        # could drive the local server with the user's Coda token.
        transport_kwargs["host_origin_protection"] = "auto"

        # Host/Origin protection is not authentication: an HTTP transport serves
        # every tool, with the owner's Coda token, to anyone who reaches the
        # port. Require a bearer token before binding anywhere but loopback.
        if bearer_token:
            if len(bearer_token) < 16:
                msg = (
                    "CODA_HTTP_BEARER_TOKEN must be at least 16 characters; "
                    "generate one with: openssl rand -hex 32"
                )
                raise click.UsageError(msg)
            mcp.auth = _BearerTokenVerifier(bearer_token)
        elif host not in _LOOPBACK_HOSTS:
            msg = (
                f"--host {host} would expose the Coda API token to the network. "
                "Set CODA_HTTP_BEARER_TOKEN (clients send it as "
                "'Authorization: Bearer <token>') or bind to 127.0.0.1."
            )
            raise click.UsageError(msg)

    asyncio.run(mcp.run_async(transport=transport, show_banner=False, **transport_kwargs))


if __name__ == "__main__":
    main()
