# Page Content Guide

How to read, write, and export page content in Coda.

## Content Formats

| Format | `outputFormat` | Description |
|--------|---------------|-------------|
| HTML | `html` | Full rich-text content with embedded objects |
| Markdown | `markdown` | Simplified text representation |

- `coda_get_page` with `outputFormat="html"` returns the page body as HTML.
- `coda_get_page` with `outputFormat="markdown"` returns a markdown approximation.
- HTML format preserves tables, images, buttons, and embedded views.
- Markdown format loses embedded objects but is easier to process as text.

## Writing Page Content

### Create

```python
coda_create_page(
    doc_id="docId",
    name="New Page",
    content="<h1>Title</h1><p>Body text</p>",
    parent_page_id="canvas-123"  # optional nesting
)
```

### Update

```python
coda_update_page(
    doc_id="docId",
    page_id="canvas-456",
    name="Updated Title",          # optional
    content="<p>New content</p>",  # optional
    insert_mode="replace"          # or "append"
)
```

## Insert Modes

| Mode | Behavior |
|------|----------|
| `replace` | Replaces all page content with the new content |
| `append` | Adds new content at the end of the existing page |

- `replace` is destructive — it overwrites everything including tables embedded in the page.
- `append` is safer for adding content without affecting existing items.
- There is no `prepend` mode. To insert at the top, use `replace` with the combined content.

## Content Format Selection

**Use HTML when:**
- Creating structured pages with headings, lists, and formatting
- Preserving exact layout from templates
- Embedding images via `<img>` tags

**Use Markdown when:**
- Reading page content for text analysis
- Quick content comparison or diffing
- Input comes from markdown-native sources (GitHub, docs)

## Export Workflows

- `coda_export_page` initiates an async export of a page to HTML or Markdown.
- Returns an export `id` — poll `coda_get_export_status` for completion.
- Once complete, the export provides a download URL (temporary, expires in hours).
- Export formats: `html`, `markdown`. PDF export is not available via API.
- Large pages with many tables may take 30+ seconds to export.

## Content Limitations

- Max page content size via API: ~256 KB of HTML.
- Embedded tables in page content are references — updating them via page content API does not change the underlying table data.
- Pack formulas (Mermaid, DrawFlowchart) render in the UI but appear as placeholder text in API responses.
- Images embedded via the Coda UI are hosted on Coda's CDN. External image URLs in `<img>` tags work but may break if the external host goes down.

## Anti-Patterns

- Using `replace` mode without reading current content first — data loss risk
- Embedding large HTML documents (>100 KB) — page load performance degrades
- Parsing HTML responses with regex — use an HTML parser library
- Expecting Pack formula output in API responses — it is not available
- Creating pages with content and no name — the name defaults to the first line of content, which may be truncated
