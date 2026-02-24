# Publishing & Analytics Guide

How to publish docs and access analytics data in Coda.

## Publishing

### Publish a Doc

```python
coda_publish_doc(
    doc_id="docId",
    slug="my-published-doc",           # URL-friendly identifier
    discoverable=True,                  # listed in Coda gallery
    earnCredit=True,                    # earn Coda credits for gallery listings
    category="projectManagement",       # gallery category
    mode="view"                         # "view" or "play" (interactive)
)
```

### Publishing Modes

| Mode | Behavior |
|------|----------|
| `view` | Read-only — visitors see content but cannot interact |
| `play` | Interactive — visitors can use buttons, filters, controls |

- Published docs get a public URL at `coda.io/@username/doc-slug`.
- Publishing does not change doc permissions — it creates a separate public view.
- Unpublish with `coda_unpublish_doc` to remove public access.

### Gallery Categories

Available categories for `coda_publish_doc`:
- `projectManagement`, `meetingNotes`, `planning`, `sales`
- `design`, `engineering`, `hr`, `education`, `personal`, `other`

### Publishing Constraints

- Only doc owners can publish or unpublish.
- The slug must be unique across all published Coda docs.
- Published docs show a "Made with Coda" banner unless the doc owner has a paid plan.
- Gallery discoverability requires a description and at least one page of content.

## Analytics

### Available Analytics Tools

| Tool | Returns |
|------|---------|
| `coda_list_doc_analytics` | Doc-level view/copy/like metrics across multiple docs |
| `coda_get_doc_analytics_summary` | Aggregated totals for a single doc |
| `coda_list_page_analytics` | Per-page view counts within a doc |
| `coda_list_pack_analytics` | Pack formula invocation metrics |
| `coda_get_pack_analytics_summary` | Aggregated Pack usage |
| `coda_list_pack_formula_analytics` | Per-formula usage breakdown |
| `coda_get_analytics_last_updated` | Timestamp of last analytics refresh |

### Date Filtering

All analytics tools accept date range parameters:

```python
coda_list_doc_analytics(
    doc_ids=["docId1", "docId2"],
    since_date="2024-01-01",
    until_date="2024-03-31",
    scale="daily"                # "daily" or "cumulative"
)
```

- `since_date` / `until_date`: ISO 8601 date strings
- `scale`: `daily` returns per-day data points; `cumulative` returns running totals
- Analytics data is updated periodically (check `coda_get_analytics_last_updated`)
- Data is available for the last 90 days for free plans, longer for paid plans

### Metrics Available

| Metric | Description |
|--------|-------------|
| `totalSessions` | Number of unique viewing sessions |
| `copies` | Number of times the doc was copied |
| `likes` | Number of likes/favorites |
| `sessionsDesktop` | Desktop viewing sessions |
| `sessionsMobile` | Mobile viewing sessions |
| `sessionsOther` | Other device sessions |

### Analytics Pagination

- Doc analytics supports pagination via `pageToken`.
- When querying many docs, limit to 50 doc IDs per request for performance.
- Page analytics is scoped to a single doc — no cross-doc page analytics in one call.

## Anti-Patterns

- Publishing docs with sensitive data — publishing creates public access regardless of doc permissions
- Relying on real-time analytics — data has a refresh delay (check `last_updated`)
- Querying analytics for 100+ docs in a single call — batch into groups of 50
- Using `cumulative` scale for trend analysis — use `daily` to see actual patterns
