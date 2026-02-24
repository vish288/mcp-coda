Analyze the structure of Coda doc `{doc_id}`.

## Steps

1. **List pages** — use `coda_list_pages` with doc_id="{doc_id}". Map the parent-child hierarchy.
2. **List tables** — use `coda_list_tables` with doc_id="{doc_id}". Note table types (table vs view), row counts, and which pages contain them.
3. **Check schema** — for each table, use `coda_list_columns` to review column types, calculated columns, and display columns.
4. **Evaluate organization**:
   - Is the page nesting depth reasonable (≤3 levels)?
   - Are related tables grouped on the same page or nearby pages?
   - Are there orphaned or empty pages?
   - Are display columns set to meaningful, unique values?
5. **Check for issues**:
   - Tables with >5,000 rows (performance risk)
   - Tables with >50 columns (complexity risk)
   - Duplicate or near-duplicate tables that should be views
   - Pages with no content or purpose
6. **Summarize** — report the doc's structure with a hierarchy diagram, table inventory, and actionable recommendations.