# Changelog

## 0.2.0 (unreleased)

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
