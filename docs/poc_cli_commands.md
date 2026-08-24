# POC CLI Command Reference

This file consolidates the main terminal and PowerShell commands used during this POC.

It is organized by phase so you can rerun or adapt the setup without digging through chat history.

## 1. Project Setup

```powershell
mkdir loyalty-ai-platform
Set-Location loyalty-ai-platform
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Alternative without activating the venv:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Dependency Installation

```powershell
python -m pip install -r requirements.txt
```

Direct venv execution used throughout the POC:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 3. PowerShell Execution Policy Fix

Used when PowerShell blocked `Activate.ps1`:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 4. Broken CA Bundle / TLS Workarounds

Session-only fix for the invalid `REQUESTS_CA_BUNDLE` value:

```powershell
Remove-Item Env:REQUESTS_CA_BUNDLE -ErrorAction SilentlyContinue
```

Permanent fix for the persisted bad user environment variable:

```powershell
reg delete HKCU\Environment /v REQUESTS_CA_BUNDLE /f
```

Diagnostic commands used to identify the problem:

```powershell
Get-ChildItem Env: | Where-Object { $_.Name -match '^(PIP_CERT|REQUESTS_CA_BUNDLE|CURL_CA_BUNDLE|SSL_CERT_FILE)$' } | Select-Object Name,Value | Format-Table -AutoSize
reg query HKCU\Environment /v REQUESTS_CA_BUNDLE
reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v REQUESTS_CA_BUNDLE
```

## 5. Python / Environment Diagnostics

```powershell
Get-Command python -ErrorAction SilentlyContinue | Select-Object Name,Source
Get-Command python3 -ErrorAction SilentlyContinue | Select-Object Name,Source
Get-Command pip -ErrorAction SilentlyContinue | Select-Object Name,Source
where.exe python
where.exe py
python --version
python3 --version
pip --version
Get-ExecutionPolicy -List | Format-Table -AutoSize
Get-Location
```

## 6. Re-entering the Project and Venv

After reopening PowerShell:

```powershell
Set-Location "C:\Users\d693389\OneDrive - Telstra\GIT-POC\aws-loyalty-poc\loyalty-ai-platform"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Exit the virtual environment:

```powershell
deactivate
```

## 7. Local Validation

```powershell
.\.venv\Scripts\python.exe -m compileall simulator lambdas rag tests
.\.venv\Scripts\python.exe -m pytest -q
```

Additional compile checks used during debugging:

```powershell
.\.venv\Scripts\python.exe -m py_compile .\rag\assistant.py
.\.venv\Scripts\python.exe -m py_compile .\rag\databricks_retriever.py
.\.venv\Scripts\python.exe -m py_compile .\rag\assistant.py .\rag\databricks_retriever.py
```

## 8. RAG Document Ingestion

Standard run:

```powershell
Invoke-Expression '.\.venv\Scripts\python.exe .\rag\ingest_documents.py'
```

Equivalent direct form when already in the repo root:

```powershell
.\.venv\Scripts\python.exe .\rag\ingest_documents.py
```

## 9. Local Assistant

Standard run:

```powershell
Invoke-Expression '.\.venv\Scripts\python.exe .\rag\assistant.py'
```

Equivalent direct form when already in the repo root:

```powershell
.\.venv\Scripts\python.exe .\rag\assistant.py
```

Example checks that were used against the assistant:

```text
What is the loyalty event schema?
What is the latest data freshness?
How many records are in quarantine?
What is the balance for member M000123?
```

## 10. Databricks SQL Connectivity and Query Routing

Connectivity smoke test:

```powershell
.\.venv\Scripts\python.exe .\rag\databricks_retriever.py "What is the latest data freshness?"
```

Other tested question patterns:

```powershell
.\.venv\Scripts\python.exe .\rag\databricks_retriever.py "Who are the top partners?"
.\.venv\Scripts\python.exe .\rag\databricks_retriever.py "Show transaction history for member M000123"
```

Temporary Databricks TLS workaround was enabled via `.env` rather than a CLI flag:

```dotenv
DATABRICKS_SQL_SOCKET_TIMEOUT=15
DATABRICKS_SQL_RETRY_ATTEMPTS=1
DATABRICKS_SQL_TLS_NO_VERIFY=true
```

## 11. OpenAI TLS Workaround

Temporary OpenAI TLS workaround was enabled via `.env` rather than a CLI flag:

```dotenv
OPENAI_TLS_NO_VERIFY=true
```

Preferred long-term OpenAI certificate configuration:

```dotenv
OPENAI_TRUSTED_CA_FILE=C:\path\to\corporate-ca.pem
```

## 12. Helper and Diagnostic One-Liners

Import health checks used during debugging:

```powershell
.\.venv\Scripts\python.exe -c "print('python startup ok'); import requests, chromadb; print('imports ok')"
.\.venv\Scripts\python.exe -c "import openai; print(openai.__version__)"
.\.venv\Scripts\python.exe -c "import langchain_openai; print('ok')"
```

Package verification used after install:

```powershell
.\.venv\Scripts\python.exe -m pip show boto3
.\.venv\Scripts\python.exe -m pip show openai
.\.venv\Scripts\python.exe -m pip show pytest
```

## 13. Path-Safe Parent-Folder Execution

When the terminal was one level above `loyalty-ai-platform`, these forms were used:

```powershell
Set-Location .\loyalty-ai-platform
.\.venv\Scripts\python.exe .\rag\assistant.py
```

Or without changing directory:

```powershell
.\loyalty-ai-platform\.venv\Scripts\python.exe .\loyalty-ai-platform\rag\assistant.py
.\loyalty-ai-platform\.venv\Scripts\python.exe .\loyalty-ai-platform\rag\ingest_documents.py
```

## 14. Notes

- Some infrastructure work for AWS and Databricks was also performed through cloud consoles and workspace UIs, not only through CLI.
- TLS workarounds were used only to unblock the corporate/intercepted environment for the POC.
- For a production-ready implementation, replace `*_TLS_NO_VERIFY=true` settings with proper corporate CA bundle trust.