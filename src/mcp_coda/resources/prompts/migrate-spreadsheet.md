Migrate {source_format} data into Coda doc `{doc_id}`.

## Steps

1. **Analyze source format** — understand the {source_format} structure:
   - For CSV: identify headers, delimiter, encoding, row count
   - For Excel: identify sheets, named ranges, formulas
   - For Google Sheets: identify tabs, shared formulas, linked data
2. **Map columns** — for each source column, determine the Coda column type:
   - Text → `text`
   - Numbers/currency → `number` or `currency`
   - Dates → `date` (ensure ISO 8601 conversion)
   - Yes/No/True/False → `checkbox`
   - Known value sets → `select` or `multiSelect`
   - Email addresses → `person` (if Coda users) or `text`
   - URLs → `hyperlink`
3. **Check target tables** — use `coda_list_tables` on doc "{doc_id}" to see existing tables:
   - If a matching table exists, verify column compatibility
   - If no table exists, create one with `coda_create_table` or suggest manual creation
4. **Prepare data** — format rows for `coda_upsert_rows`:
   - Convert dates to ISO 8601 strings
   - Convert booleans to `true`/`false`
   - Map select values to match existing options exactly (case-sensitive)
   - Identify a key column for upsert deduplication
5. **Execute migration** in batches:
   - Max 500 rows per `coda_upsert_rows` call
   - Wait for mutation completion between batches
   - Track failed rows and retry separately
6. **Verify** — compare source row count with target, spot-check a sample of rows for data integrity.