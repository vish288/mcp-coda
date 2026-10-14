# Minimal, non-root image for mcp-coda.
# The default run is locked read-only (MCP_READ_ONLY=true); override with -e MCP_READ_ONLY=false to allow writes.
FROM python:3.13-slim

# uv binary, version-pinned; dependencies come from the committed uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.9.2 /uv /uvx /usr/local/bin/
ENV UV_PYTHON_DOWNLOADS=never

# Non-root user.
RUN useradd --create-home --uid 10001 app

WORKDIR /app
COPY . /app

# Install the project and its locked deps into /app/.venv (no dev deps).
RUN uv sync --frozen --no-dev --no-editable \
    && chown -R app:app /app

USER app
ENV PATH="/app/.venv/bin:$PATH" \
    MCP_READ_ONLY=true

ENTRYPOINT ["mcp-coda"]
