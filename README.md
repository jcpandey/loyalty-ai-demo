# Loyalty AI Platform

Synthetic loyalty streaming, lakehouse, and RAG demo built from the implementation guide.

## Architecture

Synthetic events are generated locally, sent through API Gateway or directly to Kinesis, written by Lambda to Amazon S3 as compressed JSON Lines batches, ingested into Databricks Bronze, refined into Silver, aggregated into Gold, and documented for a local RAG assistant.

## Delivery Recommendation

Treat the current working implementation as the functional MVP. It already demonstrates the core business flow and gives you a stable baseline for validation.

From there, add missing enterprise architecture capabilities incrementally. Prioritize security, observability, deployment automation, and governance as separate follow-on slices so each change can be tested without destabilizing the end-to-end path.

## Repository Layout

- `docs/`: event contract, policy, runbook, and architecture notes
- `simulator/`: synthetic event generator
- `lambdas/`: producer and consumer Lambda handlers
- `databricks/`: setup, Bronze, Silver, Gold, and quality checks
- `rag/`: document ingestion and local assistant
- `tests/`: starter automated tests

## Local Setup

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If your environment has a broken `REQUESTS_CA_BUNDLE`, clear it for the current session before installing:

```powershell
Remove-Item Env:REQUESTS_CA_BUNDLE -ErrorAction SilentlyContinue
```

## Quick Validation

```powershell
.\.venv\Scripts\python.exe -m compileall simulator lambdas rag tests
.\.venv\Scripts\python.exe -m pytest -q
.\tools\run_mvp_smoke.cmd -SkipIngest
.\.venv\Scripts\python.exe .\tools\ops_health_check.py
```

If PowerShell blocks direct `.ps1` execution in your session, use the `.cmd` launcher above or run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_mvp_smoke.ps1 -SkipIngest
```

## Next Build Steps

1. Keep the current flow running as the baseline MVP and validate it with representative business questions.
2. Add observability, alerting, and failure-handling around the AWS and Databricks pipeline.
3. Introduce CI/CD and repeatable environment promotion for code, SQL, and Databricks jobs.
4. Replace temporary TLS workarounds and local secrets handling with enterprise-safe controls when certificates and managed secrets are available.
5. Expand governance and production-readiness only after each earlier slice is stable.

## CI/CD Stub

See `docs/cicd_stub.md` for the staged pipeline outline and `.github/workflows/validation.yml` for the starter automation.

For GitHub environment and secret setup, see `docs/github_actions_setup.md`.
