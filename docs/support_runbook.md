# Streaming Support Runbook

## Immediate Health Probe

Run the focused operational health check first:

```powershell
.\.venv\Scripts\python.exe .\tools\ops_health_check.py
```

Use the output to decide whether the issue is stale data, quarantine growth, or a break between Silver and Gold.

## Investigation Order

1. Check API Gateway 4xx and 5xx metrics.
2. Check producer Lambda errors and throttles.
3. Check Kinesis incoming records and iterator age.
4. Check consumer Lambda errors and the failed-event destination.
5. Confirm new JSON Lines files are arriving under the S3 landing prefix.
6. Check the Databricks workflow status and Auto Loader checkpoint.
7. Compare Bronze, Silver, and quarantine counts.
8. Record the trace ID, event ID, affected time window, and recovery action.

## Evidence To Capture

1. Latest Silver event timestamp and delay minutes.
2. Current quarantine count.
3. Latest Gold hourly aggregate timestamp and latest Gold daily aggregate date.
4. Any AWS metric spikes or Lambda error messages in the same time window.
5. The exact replay or restart action taken.

## Remediation By Health Check Failure Type

### 1. Silver Freshness Failure

Condition: `ops_health_check.py` reports `silver freshness` as `FAIL` because the delay exceeds the configured threshold or the latest Silver timestamp is missing.

Actions:

1. Confirm whether new files are arriving in the S3 landing prefix.
2. If landing files are missing, investigate API Gateway, producer Lambda, Kinesis, and consumer Lambda in that order.
3. If landing files exist but Silver is stale, inspect the Databricks workflow run history and Auto Loader checkpoint state.
4. Restart the affected Databricks job only after confirming the checkpoint path is intact.
5. Re-run `ops_health_check.py` after recovery and record the refreshed Silver timestamp.

### 2. Quarantine Count Failure

Condition: `ops_health_check.py` reports `quarantine count` as `FAIL` because the count exceeds the configured threshold.

Actions:

1. Query recent rows from `loyalty_demo.silver.loyalty_events_quarantine` to identify the failing fields and event types.
2. Compare the failing records against [docs/event_contract.md](c:/Users/d693389/OneDrive%20-%20Telstra/GIT-POC/aws-loyalty-poc/loyalty-ai-platform/docs/event_contract.md).
3. Determine whether the issue is bad simulator payloads, producer enrichment changes, or Silver validation logic.
4. Fix the upstream schema or validation issue before replaying data.
5. Replay only the affected input set if that is supported in the current environment, then confirm quarantine returns to baseline.

### 3. Latest Data Movement Failure

Condition: `ops_health_check.py` reports `latest data movement` as `FAIL` because Silver timestamps are missing or Gold timestamps are not present.

Actions:

1. If Silver is present but Gold timestamps are missing or stale, treat the incident as a Databricks transformation or workflow issue.
2. Check the Gold job definitions, recent run status, and dependent tables in Bronze and Silver.
3. Confirm that `loyalty_demo.gold.hourly_event_metrics` and `loyalty_demo.gold.daily_partner_points` are still being refreshed.
4. Re-run the Gold transformation step only after confirming the upstream Silver data is healthy.
5. Re-run the health check and capture both Silver and Gold timestamps after remediation.

### 4. Databricks Connectivity Failure

Condition: the health check fails before returning results because Databricks connection values are missing or the query execution errors.

Actions:

1. Confirm the required `.env` values are present: `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`, and `DATABRICKS_TOKEN`.
2. Confirm the POC TLS setting is still aligned with the local environment: `DATABRICKS_SQL_TLS_NO_VERIFY=true`.
3. Retry the focused query path with [rag/databricks_retriever.py](c:/Users/d693389/OneDrive%20-%20Telstra/GIT-POC/aws-loyalty-poc/loyalty-ai-platform/rag/databricks_retriever.py) to determine whether the failure is general connectivity or specific to the health check.
4. If the connector still fails, capture the exact error message and stop before making unrelated code changes.

### 5. No Rows Returned

Condition: the health check returns no rows for a required operational query.

Actions:

1. Confirm the expected Silver and Gold tables exist and are accessible in the current Databricks workspace.
2. Determine whether the environment is genuinely empty or whether table names, catalog names, or permissions changed.
3. If the environment was recently rebuilt, reload data through the ingest path and rerun the health check.
4. If the environment should contain data, treat this as a configuration or permissions regression and capture the exact workspace context.
