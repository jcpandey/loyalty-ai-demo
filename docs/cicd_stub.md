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

### 3. Lambda Deployment Stage

Run on `workflow_dispatch` through `.github/workflows/deploy_lambdas.yml`.

Checks and actions:

1. Re-run compile and unit-test validation before deployment.
2. Package `lambdas/producer/handler.py` and `lambdas/consumer/handler.py` into deployment zips.
3. Update the configured AWS Lambda functions.
4. Run the post-deploy smoke and operational health gate.

Required secrets:

1. `AWS_ACCESS_KEY_ID`
2. `AWS_SECRET_ACCESS_KEY`
3. `AWS_REGION`

Manual inputs:

1. `deploy_producer`
2. `deploy_consumer`
3. `run_post_deploy_smoke`
4. `skip_ingest`
5. `max_silver_delay_minutes`
6. `max_quarantine_count`
7. `lambda_name_prefix`
8. `lambda_environment`

Purpose:

Promote Lambda code only after validation, then prove the shared environment still passes the functional and operational gates.

The workflow resolves the producer and consumer Lambda names at runtime by searching AWS for function names that match the pattern `<lambda_name_prefix>-<lambda_environment>-producer` and `<lambda_name_prefix>-<lambda_environment>-consumer`.

### 4. Future Databricks Deployment Stage

Not implemented yet. Recommended next slice:

1. Databricks SQL and job promotion.
2. Post-deploy smoke validation.

## Recommended Promotion Flow

1. Developer runs local smoke and ops checks.
2. Pull request passes compile and unit-test validation.
3. Manual smoke validation runs against the shared environment.
4. Run the Lambda deployment workflow.
5. Only then promote Databricks and broader environment changes.

## Repository Entry Points

1. Local smoke runner: `tools/run_mvp_smoke.cmd`
2. PowerShell smoke runner: `tools/run_mvp_smoke.ps1`
3. Operational health probe: `tools/ops_health_check.py`
4. Functional verifier: `tools/mvp_verify.py`
5. Lambda deployment workflow: `.github/workflows/deploy_lambdas.yml`

## Notes

1. The smoke validation stage is intentionally manual because it requires live OpenAI and Databricks credentials.
2. The current workflow assumes the POC TLS posture is still in use for shared validation.
3. Replace manual dispatch with environment-gated deployment automation only after the pipeline is stable.
4. See `docs/github_actions_setup.md` for the GitHub environment and secret setup sequence.