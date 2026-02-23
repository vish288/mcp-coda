# mcp-coda — Agent Context

## What This Is

MCP server for the Coda v1 API. 55 tools covering docs, pages, tables, rows, formulas, controls, permissions, folders, publishing, automations, and analytics.

## Architecture

- **Framework**: FastMCP >= 2.13.0
- **HTTP client**: httpx AsyncClient
- **Auth**: Bearer token via `CODA_API_TOKEN` env var
- **Build**: hatchling with `src/` layout
- **Structure**: Modular tool files in `src/mcp_coda/servers/` (one per domain)

### RBAC Model

1. **Server-level**: `CODA_READ_ONLY=true` blocks all write tools
2. **MCP annotations**: `readOnlyHint`, `destructiveHint`, `idempotentHint` per tool
3. **Coda token scope**: API token permissions enforce doc-level access

### Key Patterns

- Tools never raise — all errors return `_err(e)` as JSON string
- Every tool returns `str` (JSON via `_ok`/`_err`)
- Write tools call `_check_write(ctx)` first
- List responses include `{items, has_more, next_cursor, total_count}`
- Rate limit errors include `retry_after` seconds
- Async mutations return `requestId` for polling via `coda_get_mutation_status`

## Development

```bash
uv sync                                    # install deps
uv run pytest tests/ -v --cov=mcp_coda    # run tests
uv run ruff check src/ tests/              # lint
uv run ruff format --check src/ tests/     # format check
```

## Tool Inventory (55 tools)

| Module | Tools | Type |
|--------|-------|------|
| account | 3 | read |
| docs | 5 | read/write |
| pages | 8 | read/write |
| tables | 4 | read |
| rows | 7 | read/write |
| formulas | 2 | read |
| controls | 2 | read |
| permissions | 6 | read/write |
| publishing | 3 | read/write |
| folders | 5 | read/write |
| automations | 1 | write |
| analytics | 7 | read |
