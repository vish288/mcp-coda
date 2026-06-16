# Changelog

## [0.5.0] - 2026-06-16

### Chores
- chore(deps): bump starlette from 0.52.1 to 1.3.1 (3a98793)
- chore(deps): bump python-multipart from 0.0.22 to 0.0.31 (5f5d4e0)
- chore(deps): bump authlib from 1.6.8 to 1.6.12 (70b8606)
- chore(deps): bump python-dotenv from 1.2.1 to 1.2.2 (b581657)
- chore(deps): bump fastmcp from 3.0.2 to 3.2.0 (37dc85c)
- chore(deps): bump pygments from 2.19.2 to 2.20.0 (27185a8)
- chore(deps): bump cryptography from 46.0.5 to 48.0.1 (e38a64b)
- chore(deps): bump pyjwt from 2.12.0 to 2.13.0 (56a8dbb)
- chore(ci): bump softprops/action-gh-release from 2 to 3 (a8e0e0a)
- chore(ci): bump codecov/codecov-action from 5 to 7 (b0bb342)
- chore(deps-dev): bump pytest from 9.0.2 to 9.0.3 (#33) (48e6c79)
- chore(deps): bump idna from 3.11 to 3.15 (#39) (f4ab522)
- chore(deps): bump pyjwt from 2.11.0 to 2.12.0 (#25) (b715a29)


## [0.4.14] - 2026-03-05

### Documentation
- docs: add Documentation Freshness rule to AGENTS.md (#24) (241fd00)


## [0.4.13] - 2026-03-03

### Features
- feat: add startup logging with package version and config summary (#23) (ca382e3)


## [0.4.12] - 2026-02-27

### Bug Fixes
- fix: align API payloads with Coda v1 OpenAPI spec (#21) (2803790)


## [0.4.11] - 2026-02-27

### Bug Fixes
- fix: shorten server.json description to <=100 chars for MCP Registry (#22) (c26d744)


## [0.4.10] - 2026-02-27

### Bug Fixes
- fix: correct broken MCP Registry URLs (#20) (f00f97e)


## [0.4.9] - 2026-02-27

### Chores
- chore: improve SEO and discoverability (#19) (9f23471)


## [0.4.8] - 2026-02-27

### Bug Fixes
- fix: harden resource/prompt loading and add URL support (#16) (d8e5973)


## [0.4.7] - 2026-02-27

### Features
- feat: add MCP Registry auto-publish on release (b8cd637)


## [0.4.6] - 2026-02-25

### Bug Fixes
- fix: update installation gateway URLs to SPA route (#15) (cfda2a2)


## [0.4.5] - 2026-02-25

### Chores
- chore(ci): bump astral-sh/setup-uv from 5 to 7 (#13) (c1faa3d)
- chore(ci): bump codecov/codecov-action from 4 to 5 (#14) (8bd3726)
- chore(ci): bump actions/checkout from 4 to 6 (#12) (779d1fe)
- chore: add Dependabot for Python deps and GitHub Actions (#11) (55328a2)


## [0.4.4] - 2026-02-24

### Features
- feat: add Gemini CLI extension manifest and context (#10) (005e1f4)


## [0.4.3] - 2026-02-24

### Features
- feat: support CODA_TOKEN and CODA_PAT env var aliases (#8) (8a70d1b)

### Documentation
- docs: sync README structure across MCP repos (#9) (8299d6b)


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
