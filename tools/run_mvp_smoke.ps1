param(
    [switch]$SkipCompile,
    [switch]$SkipTests,
    [switch]$SkipIngest,
    [switch]$SkipVerifier,
    [switch]$SkipOpsHealth
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found at $pythonExe"
}

Push-Location $repoRoot

try {
    Write-Host "Running MVP smoke checks from $repoRoot" -ForegroundColor Cyan

    $stepNumber = 1
    $stepTotal = 5

    if (-not $SkipCompile) {
        Write-Host "[$stepNumber/$stepTotal] Compile check" -ForegroundColor Yellow
        & $pythonExe -m compileall simulator lambdas rag tests tools
        if ($LASTEXITCODE -ne 0) {
            throw "Compile check failed"
        }
    }
    $stepNumber += 1

    if (-not $SkipTests) {
        Write-Host "[$stepNumber/$stepTotal] Unit tests" -ForegroundColor Yellow
        & $pythonExe -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Unit tests failed"
        }
    }
    $stepNumber += 1

    if (-not $SkipIngest) {
        Write-Host "[$stepNumber/$stepTotal] RAG document ingest" -ForegroundColor Yellow
        & $pythonExe .\rag\ingest_documents.py
        if ($LASTEXITCODE -ne 0) {
            throw "RAG ingest failed"
        }
    }
    $stepNumber += 1

    if (-not $SkipVerifier) {
        Write-Host "[$stepNumber/$stepTotal] Databricks and assistant verifier" -ForegroundColor Yellow
        & $pythonExe .\tools\mvp_verify.py
        if ($LASTEXITCODE -ne 0) {
            throw "MVP verifier failed"
        }
    }
    $stepNumber += 1

    if (-not $SkipOpsHealth) {
        Write-Host "[$stepNumber/$stepTotal] Operational health gate" -ForegroundColor Yellow
        & $pythonExe .\tools\ops_health_check.py
        if ($LASTEXITCODE -ne 0) {
            throw "Operational health gate failed"
        }
    }

    Write-Host "MVP smoke checks and operational health gate passed." -ForegroundColor Green
}
finally {
    Pop-Location
}