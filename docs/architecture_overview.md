# Architecture Overview

## Flow

1. A local simulator generates synthetic loyalty events.
2. Events are sent through API Gateway or directly to Amazon Kinesis.
3. A producer Lambda validates and enriches the payload.
4. A consumer Lambda batches events into compressed JSON Lines files in Amazon S3.
5. Databricks Auto Loader ingests landing files into a Bronze Delta table.
6. Silver processing validates, normalizes, and deduplicates by `event_id`.
7. Gold tables expose daily partner metrics, hourly event metrics, and member balances.
8. A local RAG assistant retrieves policies, runbooks, contracts, and architecture notes.

## Design Decisions

- Use synthetic data only.
- Batch events into JSON Lines files to reduce the S3 small-file problem.
- Keep processing idempotent because Lambda event-source mappings are at-least-once.
- Use RAG for policies, runbooks, and contracts rather than raw transactions.
- Answer metrics questions from Gold tables, not vectors.
- For this POC, external integrations run with SSL certificate verification disabled because corporate CA certificates are not available in the local environment.

## POC Security Posture

This implementation does not use SSL certificate validation for the OpenAI and Databricks SQL connections in the local POC environment. The goal is to keep the functional MVP working without blocking on enterprise certificate distribution.

This is an explicit POC tradeoff, not a production target. Enterprise hardening can be added later once trusted CA material and managed secret handling are available.

## Recommended Delivery Approach

Keep the current implementation as the functional MVP. It already proves the end-to-end flow across event generation, AWS ingestion, Databricks processing, and the hybrid assistant.

Add enterprise architecture pieces incrementally rather than redesigning the whole stack up front. This keeps a working path available while each production concern is introduced and validated in isolation.

## Incremental Enterprise Additions

1. Security hardening: introduce trusted CA bundles or enterprise certificate distribution, move secrets to managed stores, and tighten IAM and Unity Catalog permissions.
2. Operational resilience: add structured observability, alerting, retry policies, dead-letter handling, and documented recovery procedures.
3. Deployment discipline: introduce CI/CD, environment promotion, infrastructure-as-code coverage, and repeatable Databricks job deployment.
4. Data governance: expand quality checks, lineage, access controls, retention rules, and audit-ready table ownership.
5. Assistant productionization: move from local-only vector storage to an enterprise-hosted retrieval option if scale, concurrency, or governance requires it.

## Observability Requirements

The first enterprise increment after MVP validation should focus on operational visibility rather than redesign.

Required monitoring surfaces:

1. AWS ingest health: API Gateway errors, producer Lambda errors, Kinesis iterator age, consumer Lambda failures, and S3 landing freshness.
2. Databricks processing health: Bronze and Silver freshness, quarantine growth, Gold aggregate freshness, job status, and Auto Loader checkpoint progress.
3. Local operational probe: a repeatable health check that reports freshness, quarantine, and the most recent successful data movement across Silver and Gold.

The purpose of this slice is to detect where the pipeline stopped, prove whether data is still moving, and shorten recovery time without changing the functional MVP behavior.

## Core Storage Paths

- `landing/events/`
- `checkpoints/bronze/`
- `schemas/bronze/`
- `quarantine/events/`
