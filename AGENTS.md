# mcp-coda — Agent Context

MCP server for the Coda v1 API. 54 tools, 12 resources (2 live data + 5 rules + 5 guides), and 5 prompts covering docs, pages, tables, rows, formulas, controls, permissions, folders, publishing, automations, and analytics.

Built on FastMCP. Published to PyPI as `mcp-coda`; normal install is `uvx mcp-coda`.

## Layout

- `src/mcp_coda/__init__.py` — click CLI, loads `.env` via python-dotenv, runs the FastMCP server
- `src/mcp_coda/servers/__init__.py` — the `FastMCP` instance, `lifespan` (builds the shared `CodaClient`), and `_register_tools()` which imports every tool module so decorators execute
- `src/mcp_coda/servers/*.py` — one module per domain (docs, pages, tables, rows, …)
- `src/mcp_coda/servers/_helpers.py` — shared `_get_client`, `_ok`, `_ok_markdown`, `_err`, `_check_write`, `_format_list_as_markdown`
- `src/mcp_coda/servers/resources.py` / `prompts.py` — MCP resources and prompts
- `src/mcp_coda/resources/` — static markdown backing the rules/guides resources
- `src/mcp_coda/client.py` — async httpx client wrapping every Coda API call
- `src/mcp_coda/config.py` — `CodaConfig` dataclass built from env vars
- `src/mcp_coda/exceptions.py` — `CodaApiError`, `CodaNotFoundError`, `CodaRateLimitError`, …
- `tests/unit/` — ~307 tool- and unit-level tests; `tests/conftest.py` holds shared fixtures
- `tests/test_doc_parity.py` — re-derives tool/resource/prompt counts, tool names and version strings from the source and asserts the docs match; `tests/test_links.py` checks external URLs
- `evaluations/eval.xml` — question / expected-answer / expected-tool pairs used to sanity-check tool selection

## Key patterns

- Every tool sits under `@tool_result` (from `_helpers.py`), applied beneath `@mcp.tool`. A `CodaError` (401/403/404/429, other API statuses, read-only mode) is returned as the structured `_err(e)` JSON; any other exception is logged with its traceback and re-raised as `ToolError`, so the MCP result carries `isError: true`
- Every tool returns `str` (JSON via `_ok`/`_page`/`_err`, markdown via `_ok_markdown`)
- Write tools are declared `@tool_result(write=True)`, which runs `_check_write(ctx)` before the body
- List responses go through `_page(data)` and include `{items, has_more, next_cursor, total_count}`; most paginated endpoints default to `limit=50` (`coda_list_docs` 25, `coda_list_columns` 100)
- Rate-limit errors carry `retry_after` seconds; the server does **not** retry 429s itself
- Row writes are async server-side: they return a `requestId`, poll it with `coda_get_mutation_status`

### Access control (three layers)

1. **Server-level**: `CODA_READ_ONLY=true` blocks all write tools before any API call
2. **MCP annotations**: `readOnlyHint` / `destructiveHint` / `idempotentHint` drive client-side permission prompts
3. **Coda token**: doc-level access is enforced by Coda's sharing settings — tokens have no scopes and reach everything their owner can reach

## MCP compliance rules

### Tool annotations (mandatory)

Every tool MUST pass `annotations={}` with at least `readOnlyHint` and `openWorldHint`.

- Read: `{"openWorldHint": True, "readOnlyHint": True, "idempotentHint": True}`
- Non-destructive write: `{"openWorldHint": True, "readOnlyHint": False}`
- Destructive write: `{"openWorldHint": True, "destructiveHint": True, "readOnlyHint": False}`
- Idempotent write (PUT/update): add `"idempotentHint": True`

Also pass `tags={"coda", "<domain>", "read"|"write"}`.

### Tool descriptions

1–2 sentences, front-loading what it does *and* what it returns.

- Bad: "This tool gets rows."
- Good: "List rows in a Coda table with optional filtering. Returns row data with values, timestamps, and pagination cursor."

### Parameters

- `Annotated[type, Field(description="...")]` on every parameter
- `Literal[...]` for known value sets instead of bare `str`
- Every optional parameter has a default
- Flat — no nested dicts unless genuinely required (e.g. `cells`)

### Errors

- Actionable text: what went wrong plus a suggested fix
- Never expose stack traces, tokens, or internal paths

### Naming

`coda_{verb}_{resource}`, snake_case. Verbs in use: create, get, list, update, delete, push, trigger, export, publish, unpublish, resolve.

### Adding a tool

1. Add it to the matching server module, or create a new module under `servers/` — every non-underscore module there is imported automatically
2. Import helpers from `._helpers` — never re-implement `_get_client`, `_ok`, `_err`, `_check_write`
3. Include `annotations={}` and `tags={}` on the `@mcp.tool()` decorator
4. Add unit tests in `tests/unit/test_tools_<module>.py`
5. Update the docs listed under "Documentation freshness" in the same commit

## Development

```bash
uv sync --all-extras                    # install deps incl. dev group
uv run pytest --cov                     # tests (asyncio_mode = auto; respx mocks httpx)
uv run ruff check .
uv run ruff format --check .
```

CI: `tests.yml` runs the suite on Python 3.10–3.13 and uploads coverage from 3.13; `lint.yml` runs the two ruff commands. Ruff config lives in `pyproject.toml` (line-length 100, rule set `E,F,B,W,I,N,UP,S,C4,EM,ISC`; `tests/**` ignores `S101,S105,S106`).

Running locally:

