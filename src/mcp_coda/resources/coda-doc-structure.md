# Coda Doc Structure

Rules for organizing docs, pages, and subpages in Coda.

## Doc Hierarchy

```
Doc
├── Page (canvas — rich text + embedded objects)
│   ├── Subpage
│   └── Subpage
│       └── Nested Subpage (max 7 levels)
├── Page
└── Page (folder-page — groups children, no own content)
```

- A **doc** is the top-level container. It has its own URL, permissions, and version history.
- A **page** is a canvas that holds rich text, tables, views, controls, buttons, and formulas.
- Pages can nest up to 7 levels deep. Beyond 3 levels, navigation becomes difficult — prefer flat structures.

## Page Types

| Type | API `contentType` | Use For |
|------|-------------------|---------|
| Canvas | `canvas` | General content, tables, controls |
| Folder-page | `canvas` (no body) | Grouping child pages — acts as a navigation node |

There is no separate "folder" object inside a doc. A page with children but no meaningful body content functions as a folder.

## When to Split Docs vs. Use Subpages

**Separate docs** when:
- Different permission sets are needed (doc-level sharing is the coarsest ACL unit)
- Content exceeds ~200 tables or ~50 pages — performance degrades
- Teams or projects have independent lifecycles

**Subpages** when:
- Content shares the same audience and permissions
- Cross-referencing between pages is frequent (formulas, lookups, buttons)
- A single table schema spans related views

## Naming Conventions

- Page names: short, descriptive, no special characters (they become URL slugs)
- Avoid emoji-only names — screen readers and search cannot parse them
- Prefix with a number (`01-Setup`, `02-Data`) only for sequential processes

## API Considerations

- `coda_list_pages` returns the full page tree in a flat list with `parent.id` references
- `coda_create_page` accepts `parentPageId` for nesting
- `coda_get_page` with `content` format returns rendered page body (HTML)
- Moving a page (`coda_update_page` with new `parentPageId`) does not break cross-page formula references
- Deleting a parent page deletes all children — there is no orphan recovery

## Anti-Patterns

- Deeply nested pages (>3 levels) — hard to navigate, URL becomes unwieldy
- One table per page with no contextual content — consolidate related tables
- Using page names as stable identifiers — names change; use page IDs (`canvas-xxxx`)
- Duplicating data across pages instead of using cross-doc formulas or lookups
