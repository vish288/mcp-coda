# Coda API Best Practices

Rules for effective use of the Coda REST API v1.

## Rate Limits

| Category | Limit | Scope |
|----------|-------|-------|
| Read | 100 requests / 6 seconds | Per API token |
| Write | 10 requests / 6 seconds | Per API token |
| Burst | Short bursts above limit tolerated | Followed by throttling |

- Rate limits are per-token, not per-doc or per-IP.
- Exceeding the limit returns `429 Too Many Requests` with a `Retry-After` header (seconds).
- Strategy: respect `Retry-After`, then exponential backoff starting at 1s, max 60s.

## Pagination

All list endpoints return paginated responses:

```json
{
  "items": [...],
  "href": "https://coda.io/apis/v1/docs/...",
  "nextPageToken": "abc123",
  "nextPageLink": "https://coda.io/apis/v1/docs/...?pageToken=abc123"
}
```

- Default page size: 25 items. Max: 500 (rows), 200 (docs, pages, tables).
- Use `limit` parameter to control page size.
- Use `pageToken` from the response to fetch the next page.
- When `nextPageToken` is absent, you have reached the last page.
- Always paginate — never assume a single response contains all items.

## Async Mutations

Write operations that modify data return a `requestId`:

```json
{"requestId": "mut-abc123"}
```

- The mutation may not be complete when the response arrives.
- Poll `GET /mutationStatus/{requestId}` to check completion.
- Status values: `queued`, `processing`, `completed`, `failed`.
- Polling interval: start at 500ms, back off to 2s. Timeout after 60s.
- Do not fire dependent writes until the previous mutation is `completed`.

## Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| 400 | Bad request — invalid params | Fix request payload |
| 401 | Invalid or expired token | Re-authenticate |
| 403 | Insufficient permissions | Check token scope and doc sharing |
| 404 | Resource not found | Verify doc/table/row/page ID |
| 429 | Rate limited | Wait `Retry-After` seconds |
| 500+ | Server error | Retry with backoff (max 3 retries) |

- Error responses include `message` and `statusCode` fields.
- Never retry 400/401/403/404 — these are permanent failures.
- Always retry 429 and 5xx with appropriate backoff.

## ID Formats

| Resource | Format | Example |
|----------|--------|---------|
| Doc | `docId` | `AbCdEfGhIj` |
| Page | `canvas-XXXX` | `canvas-12345` |
| Table | `grid-XXXX` | `grid-67890` |
| Column | `c-XXXX` | `c-aBcDeFg` |
| Row | `i-XXXX` | `i-HiJkLmN` |

- IDs are stable — they survive renames, moves, and doc copies.
- Names are unstable — always store and reference by ID.
- Use `coda_resolve_link` to convert browser URLs to API IDs.

## Request Best Practices

- Include `User-Agent` header identifying your integration.
- Use `valueFormat=simpleWithArrays` for row values — it returns clean scalars instead of rich objects.
- Specify only the columns you need via `useColumnNames=true` to reduce response size.
- For bulk row operations, prefer `coda_upsert_rows` over individual `coda_update_row` calls.
- Max 500 rows per upsert request.

## Retry Strategy

```
1. Send request
2. If 429: wait Retry-After seconds, retry
3. If 5xx: wait 1s, retry (max 3 attempts, doubling wait each time)
4. If 4xx: do not retry — fix the request
5. If timeout (>30s): retry once
```

## Anti-Patterns

- Polling mutation status in a tight loop (<200ms) — wastes rate limit budget
- Ignoring pagination and assuming all items are in the first response
- Using names instead of IDs for lookups — names change, IDs are stable
- Sending individual row updates in a loop instead of batching with upsert
- Not checking `Retry-After` header — fixed sleep values miss the actual cooldown
