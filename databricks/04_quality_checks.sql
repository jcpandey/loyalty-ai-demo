-- Check for duplicates after Silver processing.
SELECT event_id, COUNT(*) AS duplicate_count
FROM loyalty_demo.silver.loyalty_events
GROUP BY event_id
HAVING COUNT(*) > 1;

-- Check null critical fields.
SELECT COUNT(*) AS invalid_record_count
FROM loyalty_demo.silver.loyalty_events
WHERE event_id IS NULL
   OR member_id IS NULL
   OR event_ts IS NULL;

-- Check freshness.
SELECT
    MAX(event_ts) AS latest_event_timestamp,
    current_timestamp() AS checked_at,
    timestampdiff(MINUTE, MAX(event_ts), current_timestamp()) AS delay_minutes
FROM loyalty_demo.silver.loyalty_events;

-- Reconciliation between Bronze and Silver plus quarantine.
SELECT
    (SELECT COUNT(*) FROM loyalty_demo.bronze.loyalty_events) AS bronze_count,
    (SELECT COUNT(*) FROM loyalty_demo.silver.loyalty_events) AS silver_count,
    (SELECT COUNT(*) FROM loyalty_demo.silver.loyalty_events_quarantine) AS quarantine_count;
