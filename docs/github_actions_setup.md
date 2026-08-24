# GitHub Actions Setup

This guide covers the GitHub-side steps that cannot be completed from the local workspace alone.

## Goal

Prepare the repository so the starter validation workflow can run both pull request checks and the shared smoke gate.

## Prerequisites

1. The code is pushed to a GitHub repository.
2. GitHub Actions is enabled for the repository.
3. You have permission to manage repository environments and secrets.

## 1. Create The Shared Environment

In GitHub:

1. Open the repository.
2. Go to `Settings`.
3. Open `Environments`.
4. Create a new environment named `poc-shared`.

Recommended protection settings for this POC:

1. Require manual approval before running the shared smoke workflow.
2. Restrict environment use to maintainers or the delivery owner.

## 2. Add Required Environment Secrets

Add these secrets to the `poc-shared` environment:

1. `OPENAI_API_KEY`
2. `OPENAI_CHAT_MODEL`
3. `DATABRICKS_SERVER_HOSTNAME`
4. `DATABRICKS_HTTP_PATH`
5. `DATABRICKS_TOKEN`

Recommended additional environment secrets or variables for this POC:

1. `OPENAI_TLS_NO_VERIFY=true`
2. `DATABRICKS_SQL_TLS_NO_VERIFY=true`
3. `OPS_MAX_SILVER_DELAY_MINUTES=10080`
4. `OPS_MAX_QUARANTINE_COUNT=10`
5. `AWS_REGION`

If you want to use the Lambda deployment workflow, also add these repository or environment secrets:

1. `AWS_ACCESS_KEY_ID`
2. `AWS_SECRET_ACCESS_KEY`

## 3. Trigger The Validation Workflow

After the workflow file is on GitHub:

1. Open the `Actions` tab.
2. Select the `Validation` workflow.
3. Choose `Run workflow`.
4. Select the target branch.
5. Keep `skip_ingest=true` for routine smoke checks unless you intentionally want to rebuild embeddings.
6. Adjust `max_silver_delay_minutes` or `max_quarantine_count` only when you are intentionally tightening the gate.

## 4. Expected Outcomes

You should see two kinds of workflow behavior:

1. `push` and `pull_request`: compile and unit-test validation only.
2. `workflow_dispatch`: the shared smoke gate, including the operational health gate.
3. `Deploy Lambdas` workflow dispatch: producer and consumer Lambda deployment, followed by optional post-deploy smoke validation.

## 5. Trigger The Lambda Deployment Workflow

After the deployment workflow file is on GitHub:

1. Open the `Actions` tab.
2. Select the `Deploy Lambdas` workflow.
3. Choose `Run workflow`.
4. Select whether to deploy producer, consumer, or both.
5. Set `lambda_name_prefix` to the shared prefix used in your AWS Lambda function names. For this POC the default `loyalty-ai-demo` is expected to work.
6. Set `lambda_environment` to the environment segment in the Lambda names such as `dev`, `test`, or `prod`.
7. The workflow expects names like `loyalty-ai-demo-dev-producer` and `loyalty-ai-demo-dev-consumer`.
8. Keep `run_post_deploy_smoke=true` for normal controlled releases.
9. Keep `skip_ingest=true` unless you intentionally want the deployment flow to rebuild embeddings.
10. Review the post-deploy smoke result before considering the deployment complete.

## 6. Failure Handling

If the manual shared smoke validation fails:

1. Read the workflow log to determine whether the failure happened in compile, tests, MVP verification, or operational health.
2. Use [docs/support_runbook.md](c:/Users/d693389/OneDrive%20-%20Telstra/GIT-POC/aws-loyalty-poc/loyalty-ai-platform/docs/support_runbook.md) for remediation.
3. Re-run the workflow only after the root cause is corrected.

If the Lambda deployment workflow fails:

1. Determine whether the failure happened in pre-deploy validation, AWS credential setup, function code update, or post-deploy smoke validation.
2. If the AWS update step fails during name resolution, verify the `lambda_name_prefix`, `lambda_environment`, region, and AWS credentials first.
3. If the post-deploy smoke gate fails, treat the deployment as unverified and use [docs/support_runbook.md](c:/Users/d693389/OneDrive%20-%20Telstra/GIT-POC/aws-loyalty-poc/loyalty-ai-platform/docs/support_runbook.md) before rerunning.

## Notes

1. This repository currently uses a POC TLS posture and expects the smoke validation environment to tolerate `*_TLS_NO_VERIFY=true`.
2. Replace that with proper CA trust and managed secrets before converting this workflow into a production deployment gate.