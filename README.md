# mcp-coda

[![PyPI version](https://img.shields.io/pypi/v/mcp-coda)](https://pypi.org/project/mcp-coda/)
[![PyPI downloads](https://img.shields.io/pypi/dm/mcp-coda)](https://pypi.org/project/mcp-coda/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-coda)](https://pypi.org/project/mcp-coda/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/vish288/mcp-coda/actions/workflows/tests.yml/badge.svg)](https://github.com/vish288/mcp-coda/actions/workflows/tests.yml)

**mcp-coda** is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for the [Coda API](https://coda.io/developers/apis/v1) — **54 tools**, **12 resources**, and **5 prompts** covering docs, pages, tables, rows, formulas, controls, permissions, folders, publishing, automations, and analytics. Works with Claude Desktop, Claude Code, Cursor, Windsurf, VS Code Copilot, and any MCP-compatible client.

Built with [FastMCP](https://github.com/jlowin/fastmcp), [httpx](https://www.python-httpx.org/), and [Pydantic](https://docs.pydantic.dev/).

## 1-Click Installation

[![Install in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://vish288.github.io/mcp-install.html?server=mcp-coda&install=cursor)

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_Server-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vish288.github.io/mcp-install.html?server=mcp-coda&install=vscode) [![Install in VS Code Insiders](https://img.shields.io/badge/VS_Code_Insiders-Install_Server-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vish288.github.io/mcp-install.html?server=mcp-coda&install=vscode-insiders)

> **Tip:** For other AI assistants (Claude Code, Windsurf, IntelliJ), visit the **[Coda MCP Installation Gateway](https://vish288.github.io/mcp-install.html?server=mcp-coda)**.

<details>
<summary><b>Manual Setup Guides (Click to expand)</b></summary>
<br/>

> Prerequisite: Install `uv` first (required for all `uvx` install flows). [Install uv](https://docs.astral.sh/uv/getting-started/installation/).

### Claude Code

```bash
claude mcp add coda -- uvx mcp-coda
```

### Windsurf & IntelliJ

**Windsurf:** Add to `~/.codeium/windsurf/mcp_config.json`
**IntelliJ:** Add to `Settings | Tools | MCP Servers`

> **Note:** The actual server config starts at `coda` inside the `mcpServers` object.

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

### pip / uv

```bash
uv pip install mcp-coda
```

</details>

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CODA_API_TOKEN` | **Yes** | - | Coda API token ([get one here](https://coda.io/account#apiSettings)) |
| `CODA_READ_ONLY` | No | `false` | Set to `true` to disable write operations |
| `CODA_BASE_URL` | No | `https://coda.io/apis/v1` | API base URL |
| `CODA_TIMEOUT` | No | `30` | Request timeout in seconds |
| `CODA_SSL_VERIFY` | No | `true` | Set to `false` to skip SSL verification |

### Token

`CODA_API_TOKEN` is a Coda API token generated at [coda.io/account#apiSettings](https://coda.io/account#apiSettings). Tokens grant access to all docs accessible by the token owner. There are no scope restrictions — access is controlled at the doc level via Coda's sharing settings.

## Compatibility

| Client | Supported | Install Method |
|--------|-----------|----------------|
| Claude Desktop | Yes | `claude_desktop_config.json` |
| Claude Code | Yes | `claude mcp add` |
| Cursor | Yes | One-click deeplink or `.cursor/mcp.json` |
| VS Code Copilot | Yes | One-click deeplink or `.vscode/mcp.json` |
| Windsurf | Yes | `~/.codeium/windsurf/mcp_config.json` |
| Any MCP client | Yes | stdio or HTTP transport |

## Tools (54)

| Category | Count | Tools |
|----------|-------|-------|
| **Account** | 4 | whoami, resolve browser link, mutation status, rate limit budget |
| **Docs** | 5 | list, get, create, update, delete |
| **Pages** | 8 | list, get, create, update, delete, get content, delete content, export |
| **Tables** | 4 | list tables, get table, list columns, get column |
| **Rows** | 7 | list, get, insert/upsert, update, delete, bulk delete, push button |
| **Formulas** | 2 | list, get |
| **Controls** | 2 | list, get |
| **Permissions** | 6 | sharing metadata, list, add, delete, search principals, ACL settings |
| **Publishing** | 3 | list categories, publish, unpublish |
| **Folders** | 5 | list, get, create, update, delete |
| **Automations** | 1 | trigger automation |
| **Analytics** | 7 | doc analytics, doc summary, page analytics, pack analytics, pack summary, formula analytics, analytics updated |

<details>
<summary>Full tool reference (click to expand)</summary>

### Account
| Tool | Description |
|------|-------------|
| `coda_whoami` | Get current user info |
| `coda_resolve_browser_link` | Convert browser URL to API IDs |
| `coda_get_mutation_status` | Check async write status |
| `coda_rate_limit_budget` | Get remaining rate limit budget |

### Docs
| Tool | Description |
|------|-------------|
| `coda_list_docs` | List accessible docs |
| `coda_get_doc` | Get doc metadata |
| `coda_create_doc` | Create a new doc |
| `coda_update_doc` | Update doc title/icon |
| `coda_delete_doc` | Delete a doc |

### Pages
| Tool | Description |
|------|-------------|
| `coda_list_pages` | List pages in a doc |
| `coda_get_page` | Get page metadata |
| `coda_create_page` | Create a page |
| `coda_update_page` | Update page name/content |
| `coda_delete_page` | Delete a page |
| `coda_get_page_content` | Read page content |
| `coda_delete_page_content` | Clear page content |
| `coda_export_page` | Export page as HTML or markdown |

### Tables
| Tool | Description |
|------|-------------|
| `coda_list_tables` | List tables and views |
| `coda_get_table` | Get table metadata |
| `coda_list_columns` | List columns in a table |
| `coda_get_column` | Get column metadata |

### Rows
| Tool | Description |
|------|-------------|
| `coda_list_rows` | List and filter rows |
| `coda_get_row` | Get a single row |
| `coda_insert_rows` | Insert or upsert rows |
| `coda_update_row` | Update a row |
| `coda_delete_row` | Delete a row |
| `coda_delete_rows` | Bulk delete rows by filter |
| `coda_push_button` | Push a button column value |

### Formulas
| Tool | Description |
|------|-------------|
| `coda_list_formulas` | List named formulas |
| `coda_get_formula` | Get formula value |

### Controls
| Tool | Description |
|------|-------------|
| `coda_list_controls` | List controls |
| `coda_get_control` | Get control value |

### Permissions
| Tool | Description |
|------|-------------|
| `coda_get_sharing_metadata` | Get sharing config |
| `coda_list_permissions` | List ACL entries |
| `coda_add_permission` | Grant access |
| `coda_delete_permission` | Revoke access |
| `coda_search_principals` | Search users/groups |
| `coda_get_acl_settings` | Get ACL settings |

### Publishing
| Tool | Description |
|------|-------------|
| `coda_list_categories` | List publishing categories |
| `coda_publish_doc` | Publish a doc |
| `coda_unpublish_doc` | Unpublish a doc |

### Folders
| Tool | Description |
|------|-------------|
| `coda_list_folders` | List folders |
| `coda_get_folder` | Get folder details |
| `coda_create_folder` | Create a folder |
| `coda_update_folder` | Rename a folder |
| `coda_delete_folder` | Delete a folder |

### Automations
| Tool | Description |
|------|-------------|
| `coda_trigger_automation` | Trigger an automation rule |

### Analytics
| Tool | Description |
|------|-------------|
| `coda_list_doc_analytics` | Doc usage metrics |
| `coda_get_doc_analytics_summary` | Aggregated doc metrics |
| `coda_list_page_analytics` | Page usage metrics |
| `coda_list_pack_analytics` | Pack usage metrics |
| `coda_get_pack_analytics_summary` | Aggregated pack metrics |
| `coda_list_pack_formula_analytics` | Formula-level metrics |
| `coda_get_analytics_updated` | Analytics freshness timestamp |

</details>

## Resources (12)

The server exposes [MCP resources](https://modelcontextprotocol.io/docs/concepts/resources) that provide ambient context without consuming tool calls.

### Data Resources (live API)

| URI | Name | Description |
|-----|------|-------------|
| `coda://docs` | Coda Docs | List of docs accessible to the current API token |
| `coda://docs/{doc_id}/schema` | Coda Doc Schema | Table and column definitions for a doc |

### Rules (static knowledge)

| URI | Name | Description |
|-----|------|-------------|
| `resource://rules/coda-doc-structure` | Coda Doc Structure | Doc/page hierarchy, page types, naming, when to split docs vs folders |
| `resource://rules/coda-table-design` | Coda Table Design | Column types, relations, display columns, row limits, table vs view |
| `resource://rules/coda-permissions` | Coda Permission Model | Doc-level vs page-level locking, ACL, domain sharing, principal types |
| `resource://rules/coda-automations` | Coda Automation Patterns | Webhooks, button triggers, rate limits, payload design, idempotency |
| `resource://rules/coda-api-patterns` | Coda API Best Practices | Rate limits, pagination, async mutations, error handling, retry |

### Guides (how-to)

| URI | Name | Description |
|-----|------|-------------|
| `resource://guides/row-operations` | Row Operations Guide | Insert vs upsert, bulk ops, key columns, cell formats, delete strategies |
| `resource://guides/page-content` | Page Content Guide | HTML vs markdown, insert modes, export workflows |
| `resource://guides/formula-controls` | Formulas & Controls Guide | Named formulas, control types, reading values |
| `resource://guides/publishing-analytics` | Publishing & Analytics Guide | Publishing categories, gallery settings, analytics date filtering |
| `resource://guides/folder-organization` | Folder Organization Guide | Folder CRUD, doc-folder relationships, hierarchy, bulk organization |

## Prompts (5)

The server provides [MCP prompts](https://modelcontextprotocol.io/docs/concepts/prompts) — reusable task templates that clients can invoke.

| Prompt | Parameters | Description |
|--------|-----------|-------------|
| `analyze_doc_structure` | `doc_id` | Analyze a doc's page hierarchy, table layout, and organization |
| `design_table_schema` | `description` | Design a table schema from a natural language description |
| `migrate_spreadsheet` | `doc_id`, `source_format` | Guide for migrating CSV/Excel/Sheets data into Coda |
| `setup_automation` | `doc_id`, `trigger_type` | Set up a webhook/button/time automation with error handling |
| `audit_permissions` | `doc_id` | Audit sharing and permissions, suggest tightening |

## Usage Examples

### Docs & Pages

```
"List all my Coda docs"
→ coda_list_docs(is_owner=True)

"Get the content of page 'Sprint Planning' in doc d1"
→ coda_list_pages(doc_id="d1") → find page ID
→ coda_get_page_content(doc_id="d1", page_id_or_name="canvas-abc")

"Create a new doc from a template"
→ coda_create_doc(title="Q1 Planning", source_doc="template-doc-id")
```

### Tables & Rows

```
"List all tables in doc d1"
→ coda_list_tables(doc_id="d1")

"Find rows where Status is 'Done'"
→ coda_list_rows(doc_id="d1", table_id_or_name="Tasks", query="Done")

"Insert a new row into the Tasks table"
→ coda_insert_rows(doc_id="d1", table_id_or_name="Tasks", rows=[{"cells": [{"column": "Name", "value": "New task"}]}])

"Update a row's status"
→ coda_update_row(doc_id="d1", table_id_or_name="Tasks", row_id_or_name="i-abc", row={"cells": [{"column": "Status", "value": "In Progress"}]})
```

### Formulas & Controls

```
"Get the value of the TotalBudget formula"
→ coda_get_formula(doc_id="d1", formula_id_or_name="TotalBudget")

"Check the current value of the DateFilter control"
→ coda_get_control(doc_id="d1", control_id_or_name="DateFilter")
```

### Permissions & Sharing

```
"Share a doc with a teammate"
→ coda_add_permission(doc_id="d1", access="write", principal={"type": "email", "email": "alice@example.com"})

"List who has access to a doc"
→ coda_list_permissions(doc_id="d1")
```

## Security Considerations

- **Token scope**: Coda API tokens grant access to all docs the token owner can access. Use a dedicated service account for production deployments to limit exposure.
- **Read-only mode**: Set `CODA_READ_ONLY=true` to disable all write operations (create, update, delete). Read-only mode is enforced server-side before any API call.
- **MCP tool annotations**: Each tool declares `readOnlyHint`, `destructiveHint`, and `idempotentHint` for client-side permission prompts.
- **SSL verification**: `CODA_SSL_VERIFY=true` by default. Only disable for development against local proxies.
- **No credential storage**: The server does not persist tokens. Credentials are read from environment variables at startup.

## Rate Limits & Permissions

### Rate Limits

Coda enforces per-token rate limits (varies by plan). When rate-limited, tools return a 429 error with `retry_after` seconds. Use `coda_rate_limit_budget` to check remaining budget before batch operations. Paginated endpoints default to 25 results per page; use `limit` to adjust.

### Async Mutations

Write operations (insert, update, delete rows) are processed asynchronously. Tools return a `requestId` that can be checked with `coda_get_mutation_status` to confirm completion.

### Access Control

| Layer | Mechanism |
|-------|-----------|
| Server-level | `CODA_READ_ONLY=true` blocks all write tools |
| MCP annotations | `readOnlyHint`, `destructiveHint`, `idempotentHint` for client-side prompts |
| Coda token | Doc-level access enforced by Coda's sharing settings |

## CLI & Transport Options

```bash
# Default: stdio transport (for MCP clients)
uvx mcp-coda

# HTTP transport (SSE or streamable-http)
uvx mcp-coda --transport sse --host 127.0.0.1 --port 8000
uvx mcp-coda --transport streamable-http --port 9000

# CLI overrides for config
uvx mcp-coda --coda-token your-token --read-only
```

The server loads `.env` files from the working directory automatically via `python-dotenv`.

## Development

```bash
git clone https://github.com/vish288/mcp-coda.git
cd mcp-coda
uv sync --all-extras

uv run pytest --cov
uv run ruff check .
uv run ruff format --check .
```

## License

MIT
