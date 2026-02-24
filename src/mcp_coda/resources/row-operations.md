# Row Operations Guide

How to insert, update, upsert, and delete rows in Coda tables.

## Insert vs. Upsert

| Operation | Tool | Behavior |
|-----------|------|----------|
| Insert | `coda_upsert_rows` (no key columns) | Always creates new rows |
| Upsert | `coda_upsert_rows` (with key columns) | Updates if key matches, inserts if not |
| Update | `coda_update_row` | Updates a single row by row ID |
| Delete | `coda_delete_row` / `coda_delete_rows` | Removes rows by ID |

## Bulk Operations

- `coda_upsert_rows` accepts up to **500 rows** per request.
- For larger datasets, batch into 500-row chunks and wait for each mutation to complete before sending the next.
- Each upsert returns a `requestId` — poll `coda_get_mutation_status` before proceeding.

## Key Columns (Upsert Matching)

- `keyColumns` specifies which columns to match on for upsert deduplication.
- If a row exists where all key column values match, it is updated. Otherwise, a new row is inserted.
- Key columns should contain unique, stable values (IDs, codes). Avoid free-text fields.
- Multiple key columns create a composite key — all values must match for an update.

## Cell Value Formats

| Column Type | Value Format | Example |
|-------------|-------------|---------|
| Text | Plain string | `"Hello"` |
| Number | Numeric | `42`, `3.14` |
| Checkbox | Boolean | `true`, `false` |
| Date | ISO 8601 string | `"2024-03-15"` |
| Select | Option value string | `"In Progress"` |
| Multi-select | Comma-separated | `"Tag1,Tag2"` |
| Person | Email string | `"user@example.com"` |
| Hyperlink | URL string | `"https://example.com"` |
| Relation | Display column value or row ID | `"Project Alpha"` |
| Image | Image URL | `"https://example.com/img.png"` |

- Use `useColumnNames=true` in requests to reference columns by name instead of ID.
- Never write to calculated or lookup columns — the API rejects it.

## Button Pushing

- `coda_push_button` triggers a button column's formula for a specific row.
- Returns a `requestId` for async status polling.
- The button's formula executes server-side with the row's context.
- Rate limit: same as write operations (10/6s).

## Delete Strategies

- **Single row**: `coda_delete_row(doc_id, table_id, row_id)` — immediate, returns `requestId`.
- **Bulk delete**: `coda_delete_rows(doc_id, table_id, row_ids)` — up to 500 rows per call.
- Deletions are **permanent** — there is no undo or soft-delete via API.
- To implement soft-delete: add an "Archived" checkbox column, filter views to exclude archived rows.

## Reading Rows

- `coda_list_rows` returns up to 500 rows per page with pagination.
- `coda_get_row` fetches a single row by ID with full cell values.
- Use `query` parameter for server-side filtering: `query='Status:"Done"'`.
- Use `sortBy` for server-side sorting (column ID or name).
- `valueFormat=simpleWithArrays` returns clean values instead of rich objects.

## Anti-Patterns

- Inserting rows one at a time in a loop — batch with `coda_upsert_rows`
- Using display-column values as upsert keys when they are not unique
- Not waiting for mutation completion before dependent writes
- Attempting to write to calculated/lookup columns — check `calculated` flag first
- Deleting rows without confirmation — there is no undo
