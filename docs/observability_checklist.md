# Observability Checklist

Use this checklist for the first enterprise increment after the MVP baseline has passed.

## Goal

Add operational visibility and recovery guidance without changing the working business flow.

## Monitoring Objectives

1. Detect ingest failures quickly.
2. Detect data staleness before users notice it.
3. Distinguish AWS transport issues from Databricks processing issues.
4. Make recovery actions explicit and repeatable.

## AWS Signals

1. API Gateway `4XXError` and `5XXError`
Pass criteria: no sustained increase during normal simulator runs.
Alert threshold: warning when either metric is `>= 1` for 2 consecutive 5-minute periods during an active test window, critical when `>= 5` for 2 consecutive 5-minute periods.

2. Producer Lambda `Errors`, `Throttles`, and `Duration`
Pass criteria: no unexpected errors, and execution duration stays within the configured timeout budget.
Alert threshold: critical on `Errors >= 1` for 2 consecutive 5-minute periods, warning on `Throttles >= 1` for 1 period, warning when `Duration` exceeds 80% of configured timeout for 3 consecutive periods.

3. Kinesis `IncomingRecords`, `IncomingBytes`, and `GetRecords.IteratorAgeMilliseconds`
Pass criteria: records continue arriving and iterator age does not grow uncontrollably.
Alert threshold: critical when `GetRecords.IteratorAgeMilliseconds > 300000` for 2 consecutive 5-minute periods during active ingestion.

4. Consumer Lambda `Errors`, `Throttles`, and failed-event destination usage
Pass criteria: no sustained consumer failures and no growing backlog of failed events.
Alert threshold: critical on `Errors >= 1` for 2 consecutive 5-minute periods, warning on `Throttles >= 1`, critical on any failed-event destination writes during a normal validation run.

5. S3 landing prefix freshness under `landing/events/`
Pass criteria: new JSON Lines files appear after each simulator run.
Alert threshold: investigate when no new landing file appears within 15 minutes of a planned simulator batch.

## Databricks Signals

1. Bronze ingestion freshness
Pass criteria: Bronze receives new files after landing files arrive.
Alert threshold: investigate when Bronze does not reflect new landing files within 15 minutes of confirmed S3 arrival.

2. Silver freshness and row growth
Pass criteria: `loyalty_demo.silver.loyalty_events` advances with recent `event_ts` values.
Alert threshold: warning when `silver_delay_minutes > 1440`, critical when `silver_delay_minutes > 10080`.

3. Quarantine count
Pass criteria: quarantine remains at the expected low baseline for clean simulator traffic.
Alert threshold: warning when `quarantine_count > 2`, critical when `quarantine_count > 10`.

4. Gold aggregate freshness
Pass criteria: `loyalty_demo.gold.hourly_event_metrics` and `loyalty_demo.gold.daily_partner_points` continue to advance.
Alert threshold: investigate when Silver advances but Gold hourly or daily aggregates do not advance within the next scheduled processing window.

5. Databricks workflow and checkpoint health
Pass criteria: jobs succeed consistently and Auto Loader checkpoints advance without manual repair.
Alert threshold: critical on any failed production workflow run, warning when two consecutive scheduled runs are delayed or skipped.

## Local Health Check Command

Use the focused Databricks health check as the repeatable operational probe:

```powershell
.\.venv\Scripts\python.exe .\tools\ops_health_check.py
```

This reports:

1. Silver freshness and delay minutes.
2. Quarantine count.
3. Latest successful data movement across Silver and Gold.

## Alerting Priorities

1. High: consumer Lambda errors, Kinesis iterator age growth, Databricks job failures.
2. High: no new Silver data within the expected freshness window.
3. Medium: quarantine count spikes above baseline.
4. Medium: Gold aggregates stop advancing while Silver continues to move.

## Default Thresholds For This POC

Use these as the first operating thresholds until you have enough runtime history to tighten them.

1. Silver freshness delay: fail when `silver_delay_minutes > 10080`.
This is a 7-day threshold chosen to avoid false failures while the POC is not running continuously.

2. Quarantine growth: fail when `quarantine_count > 10`.
For clean simulator traffic, the expected steady-state value is `0`.

3. Gold movement expectation: investigate if Silver advances but Gold timestamps stop moving.
Treat this as a transformation or workflow issue rather than an ingestion issue.

You can override the first two thresholds in the health check with:

```powershell
.\.venv\Scripts\python.exe .\tools\ops_health_check.py --max-silver-delay-minutes 1440 --max-quarantine-count 2
```

Or by setting environment variables:

```dotenv
OPS_MAX_SILVER_DELAY_MINUTES=1440
OPS_MAX_QUARANTINE_COUNT=2
```

## Ownership

1. Ingest owner: API Gateway, producer Lambda, Kinesis, consumer Lambda, and S3 landing freshness.
2. Databricks owner: Bronze, Silver, Gold, workflow failures, checkpoint issues, and quarantine growth.
3. Assistant owner: RAG ingest freshness, local vector state, and response validation issues.
4. Incident coordinator: collects timestamps, trace IDs, failing layer, and the recovery action taken.

## Recovery Readiness

Before calling this slice complete, confirm all of these exist:

1. Named dashboards or saved views for AWS and Databricks signals.
2. Thresholds for freshness delay and quarantine growth.
3. A clear owner for responding to ingest versus transformation failures.
4. A documented replay or reprocessing path.
5. An updated runbook with investigation order and evidence to capture.

## Recommended Implementation Sequence

1. Establish dashboards and manual health checks first.
2. Add alert thresholds once normal baselines are known.
3. Extend the runbook with concrete recovery actions.
4. Only then automate more aggressive remediation.