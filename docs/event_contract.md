# Loyalty Event Contract

This project uses a stable event envelope so schema changes can be managed safely.

## Example Payload

```json
{
  "event_id": "ad23918c-127e-4863-a15a-c1bc4a62047e",
  "event_type": "POINTS_EARNED",
  "event_version": "1.0",
  "event_timestamp": "2026-08-20T09:15:31.251Z",
  "member_id": "M000123",
  "partner_id": "ACCOR",
  "transaction_id": "T-7dc8caf1",
  "points": 250,
  "amount_aud": 125.5,
  "channel": "MOBILE_APP",
  "source_system": "LOYALTY_SIMULATOR",
  "trace_id": "f7f709e8-d03f-44e9-9ae5-5b06c98784b0",
  "attributes": {
    "campaign_id": "WINTER_BONUS"
  }
}
```

## Required Fields

- `event_id`
- `event_timestamp`
- `event_type`
- `member_id`

## Validation Rules

- `event_id` is the idempotency key.
- `points` may be positive for earning and negative for redemption or adjustment.
- `event_version` controls schema evolution.
- Member IDs are synthetic and contain no personal information.
- Timestamps use UTC ISO 8601 format.
- Unknown attributes should be placed under `attributes` rather than top-level fields when possible.