```bash
uvx mcp-coda                                              # stdio (default)
uvx mcp-coda --transport sse --host 127.0.0.1 --port 8000
uvx mcp-coda --transport streamable-http --port 9000
uvx mcp-coda --coda-token <token> --read-only             # CLI overrides for config
```

## Tool inventory (54)

| Module | Tools | Type | Covers |
|--------|-------|------|--------|
| account | 4 | read | `coda_whoami`, `coda_resolve_browser_link`, `coda_get_mutation_status`, `coda_rate_limit_budget` |
| docs | 5 | read/write | list, get, create, update, delete docs |
| pages | 8 | read/write | list, get, create, update, delete, export pages; get/delete page content |
| tables | 4 | read | list/get tables, list/get columns |
| rows | 7 | read/write | list, get, insert (upsert via `key_columns`), update, delete row/rows, push button |
| formulas | 2 | read | list, get formulas |
| controls | 2 | read | list, get controls |
| permissions | 6 | read/write | sharing metadata, list/add/delete permissions, search principals, ACL settings |
| publishing | 3 | read/write | list categories, publish, unpublish |
| folders | 5 | read/write | list, get, create, update, delete folders |
| automations | 1 | write | trigger automation |
| analytics | 7 | read | doc/page/pack analytics + summaries, last-updated day |

## Common workflows

- **Table data**: `coda_list_docs` → `coda_list_tables` → `coda_list_columns` → `coda_list_rows` → `coda_insert_rows` / `coda_update_row`
- **Page editing**: `coda_resolve_browser_link` → `coda_get_page` → `coda_update_page`
- **Doc setup**: `coda_create_doc` → `coda_create_page` → `coda_list_tables` → `coda_insert_rows`
- **Access control**: `coda_list_permissions` → `coda_add_permission` → `coda_publish_doc`
- **Automation**: `coda_list_docs` → `coda_trigger_automation` → `coda_get_mutation_status`

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CODA_API_TOKEN` | Yes | — | Coda API token |
| `CODA_READ_ONLY` | No | `false` | `true`/`1`/`yes` disables every write tool |
| `CODA_BASE_URL` | No | `https://coda.io/apis/v1` | API base URL (trailing slash stripped) |
| `CODA_TIMEOUT` | No | `30` | HTTP timeout, seconds |
| `CODA_SSL_VERIFY` | No | `true` | `false`/`0`/`no` skips certificate verification |

The token is read from `CODA_API_TOKEN`, then `CODA_TOKEN`, then `CODA_PAT` — first non-empty wins. Tokens are generated at <https://coda.io/account#apiSettings> under "API settings". `CodaConfig.validate()` rejects non-ASCII tokens (httpx header encoding).

## Coda API gotchas

- Browser URLs are not API IDs — run `coda_resolve_browser_link` first to get doc/page/table/row IDs
- Pack formulas (DrawFlowchart, Mermaid, etc.) cannot be inserted or executed through the API
- Rate limits are per-token and vary by plan; check `coda_rate_limit_budget` before batch operations
- Analytics endpoints generally require doc ownership, not just Viewer access
- Minimum doc roles: Viewer for reads; Editor for page/row writes, folder management, and triggering automations; Doc Owner for permissions and publishing

## Release workflow

Releases run through GitHub Actions. Never bump versions or create tags by hand.

```bash
gh workflow run release.yml -f bump=minor               # 0.3.0 → 0.4.0
gh workflow run release.yml -f bump=patch               # 0.4.0 → 0.4.1
gh workflow run release.yml -f bump=major               # 0.4.0 → 1.0.0
gh workflow run release.yml -f bump=minor -f dry_run=true   # preview changelog, no push
```

1. `release.yml` (workflow_dispatch) bumps the `pyproject.toml` version, regenerates `uv.lock`, generates `CHANGELOG.md`, and creates the release commit + tag via the GitHub API
2. `publish.yml` (triggered by the `v*` tag push) builds the wheel, publishes to PyPI, and creates the GitHub Release

Rules:

- Never edit the `pyproject.toml` version directly — the workflow owns it
- Never create tags manually
- Commit messages must follow conventional commits (`feat:`, `fix:`, `docs:`, …) so the changelog generates
- The release commit is authored by `github-actions[bot]` with message `chore(release): X.Y.Z`

## Documentation freshness (mandatory)

Any changeset that adds, removes, or modifies tools, resources, or prompts MUST update all of these in the same commit:

- `README.md` — tool count in heading and intro, tool table, full tool reference, usage examples, permissions table
- `llms.txt` — tool count in tagline and documentation link
- `llms-full.txt` — tool count in tagline, documentation link, full tool reference section
- `AGENTS.md` — tool count in intro, tool inventory table
- `server.json` — `description` field (≤100 chars)
- `gemini-extension.json` — `description` field
- `src/mcp_coda/resources/**.md` — the rules/guides shipped to clients; they must only name tools that exist

Check: `uv run pytest tests/test_doc_parity.py` re-derives every count, tool name and version string from the source and fails on drift. To eyeball the total: `grep -c '^async def coda_' src/mcp_coda/servers/*.py`. Also confirm the category list is complete and new tools appear in the right sections with parameters and annotations.

## Known limitations

- Errors come back as successful tool results carrying `{"error": ...}` (soft-error pattern) — callers must inspect the JSON body, not just the transport status
- There are no response models — tools return the raw Coda API JSON straight through `_ok`, so field names keep the API's camelCase and unknown fields survive. The only shaping is `_truncate`'s 25k-character cap and the `{items, has_more, next_cursor, total_count}` list envelope each tool builds inline. Parsing responses into typed models would rename every field and silently drop extras, so it is a breaking change, not a refactor.
