# mcp-coda — Gemini CLI Extension Context

MCP server providing 54 tools, 12 resources, and 5 prompts for the Coda API. Covers the full Coda document lifecycle: docs, pages, tables, rows, formulas, permissions, automations, and publishing.

## Tool Categories

- **Docs** — list, get, create, delete docs; resolve browser links to API IDs
- **Pages** — list, get, create, update, delete, export pages
- **Folders** — list, create folders
- **Tables** — list, get tables; list columns
- **Rows** — list, get, insert, update, delete rows
- **Formulas & Controls** — list/get formulas, list/get controls
- **Automations** — trigger automations
- **Permissions** — list, add, delete permissions; publish/unpublish docs
- **Utilities** — push button, check mutation status

## Common Workflows

- **Table data management**: `coda-list-docs` -> `coda-list-tables` -> `coda-list-columns` -> `coda-list-rows` -> `coda-insert-rows` or `coda-update-row`
- **Page editing**: `coda-resolve-link` -> `coda-get-page` -> `coda-update-page`
- **Doc setup**: `coda-create-doc` -> `coda-create-page` -> `coda-list-tables` -> `coda-insert-rows`
- **Access control**: `coda-list-permissions` -> `coda-add-permission` -> `coda-publish-doc`
- **Automation trigger**: `coda-list-docs` -> `coda-trigger-automation` -> `coda-mutation-status`

## Notes

- Generate API tokens at https://coda.io/account under "API settings".
- Set `CODA_READ_ONLY=true` to restrict all operations to read-only.
- Default request timeout is 30 seconds; override with `CODA_TIMEOUT`.
- Use `coda-resolve-link` to convert browser URLs to API doc/page IDs before other operations.
- Pack formulas (e.g., DrawFlowchart, Mermaid) cannot be inserted or executed via the API.
- Coda API rate limits apply; the server does not retry on 429 responses.
