# mcp-coda — Agent Context

MCP server for the Coda v1 API. It provides 54 tools, 12 resources (2 live data + 5 rules + 5 guides), and 5 prompts. They cover docs, pages, tables, rows, formulas, controls, permissions, folders, publishing, automations, and analytics.

mcp-coda runs on FastMCP. PyPI hosts it as the `mcp-coda` package. Install it with `uvx mcp-coda`.

## Protocol support

- Implements the MCP 2026-07-28 specification (MCP 2.0). Stays compatible with 2025-11-25 clients.
- Built on FastMCP 4.x and the MCP Python SDK 2.x.
- Transports: `stdio` (default) and `streamable-http` (recommended for remote). `sse` still works, but the 2026-07-28 spec deprecates it, so the server prints a warning.
- Uses tools, resources, and prompts only. No Roots, Sampling, Logging, elicitation, or resource subscriptions, so the 2026-07-28 deprecations do not affect it.

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

- Every tool sits under `@tool_result` (from `_helpers.py`), below `@mcp.tool`. For an expected `CodaError` (401/403/404/429, other API statuses, read-only mode) it returns a `ToolResult(is_error=True)` whose text is the `_err(e)` JSON and no `structuredContent`. Any other exception is logged with its traceback and re-raised as `ToolError`, so the MCP result is also `isError: true` with `TypeName: message` text
- Errors: expected failures are `isError: true` results whose error body (`{"error", "hint", "status_code"?, "body"?, "retry_after"?}`) is the text content; bugs are `isError: true` with `TypeName: message` text, logged with a traceback. No error result carries `structuredContent` — the TS MCP SDK validates it against the output schema even when `isError` is true, so an error payload there would make strict clients reject the result
- Every tool returns a fastmcp `ToolResult`. Success: `_ok`/`_page` put the Coda JSON object in `structuredContent` beside the pretty text; the two markdown branches use `_text` (text only, no `structuredContent`). Expected failures come from `_error_result(_err(e))`. Tools advertise no `outputSchema` (payloads pass upstream fields through untyped); a typed schema is opt-in per tool via `@mcp.tool(output_schema=…)`
- Write tools are declared `@tool_result(write=True)`, which runs `_check_write(ctx)` before the body
- List responses go through `_page(data)` and include `{items, has_more, next_cursor, total_count}`; most paginated endpoints default to `limit=50` (`coda_list_docs` 25, `coda_list_columns` 100)
- Rate-limit errors carry `retry_after` seconds; the server does **not** retry 429s itself
- Row writes are async server-side: they return a `requestId`, poll it with `coda_get_mutation_status`

### Access control (three layers)

1. **Server-level**: `CODA_READ_ONLY=true` (or the shared `MCP_READ_ONLY=true`) locks the server read-only — write tools and write-workflow prompts are hidden from `tools/list`/`prompts/list`, calling a hidden tool is an `Unknown tool` error, and `_check_write` still refuses on any path that reaches it. The lock is computed once at startup and cannot be lifted at runtime; `--read-only` can only raise it. It is a *deployment* control, not a per-user one: a Coda token has no scopes and there is no per-request auth, so it only holds when the deployer owns the launch (managed MCP config `env`, container/k8s env, deployer-run HTTP)
2. **MCP annotations**: `readOnlyHint` / `destructiveHint` / `idempotentHint` drive client-side permission prompts
3. **Coda token**: Coda's sharing settings enforce doc-level access. Tokens have no scopes and reach everything their owner can reach

