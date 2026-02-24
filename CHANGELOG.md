# Changelog

## [0.4.2] - 2026-02-24


## [0.4.0] - 2026-02-24

### Features
- Merge pull request #4 from vish288/feat/static-resources-and-prompts (9088eb2)
- feat: add 10 static knowledge resources and 5 MCP prompts (63a1379)
- feat: unified install gateway, annotation fix, test suite (#1) (b736eee)

### Bug Fixes
- fix: validate token is ASCII before passing to httpx (#6) (23f5b62)
- fix: disable FastMCP startup banner (#5) (92c988e)
- fix: DRY _load_file helper, string.Template for prompts, caching (629347e)

### Documentation
- docs: add release workflow and architecture details to AGENTS.md (#2) (03f04ab)

### Other


## 0.3.0 (unreleased)

### Added

- MCP Resources: `coda://docs` (static) and `coda://docs/{doc_id}/schema` (template)
- Rate limit budget tracker (`RateLimitBudget`) — sliding window counter for reads/writes
- `coda_rate_limit_budget` tool — check remaining API call budget before batch operations
- Evaluation XML with 10 QA pairs for tool selection validation
- Tests for resources and rate limit budget (165 total tests)

### Changed

- Tool count: 53 → 54 (added `coda_rate_limit_budget`)
- Client now tracks request budget per sliding window (100 reads/6s, 10 writes/6s)

## 0.2.0

### Added

- Pydantic response models in `models/` (base, docs, pages, tables, rows, formulas, permissions, folders)
- Unit tests for all 12 tool modules (permissions, publishing, folders, analytics, automations, formulas, controls, tables)
- Unit tests for Pydantic models
- `response_format` parameter (json/markdown) on `coda_list_docs` and `coda_list_rows`
- CHARACTER_LIMIT (25000) truncation on all responses
- `isError: true` flag in all error responses
- `openWorldHint: True` annotation on all 53 tools
- `_format_list_as_markdown` helper for readable list output

### Changed

- Test count: 87 → 155

## 0.1.0

Initial release.

### Tools (55)

- **Account** (3): whoami, resolve_browser_link, get_mutation_status
- **Docs** (5): list, get, create, update, delete
- **Pages** (8): list, get, create, update, delete, get_content, delete_content, export
- **Tables** (4): list_tables, get_table, list_columns, get_column
- **Rows** (7): list, get, insert (with upsert), update, delete, bulk_delete, push_button
- **Formulas** (2): list, get
- **Controls** (2): list, get
- **Permissions** (6): get_sharing_metadata, list, add, delete, search_principals, get_acl_settings
- **Publishing** (3): list_categories, publish, unpublish
- **Folders** (5): list, get, create, update, delete
- **Automations** (1): trigger
- **Analytics** (7): doc_analytics, doc_summary, page_analytics, pack_analytics, pack_summary, pack_formula_analytics, analytics_updated

### Features

- 3-layer RBAC: server read-only toggle, MCP annotations, Coda token scope
- Rate limit error surfacing with `retry_after` seconds
- Async mutation tracking via `coda_get_mutation_status`
- Curated JSON responses with pagination envelope
- stdio, SSE, and streamable-http transports
