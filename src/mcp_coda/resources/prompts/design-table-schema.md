Design a Coda table schema based on this description: {description}

## Steps

1. **Identify entities** — extract the distinct data objects from the description. Each entity becomes a table.
2. **Define columns** for each table:
   - Choose appropriate column types (text, number, date, select, checkbox, person, etc.)
   - Identify the display column — pick a unique, human-readable field
   - Mark columns that should be calculated (formulas, lookups)
   - Add select/multi-select options where values are from a known set
3. **Define relations** — identify foreign-key relationships between tables:
   - Create relation columns linking child to parent tables
   - Add lookup columns to pull display values across relations
4. **Add computed columns**:
   - Status rollups (e.g., "% complete" from child task statuses)
   - Date calculations (e.g., "days until due")
   - Conditional formatting triggers
5. **Output the schema** as a structured list:
   - Table name, display column, estimated row volume
   - For each column: name, type, required/optional, formula (if calculated)
   - Relation diagram showing table connections
6. **Validate**:
   - No table exceeds likely 10,000-row limit for interactive use
   - No table has >50 columns
   - Relations are unambiguous (each relation column clearly names the target table)
   - Display columns are unique and descriptive