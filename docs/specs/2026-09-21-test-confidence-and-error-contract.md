# mcp-coda — spec for the test-confidence → error-contract → dedup initiative

## Objective

Make the suite prove tool behaviour through the real MCP server, gate it in CI
(done, 0.5.9), collapse the 54 identical `try/except` tool bodies into one
decorator that returns expected API failures as JSON and raises everything
else as a real MCP `isError` (done, 0.6.0), then remove the drift-prone
inventory lists (this branch). No public tool, resource or prompt changes shape.

## Commands

```
uv run pytest -q                                   # network marker excluded
uv run pytest -q --cov --cov-report=term-missing   # src/ only, gate 99
uv run ruff check . && uv run ruff format --check .
uv build
```

## Structure

```
src/mcp_coda/
  client.py            CodaClient: 5 verbs over _request; strips None params; rejects ./.. segments
  config.py            CodaConfig dataclass, from_env(), validate()
  exceptions.py        CodaError > CodaApiError > {Auth, NotFound, RateLimit}; CodaWriteDisabledError
  servers/__init__.py  FastMCP `mcp`, lifespan, pkgutil discovery of sibling modules
  servers/_helpers.py  tool_result, _ok, _page, _err, _check_write, _get_client, _load_file
  servers/<domain>.py  54 @mcp.tool across 12 modules, each under @tool_result
  servers/resources.py 11 resources + 1 template
  servers/prompts.py   5 prompts
tests/
  conftest.py          _make_ctx, config, tool_client, readonly_client
  unit/test_tools_*.py .fn-level unit layer (mock client, MagicMock ctx)
  unit/test_tool_contract.py   one row per tool: request shape, forced failure, read-only, error split
  unit/test_server_assembly.py real lifespan; counts == decorators scanned from src/; every resource read
  test_doc_parity.py   docs vs source grep
```

## Code style

```python
@mcp.tool(tags={"coda", "docs", "read"}, annotations={...})
@tool_result
async def coda_get_doc(ctx: Context, doc_id: Annotated[str, Field(description=...)]) -> str:
    """One-line summary. Then when to use it and what it does NOT return."""
    return _ok(await _get_client(ctx).get(f"/docs/{doc_id}"))
```

Ruff: E F B W I N UP S C4 EM ISC, line length 100, py310. No `# noqa`, no
`# type: ignore`.

## Testing strategy

1. `.fn` unit tests: unwrap `FunctionTool.fn`, MagicMock ctx, AsyncMock client.
2. Contract tests: `fastmcp.Client(mcp)` with the lifespan swapped for a real
   `CodaClient` pointed at respx. Wire request + `_err` envelope per tool.
3. Assembly: real lifespan via env; live counts vs decorator scan; every
   resource read (this is what proves packaged markdown files exist).

Contract tests win over `.fn` tests when they disagree about a request.

## Boundaries

- `dedup` branch: `servers/__init__.py`, `resources.py`, `prompts.py` tails,
  the two test-side list copies, `AGENTS.md` wording. No tool changes.
- Never edit `.github/workflows/release.yml` or `publish.yml`.
- No live-API tests. No new runtime dependencies.

## Success criteria

- dedup: `_modules`, `_RESOURCE_FILES`, `_PROMPT_FILES` gone; `list_tools()`
  54, `list_resources()` 11 + 1 template, `list_prompts()` 5, unchanged.
- Every `[fix]` ticket at `fixed` with a `gh:` number; `[ticket-only]` filed.

State (2026-09-26, v0.6.0): 54 tools, 587 tests, src/ coverage 99.30%.

## Outcome

- Released versions: 0.5.9 (harness), 0.6.0 (contract), 0.6.1 (dedup)
- Closed issues: #54, #56, #58, #59
