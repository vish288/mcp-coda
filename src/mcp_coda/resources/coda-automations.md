# Coda Automation Patterns

Rules for building automations, webhooks, and triggered actions in Coda.

## Automation Types

| Type | Trigger | API Tool |
|------|---------|----------|
| Webhook | External HTTP POST to a Coda webhook URL | `coda_trigger_webhook` |
| Button | User clicks a button column or page button | `coda_push_button` |
| Time-based | Scheduled (hourly, daily, etc.) | Configured in Coda UI only |
| Row change | A row value changes | Configured in Coda UI only |

Only webhooks and buttons are triggerable via the API. Time-based and row-change automations are configured exclusively in the Coda UI.

## Webhook Patterns

### Triggering

```
POST /docs/{docId}/hooks/{hookId}/trigger
Content-Type: application/json

{"payload": {"key": "value"}}
```

- The payload is freeform JSON. Coda passes it to the automation rule as `EventData`.
- Webhook URLs are doc-scoped — each doc has its own set of hooks.
- Webhooks must be enabled in the doc's automation settings.

### Payload Design

- Keep payloads flat — deeply nested JSON is harder to reference in Coda formulas.
- Include an `eventType` field for routing: `{"eventType": "order_created", "orderId": "123"}`.
- Include a `timestamp` field (ISO 8601) for debugging and idempotency.
- Max payload size: 1 MB.

### Idempotency

- Coda does not deduplicate webhook deliveries. The same payload sent twice runs the automation twice.
- Include a unique `requestId` in the payload. Use a Coda formula to check for duplicates before processing.
- Pattern: store processed `requestId` values in a "Processed Events" table, check before acting.

## Button Patterns

### Pushing Buttons via API

```python
coda_push_button(doc_id="doc123", table_id="tbl456", row_id="row789", column_id="c-btnCol")
```

- The button's formula executes server-side. You receive a `requestId` for polling.
- Use `coda_get_mutation_status` to check completion.
- Button actions can modify rows, send notifications, call external APIs (via Packs).

### Button Design

- One action per button. Compound actions should chain via helper columns.
- Name buttons with verbs: "Approve", "Send Reminder", "Archive".
- Buttons in views inherit the view's filter context — the row is already scoped.

## Rate Limits

- Webhook triggers: 10 requests per 6 seconds (write rate limit applies).
- Button pushes: same write rate limit — 10 per 6 seconds.
- Automation execution: Coda queues beyond capacity. No guarantee on execution latency.
- Back-off strategy: respect `Retry-After` header, exponential backoff starting at 1s.

## Error Handling

- Webhook trigger returns `202 Accepted` — it does not confirm the automation executed.
- Button push returns a `requestId`. Poll `coda_get_mutation_status` for `completed` or `failed`.
- Failed automations are logged in the doc's automation history (UI only — not queryable via API).

## Anti-Patterns

- Sending high-frequency webhooks (>10/min) without batching — triggers rate limiting
- Relying on webhook ordering — Coda does not guarantee FIFO delivery
- Buttons that modify unrelated tables without clear naming — confusing for doc users
- Not including idempotency keys — duplicate webhook deliveries cause duplicate actions
- Using webhooks for data sync instead of the row upsert API — webhooks are for event-driven flows