HTTP transports add a network layer: Host/Origin protection is not authentication, so binding to a non-loopback host requires `CODA_HTTP_BEARER_TOKEN` (min 16 chars, constant-time compared via a `TokenVerifier` subclass). The CLI refuses to start on a non-loopback host without it.

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
uv run pyright                          # type check (src only, basic mode)
```

CI: `tests.yml` runs the suite on Python 3.10–3.13 and uploads coverage from 3.13; `lint.yml` runs the two ruff commands. Ruff config lives in `pyproject.toml` (line-length 100, rule set `E,F,B,W,I,N,UP,S,C4,EM,ISC`; `tests/**` ignores `S101,S105,S106`).

Running locally:

```bash
uvx mcp-coda                                              # stdio (default)
uvx mcp-coda --transport sse --host 127.0.0.1 --port 8000
uvx mcp-coda --transport streamable-http --port 9000
uvx mcp-coda --read-only                                  # CODA_API_TOKEN from env (--coda-token is deprecated, hidden, warns on stderr)
```

## Tool inventory (54)

| Module | Tools | Type | Covers |
|--------|-------|------|--------|
| account | 3 | read | `coda_whoami`, `coda_resolve_browser_link`, `coda_get_mutation_status` |
| docs | 5 | read/write | list, get, create, update, delete docs |
| pages | 9 | read/write | list, get, create, update, delete, export pages; get/delete page content; export status |
| tables | 4 | read | list/get tables, list/get columns |
| rows | 7 | read/write | list, get, insert (upsert via `key_columns`), update, delete row/rows, push button |
| permissions | 6 | read/write | sharing metadata, list/add/delete permissions, search principals, ACL settings |
| folders | 5 | read/write | list, get, create, update, delete folders |
| misc | 8 | read/write | list/get formulas, list/get controls, list categories, publish/unpublish, trigger automation |
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
| `CODA_READ_ONLY` | No | `false` | Lock the server read-only: write tools and write-workflow prompts are not listed and are refused before any API call. Any value other than `false`/`0`/`no`/`off`/empty locks |
| `MCP_READ_ONLY` | No | `false` | Shared alias for `CODA_READ_ONLY` across the mcp-* servers; either locking wins, any value other than `false`/`0`/`no`/`off`/empty locks, nothing lifts it at runtime, and `--read-only` can only raise the lock |
| `CODA_BASE_URL` | No | `https://coda.io/apis/v1` | API base URL (trailing slash stripped) |
| `CODA_TIMEOUT` | No | `30` | HTTP timeout, seconds |
| `CODA_HTTP_BEARER_TOKEN` | No | — | Bearer token (min 16 chars) required to bind an HTTP transport to a non-loopback host; clients send `Authorization: Bearer` |

The token is read from `CODA_API_TOKEN`, then `CODA_TOKEN`, then `CODA_PAT` — first non-empty wins. Tokens are generated at <https://coda.io/account#apiSettings> under "API settings". `CodaConfig.validate()` rejects non-ASCII tokens (httpx header encoding).

## Coda API gotchas

- Browser URLs are not API IDs — run `coda_resolve_browser_link` first to get doc/page/table/row IDs
- The API cannot insert or execute pack formulas (DrawFlowchart, Mermaid, etc.)
- Rate limits are per-token and vary by plan; a 429 returns `retry_after` seconds and the server does not retry itself
- Analytics endpoints generally require doc ownership, not only Viewer access
- Minimum doc roles: Viewer for reads; Editor for page/row writes, folder management, and triggering automations; Doc Owner for permissions and publishing

## Release workflow

Releases run through GitHub Actions. Never bump versions or create tags by hand.

```bash
gh workflow run release.yml -f bump=minor               # 0.3.0 → 0.4.0
gh workflow run release.yml -f bump=patch               # 0.4.0 → 0.4.1
gh workflow run release.yml -f bump=major               # 0.4.0 → 1.0.0
gh workflow run release.yml -f bump=minor -f dry_run=true   # preview changelog, no push
```

1. `release.yml` (workflow_dispatch) runs `tests.yml` and `lint.yml` on the released commit first (`needs: [test, lint]`), bumps the `pyproject.toml` version, regenerates `uv.lock`, generates `CHANGELOG.md`, and creates the release commit + tag via the GitHub API. The commit is created with `GITHUB_TOKEN` and no author/committer, so GitHub signs it as `github-actions[bot]` (verification `verified: true`); only the `main` and tag ref updates use `RELEASE_PAT` (needed to bypass the branch ruleset); `release.yml` dispatches `publish.yml`, and the PAT's tag push no longer triggers publish (publish.yml is dispatch-only)
2. `publish.yml` runs as split, idempotent jobs (`status → build → pypi → github-release → registry`): each target is checked first and written only when not already done, so PyPI, the GitHub release and the MCP Registry each complete independently and recoverably
3. Recovery of a failed publish is `gh run rerun <id> --failed` or `gh workflow run publish.yml --ref refs/tags/vX.Y.Z`; both are no-ops for targets that are already done
4. `reconcile.yml` does this unattended — about 5 min after a failed publish run, then every 6 h on a schedule — scanning the last three tags and dispatching `publish.yml` as needed, capped at 8 failed attempts per tag before it asks for a human

> The `chore(release)` commits are GitHub-verified, but regular `Vish` commits merged into `main` show unsigned: the ruleset allows only rebase merges, and GitHub rewrites rebased PR commits with a new committer and no signature. PR review plus the required `test`/`lint` checks are the integrity control there.

Rules:

- Never edit the `pyproject.toml` version directly — the workflow owns it
- Never create tags manually
- Commit messages must follow conventional commits (`feat:`, `fix:`, `docs:`, …) so the changelog generates
- `github-actions[bot]` authors the release commit with the message `chore(release): X.Y.Z`

## Documentation freshness (mandatory)

Any changeset that adds, removes, or modifies tools, resources, or prompts MUST update all of these in the same commit:

- `README.md` — tool count in heading and intro, tool table, full tool reference, usage examples, permissions table
- `llms.txt` — tool count in tagline and documentation link
- `llms-full.txt` — tool count in tagline, documentation link, full tool reference section
- `AGENTS.md` — tool count in intro, tool inventory table
- `server.json` — `description` field (≤100 chars)
- `gemini-extension.json` — `description` field
- `src/mcp_coda/resources/**.md` — the rules/guides shipped to clients; they must only name tools that exist

Check: `uv run pytest tests/test_doc_parity.py` re-derives every count, tool name and version string from the source and fails on drift. To count the total: `grep -c '^async def coda_' src/mcp_coda/servers/*.py`. Also confirm the category list is complete and new tools appear in the right sections with parameters and annotations.

## Known limitations

- Passthrough objects stay untyped. Tools return the raw Coda API JSON through `_ok` (wrapped in a `ToolResult` as `structuredContent` plus pretty text), so field names keep the API's camelCase and unknown fields survive; tools advertise no `outputSchema`. `_ok` shrinks oversized list envelopes by dropping items (never slicing the JSON) and caps single non-list payloads at 25k characters via `_text` (text only), and each list tool builds the `{items, has_more, next_cursor, total_count}` envelope inline. A typed `output_schema=` is opt-in per tool; blanket typed response models would rename every field and silently drop extras, so that is a breaking change, not a refactor.
