# MVP Validation Checklist

Use this checklist to confirm the current POC remains a functional MVP before adding enterprise architecture changes.

## Preconditions

- The local `.env` file contains working OpenAI and Databricks values.
- The POC SSL posture is enabled for this environment:
  - `OPENAI_TLS_NO_VERIFY=true`
  - `DATABRICKS_SQL_TLS_NO_VERIFY=true`
- The virtual environment is available at `.venv`.
- The RAG collection has been loaded at least once with `rag/ingest_documents.py`.
- AWS ingestion and Databricks tables already exist.

## Startup Commands

```powershell
Set-Location "C:\Users\d693389\OneDrive - Telstra\GIT-POC\aws-loyalty-poc\loyalty-ai-platform"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Baseline Technical Checks

1. Run a local compile check.

```powershell
.\.venv\Scripts\python.exe -m compileall simulator lambdas rag tests tools
```

Pass criteria: no Python compile errors are reported.

2. Run the unit tests.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Pass criteria: the existing starter test suite passes.

3. Refresh the local knowledge base when docs or RAG code changed.

```powershell
.\.venv\Scripts\python.exe .\rag\ingest_documents.py
```

Pass criteria: the ingestion completes without OpenAI or Chroma errors.

## Business Smoke Checks

Run the combined smoke test:

```powershell
.\tools\run_mvp_smoke.cmd
```

If you want to call the PowerShell script directly from a restricted shell, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_mvp_smoke.ps1
```

Or run the Python verifier directly:

```powershell
.\.venv\Scripts\python.exe .\tools\mvp_verify.py
```

Expected smoke coverage:

1. Databricks freshness query returns a structured result.
2. Databricks quarantine query returns a structured result.
3. Databricks top partners query returns a structured result.
4. Databricks member balance query returns a structured result.
5. Assistant answers the loyalty event schema question using document context.
6. Assistant answers the support runbook question using operational document context.

## Manual End-to-End Confirmation

Use these only when you need to revalidate the ingestion path itself rather than the reporting layer.

1. Send a small batch of synthetic events.

```powershell
.\.venv\Scripts\python.exe .\simulator\generate_events.py --count 5 --no-verify-ssl
```

2. Confirm new S3 landing files appear under `landing/events/`.
3. Confirm Bronze receives new rows.
4. Confirm Silver and Gold reflect the new data.
5. Re-run `.\tools\run_mvp_smoke.cmd`.

## MVP Acceptance Gate

Treat the POC as stable enough for the next enterprise increment only when all of these are true:

1. Compile and unit-test checks pass.
2. The RAG ingest completes successfully.
3. The smoke verifier exits successfully.
4. At least one end-to-end event batch is visible from ingest through query.
5. Known questions return answers without manual code changes.

## Next Increment After MVP Validation

Once this checklist passes consistently, implement observability and failure handling next. That is the highest-value enterprise slice available without needing CA certificate rollout first.