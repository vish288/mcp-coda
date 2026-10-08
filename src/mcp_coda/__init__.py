"""MCP server for Coda API."""

from __future__ import annotations

import asyncio
import logging
import os

import click
from dotenv import load_dotenv


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="MCP transport protocol. (sse is deprecated; use streamable-http)",
)
@click.option("--port", default=8000, help="Port for SSE/HTTP transport.")
@click.option("--host", default="127.0.0.1", help="Host for SSE/HTTP transport.")
@click.option("--coda-token", envvar="CODA_API_TOKEN", help="Coda API token.")
@click.option("--read-only", is_flag=True, help="Disable all write operations.")
def main(
    transport: str,
    port: int,
    host: str,
    coda_token: str | None,
    read_only: bool,
) -> None:
    """Run the Coda MCP server."""
    load_dotenv()

    if coda_token:
        os.environ["CODA_API_TOKEN"] = coda_token
    if read_only:
        os.environ["CODA_READ_ONLY"] = "true"

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s | %(message)s",
    )

    from .servers import mcp

    if transport == "sse":
        click.echo(
            "Warning: --transport sse uses the HTTP+SSE transport, deprecated in MCP 2026-07-28. "
            "Use --transport streamable-http.",
            err=True,
        )

    run_kwargs: dict[str, object] = {"transport": transport}
    if transport != "stdio":
        run_kwargs["host"] = host
        run_kwargs["port"] = port
        # DNS-rebinding protection: validate Host/Origin before a request reaches
        # the MCP endpoint. "auto" guards loopback-bound servers, allowing the
        # configured host plus localhost/127.0.0.1/[::1] and rejecting any other
        # Host (421) or cross-site Origin (403). Without this a rebinding page
        # could drive the local server with the user's Coda token.
        run_kwargs["host_origin_protection"] = "auto"

    asyncio.run(mcp.run_async(show_banner=False, **run_kwargs))


if __name__ == "__main__":
    main()
