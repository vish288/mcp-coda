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

## MCP Compliance Rules

### Tool Annotations (MANDATORY)
Every tool MUST have `annotations={}` with at minimum `readOnlyHint` and `openWorldHint`.
- Read tools: `annotations={"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True}`
- Non-destructive write tools: `annotations={"openWorldHint": True, "readOnlyHint": False}`
- Destructive write tools: `annotations={"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False}`
- Idempotent writes (PUT/update): add `idempotentHint: True`

### Tool Descriptions
- 1-2 sentences. Front-load what it does AND what it returns.
- Bad: "This tool gets rows."
- Good: "List rows in a Coda table with optional filtering. Returns row data with values, timestamps, and pagination cursor."

### Error Handling
- Every tool MUST wrap in try/except and return `_err(e)` — never raise.
- Error text MUST be actionable: include what went wrong and suggest a fix.
- Never expose stack traces, tokens, or internal paths.

### Parameter Design
- Use `Annotated[type, Field(description="...")]` on every parameter.
- Use `Literal[...]` for known value sets instead of plain `str`.
- Every optional parameter must have a default.
- Flatten — no nested dicts unless truly necessary (like `cells`).

### Read-Only Mode
- Every write tool MUST call `_check_write(ctx)` before any mutation.

### Naming Convention
- Pattern: `coda_{verb}_{resource}` (snake_case)
- Verbs: create, get, list, update, delete, push, trigger, export, publish, unpublish, resolve

### Adding New Tools
- Add to the appropriate server module (or create a new one registered in `servers/__init__.py`)
- Import helpers from `._helpers` — never duplicate `_get_client`, `_ok`, `_err`, etc.
- Always include `annotations={}` on the `@mcp.tool()` decorator
- Tag appropriately for read/write

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

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CODA_API_TOKEN` | Yes | Coda API token |
| `CODA_READ_ONLY` | No | Disable all write operations |
| `CODA_BASE_URL` | No | API base URL (default: `https://coda.io/apis/v1`) |
| `CODA_TIMEOUT` | No | HTTP timeout in seconds (default: 30) |
| `CODA_SSL_VERIFY` | No | Verify SSL certificates (default: true) |
