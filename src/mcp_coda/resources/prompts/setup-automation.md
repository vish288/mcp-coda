Set up a {trigger_type}-triggered automation in Coda doc `{doc_id}`.

## Steps

### 1. Understand the trigger type

**Webhook** (`{trigger_type}` = webhook):
- List existing webhooks or create a new one in the doc
- Design the payload schema with `eventType`, `requestId`, and `timestamp` fields
- Plan idempotency: create a "Processed Events" table to track handled `requestId` values

**Button** (`{trigger_type}` = button):
- Identify the target table and the action the button should perform
- Design the button formula (row modification, notification, Pack call)
- Choose placement: row-level button column or page-level button

**Time-based** (`{trigger_type}` = time):
- Note: time-based automations can only be configured in the Coda UI, not via API
- Define the schedule (hourly, daily, weekly) and the action to execute
- Document the automation rule for manual setup

### 2. Design the action

- What data should be read or modified when the automation fires?
- What is the expected output or side effect?
- Are there dependent actions that should chain after completion?

### 3. Error handling

- What happens if the automation fails? Define fallback behavior.
- For webhooks: plan retry logic on the sender side (the Coda webhook endpoint returns 202, not a success/failure).
- For buttons: poll `coda_get_mutation_status` for completion.

### 4. Implement

- For webhooks: document the endpoint URL, payload format, and expected response.
- For buttons: create the button column with `coda_upsert_rows` or document the formula for manual setup.
- For time-based: provide step-by-step UI configuration instructions.

### 5. Test

- Fire the trigger with test data and verify the automation executed correctly.
- Check for idempotency: fire the same trigger twice — the second should be a no-op or handled gracefully.
- Verify rate limits are not exceeded under expected load.