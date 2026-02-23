# mcp-coda

MCP server for the [Coda API](https://coda.io/developers/apis/v1) — docs, pages, tables, rows, formulas, controls, permissions, folders, publishing, automations, and analytics.

## Features

- 55 tools covering the full Coda v1 API
- Read-only mode via `CODA_READ_ONLY=true`
- MCP tool annotations (readOnlyHint, destructiveHint, idempotentHint)
- Rate limit error surfacing with `retry_after` seconds
- Async mutation tracking via `coda_get_mutation_status`
- stdio, SSE, and streamable-http transports

## Installation

```bash
# Via uvx (recommended)
uvx mcp-coda

# Via pip
pip install mcp-coda
```

## Configuration

Set the `CODA_API_TOKEN` environment variable with your [Coda API token](https://coda.io/account#apiSettings).

```bash
export CODA_API_TOKEN=your-token-here
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CODA_API_TOKEN` | Yes | — | Coda API token |
| `CODA_READ_ONLY` | No | `false` | Disable all write operations |
| `CODA_BASE_URL` | No | `https://coda.io/apis/v1` | API base URL |
| `CODA_TIMEOUT` | No | `30` | HTTP timeout in seconds |
| `CODA_SSL_VERIFY` | No | `true` | Verify SSL certificates |

## Usage

### Claude Code / Cursor

Add to your MCP config (`.mcp.json` or `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "coda": {
      "command": "uvx",
      "args": ["mcp-coda"],
      "env": {
        "CODA_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

### CLI

```bash
# stdio (default)
mcp-coda

# SSE transport
mcp-coda --transport sse --port 8000

# Read-only mode
mcp-coda --read-only
```

## Tools

### Account (3)
- `coda_whoami` — Get current user info
- `coda_resolve_browser_link` — Convert browser URL to API IDs
- `coda_get_mutation_status` — Check async write status

### Docs (5)
- `coda_list_docs` — List accessible docs
- `coda_get_doc` — Get doc metadata
- `coda_create_doc` — Create a new doc
- `coda_update_doc` — Update doc title/icon
- `coda_delete_doc` — Delete a doc

### Pages (8)
- `coda_list_pages` — List pages in a doc
- `coda_get_page` — Get page metadata
- `coda_create_page` — Create a page
- `coda_update_page` — Update page name/content
- `coda_delete_page` — Delete a page
- `coda_get_page_content` — Read page content
- `coda_delete_page_content` — Clear page content
- `coda_export_page` — Export page content

### Tables (4)
- `coda_list_tables` — List tables/views
- `coda_get_table` — Get table metadata
- `coda_list_columns` — List columns
- `coda_get_column` — Get column metadata

### Rows (7)
- `coda_list_rows` — List/filter rows
- `coda_get_row` — Get a single row
- `coda_insert_rows` — Insert/upsert rows
- `coda_update_row` — Update a row
- `coda_delete_row` — Delete a row
- `coda_delete_rows` — Bulk delete rows
- `coda_push_button` — Push a button

### Formulas (2)
- `coda_list_formulas` — List named formulas
- `coda_get_formula` — Get formula value

### Controls (2)
- `coda_list_controls` — List controls
- `coda_get_control` — Get control value

### Permissions (6)
- `coda_get_sharing_metadata` — Get sharing config
- `coda_list_permissions` — List ACL entries
- `coda_add_permission` — Grant access
- `coda_delete_permission` — Revoke access
- `coda_search_principals` — Search users/groups
- `coda_get_acl_settings` — Get ACL settings

### Publishing (3)
- `coda_list_categories` — List publishing categories
- `coda_publish_doc` — Publish a doc
- `coda_unpublish_doc` — Unpublish a doc

### Folders (5)
- `coda_list_folders` — List folders
- `coda_get_folder` — Get folder details
- `coda_create_folder` — Create a folder
- `coda_update_folder` — Rename a folder
- `coda_delete_folder` — Delete a folder

### Automations (1)
- `coda_trigger_automation` — Trigger an automation rule

### Analytics (7)
- `coda_list_doc_analytics` — Doc usage metrics
- `coda_get_doc_analytics_summary` — Aggregated doc metrics
- `coda_list_page_analytics` — Page usage metrics
- `coda_list_pack_analytics` — Pack usage metrics
- `coda_get_pack_analytics_summary` — Aggregated pack metrics
- `coda_list_pack_formula_analytics` — Formula-level metrics
- `coda_get_analytics_updated` — Analytics freshness timestamp

## RBAC Model

Three layers of access control:

1. **Server-level**: `CODA_READ_ONLY=true` blocks all write tools
2. **MCP annotations**: Each tool declares `readOnlyHint`, `destructiveHint`, `idempotentHint` for client-side permission prompts
3. **Coda token scope**: The API token's permissions enforce doc-level access

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
pytest tests/ -v --cov=mcp_coda

# Lint
ruff check src/ tests/
ruff format --check src/ tests/

# Type check
mypy src/
```

## License

MIT
