# Formulas & Controls Guide

How to work with named formulas and controls in Coda.

## Named Formulas

Named formulas are doc-level computed values — like spreadsheet named ranges but with Coda formula power.

### Reading Formulas

```python
coda_list_formulas(doc_id="docId")         # list all named formulas
coda_get_formula(doc_id="docId", formula_id="f-abc")  # get a specific formula
```

Response includes:
- `name` — the formula's display name
- `value` — the current computed value
- `type` — the result type (text, number, date, etc.)

### Formula Evaluation

- Formula values are **computed server-side** by Coda. The API returns the current result.
- Formulas update automatically when their dependencies change.
- There is no way to create or modify formulas via the API — only read their current values.
- Formulas that reference external Packs evaluate on Coda's schedule (typically every hour for time-triggered Packs).

### Common Formula Patterns

| Pattern | Example | Use Case |
|---------|---------|----------|
| Row count | `[Tasks].Count()` | Dashboard metric |
| Filtered count | `[Tasks].Filter(Status="Done").Count()` | Progress tracking |
| Lookup | `[Settings].Filter(Key="theme").First().Value` | Config values |
| Date calc | `Today() - [Project].StartDate` | Days elapsed |

## Controls

Controls are interactive UI elements on a page that hold a value.

### Control Types

| Type | Description | Value Type |
|------|-------------|------------|
| Text input | Free-text entry | `string` |
| Select list | Dropdown with options | `string` |
| Slider | Numeric range | `number` |
| Date picker | Calendar selection | `string` (ISO 8601) |
| Checkbox/toggle | On/off | `boolean` |
| Button | Action trigger | N/A (no value) |
| Scale | Star/emoji rating | `number` |

### Reading Control Values

```python
coda_list_controls(doc_id="docId", page_id="canvas-123")  # all controls on a page
coda_get_control(doc_id="docId", control_id="ctrl-xyz")    # specific control
```

Response includes:
- `name` — control's display name
- `controlType` — one of the types above
- `value` — current value set by the user

### Control vs. Formula

| Aspect | Control | Formula |
|--------|---------|---------|
| Source | User input | Computed |
| Writeable | Yes (by users in UI) | No |
| API access | Read-only via API | Read-only via API |
| Use case | Filters, parameters, settings | Metrics, derived values |

- Neither controls nor formulas can be written to via the API.
- Controls are set by user interaction in the Coda UI.
- Formulas reference controls as inputs: `If([FilterControl]="Active", ...)`.

## API Constraints

- Formulas and controls are **read-only** via the API. No create, update, or delete.
- Control values reflect the last user interaction — there is no history.
- Formula values are eventually consistent — a formula depending on a just-modified row may return stale data for a few seconds.

## Anti-Patterns

- Trying to set control values via API — not supported
- Polling formula values at high frequency for real-time updates — formulas update on Coda's schedule
- Using formula names as identifiers — names can change; use formula IDs (`f-xxxx`)
- Expecting Pack formula rendering in API responses — only the raw value is returned
