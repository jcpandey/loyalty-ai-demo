# CI/CD Stub

This document defines the minimum CI/CD shape for the loyalty POC.

## Goal

Automate the validation gates that already exist locally, then add deployment stages incrementally without destabilizing the working MVP.

## Pipeline Stages

### 1. Pull Request Validation

Run on pull requests and pushes to the default branch.

Checks:

1. Python dependency installation.
2. Compile validation across `simulator`, `lambdas`, `rag`, `tests`, and `tools`.
3. Unit tests.

Purpose:

Catch basic regressions before anything reaches the shared branch.

### 2. Manual Smoke Validation

Run on `workflow_dispatch` after secrets are configured.

Checks:

1. `tools/run_mvp_smoke.ps1 -SkipIngest`
2. Embedded operational health gate via `tools/ops_health_check.py`

Required secrets:

1. `OPENAI_API_KEY`
2. `OPENAI_CHAT_MODEL`
3. `DATABRICKS_SERVER_HOSTNAME`
4. `DATABRICKS_HTTP_PATH`
5. `DATABRICKS_TOKEN`

Manual inputs:

1. `skip_ingest`
2. `max_silver_delay_minutes`
3. `max_quarantine_count`

Purpose:

Prove that the shared environment still supports the full MVP query path and operational checks.

### 3. Future Deployment Stage

Not implemented yet. Recommended deployment slices are:

1. Lambda packaging and deployment.
2. Databricks SQL and job promotion.
3. Post-deploy smoke validation.

## Recommended Promotion Flow

1. Developer runs local smoke and ops checks.
2. Pull request passes compile and unit-test validation.
3. Manual smoke validation runs against the shared environment.
4. Only then promote Lambda, Databricks, and docs changes.

## Repository Entry Points

1. Local smoke runner: `tools/run_mvp_smoke.cmd`
2. PowerShell smoke runner: `tools/run_mvp_smoke.ps1`
3. Operational health probe: `tools/ops_health_check.py`
4. Functional verifier: `tools/mvp_verify.py`

## Notes

1. The smoke validation stage is intentionally manual because it requires live OpenAI and Databricks credentials.
2. The current workflow assumes the POC TLS posture is still in use for shared validation.
3. Replace manual dispatch with environment-gated deployment automation only after the pipeline is stable.
4. See `docs/github_actions_setup.md` for the GitHub environment and secret setup sequence.