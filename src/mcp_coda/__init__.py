"""MCP server for Coda API."""

from __future__ import annotations

import asyncio
import os

import click
from dotenv import load_dotenv


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="MCP transport protocol.",
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

    from .servers import mcp

    run_kwargs: dict[str, object] = {"transport": transport}
    if transport != "stdio":
        run_kwargs["host"] = host
        run_kwargs["port"] = port

    asyncio.run(mcp.run_async(**run_kwargs))


if __name__ == "__main__":
    main()
