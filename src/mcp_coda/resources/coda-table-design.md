# Coda Table Design

Rules for designing tables, columns, relations, and views in Coda.

## Column Types

| Type | API `format.type` | Notes |
|------|-------------------|-------|
| `text` | `text` | Plain or rich text |
| `number` | `number` | Precision, currency, percent variants |
| `date` | `date` | Date only, datetime, or time |
| `person` | `person` | Coda user reference |
| `lookup` | `lookup` | Pulls values from a related table |
| `select` | `select` / `multiSelect` | Single or multi-choice from a defined list |
| `checkbox` | `checkbox` | Boolean |
| `currency` | `currency` | Number with currency symbol |
| `slider` | `slider` | Numeric range |
| `scale` | `scale` | Star/emoji rating |
| `button` | `button` | Triggers a formula action |
| `image` | `image` | Inline image attachment |
| `hyperlink` | `hyperlink` | URL with display text |

## Display Column

- Every table has exactly one **display column** — the first column by default.
- The display column value appears in lookup references and relation pills.
- Choose a human-readable, unique column (e.g., "Name", "Title") as the display column.
- API: `column.display == true` identifies it.

## Relations and Lookups

1. **Relation column**: Links rows between two tables. Each cell holds one or more row references.
2. **Lookup column**: Derives values from the related table via the relation column.

Pattern:
```
[Tasks] --relation--> [Projects]
[Tasks].Project Name = Lookup(Projects.Name via relation)
```

- Always create the relation first, then add lookups.
- Lookups are read-only computed columns — never write to them via API.
- Relation columns accept row IDs or display-column values for matching.

## Calculated Columns

- Any column can have a formula. Calculated columns (`column.calculated == true`) are read-only.
- Do not attempt to write values to calculated columns via `coda_upsert_rows` — the API will reject it.
- Use `coda_list_columns` to check `calculated` flag before building write payloads.

## Row Limits and Performance

- Coda supports ~10,000 rows per table for interactive use. Beyond that, filtering and formula performance degrade.
- Tables with >100 columns become slow to load and query.
- For large datasets: split into multiple tables with relations, or use views with filters.
- The API returns max 500 rows per request. Use pagination (`pageToken`) for larger result sets.

## Table vs. View

- A **table** is the source-of-truth data store.
- A **view** is a filtered/sorted/grouped lens on a table. Views share the same underlying data.
- API: `tableType` is `"table"` or `"view"`. Both are queryable via `coda_list_rows`.
- Creating a view does not duplicate data — changes in one reflect in all views of that table.
- Views can have hidden columns, custom sort, and row filters.

## Schema Naming

- Table names: singular noun (`Task`, `Project`), PascalCase or Title Case
- Column names: descriptive, no abbreviations (`Due Date` not `dd`)
- Avoid spaces in names used as formula references — Coda auto-escapes but it adds noise
- Select list values: consistent casing, no trailing spaces

## Anti-Patterns

- Writing to calculated or lookup columns — always check `calculated` flag first
- Creating separate tables for what should be select-list values
- Using text columns for structured data (dates, numbers) — use typed columns
- Ignoring the display column — it affects how relations render everywhere
